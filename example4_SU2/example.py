from FADO import *
import SU2
import scipy.optimize
import subprocess
import numpy as np

#tab = TableReader(0,0,start=(-1,7),end=(None,None),delim=",")
#functionVal = tab.read("history_direct.csv")

# This is a Python implementation of the config file, should be done with pywrapper in the future
config = SU2.io.Config("config_CFD.cfg")
designparams = copy.deepcopy(config['DV_VALUE_OLD'])
print(designparams)
print(len(designparams))

myarr = [1.0, 0.0]
print(type(myarr))
print(type(designparams))

var = InputVariable(np.array(designparams),ArrayLabelReplacer("__X__"))

pType_direct = Parameter(["DIRECT"],LabelReplacer("__MATH_PROBLEM__"))
pType_adjoint = Parameter(["DISCRETE_ADJOINT"],LabelReplacer("__MATH_PROBLEM__"))

directRun = ExternalRun("DIRECT","SU2_CFD config_tmpl.cfg",True)
directRun.addConfig("config_tmpl.cfg")
directRun.addData("mesh_NACA0012_inv.su2")
directRun.addParameter(pType_direct)

adjointRun = ExternalRun("ADJOINT","SU2_CFD_AD config_tmpl.cfg",True)
adjointRun.addConfig("config_tmpl.cfg")
adjointRun.addData("mesh_NACA0012_inv.su2")
adjointRun.addData("DIRECT/restart_flow.dat")
adjointRun.addParameter(pType_adjoint)

dotProduct = ExternalRun("DOT","SU2_DOT_AD config_tmpl.cfg",True)
dotProduct.addConfig("config_tmpl.cfg")
dotProduct.addData("mesh_NACA0012_inv.su2")
dotProduct.addData("ADJOINT/restart_adj_cd.dat")
dotProduct.addParameter(pType_adjoint)

fun = Function("DRAG","DIRECT/history_direct.csv",TableReader(0,0,start=(-1,7),end=(None,None),delim=","))
fun.addInputVariable(var,"DOT/of_grad.dat",TableReader(None,0))
fun.addValueEvalStep(directRun)
fun.addGradientEvalStep(adjointRun)
fun.addGradientEvalStep(dotProduct)

# Driver
update_iters = 1
driver = ExteriorPenaltyDriver(0.05,update_iters)

#calculate scaling
def_objs = config['OPT_OBJECTIVE']
this_obj = def_objs.keys()[0]
scale = def_objs[this_obj]['SCALE']
global_factor = float(config['OPT_GRADIENT_FACTOR'])
sign  = SU2.io.get_objectiveSign(this_obj)
driver.addObjective("min",fun,sign * scale * global_factor)

driver.preprocess()
driver.setEvaluationMode(False)
driver.setStorageMode(True)

funcVal = driver.fun(np.array(designparams))
grad = driver.grad(np.array(designparams))



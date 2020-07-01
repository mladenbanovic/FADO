from FADO import *
import SU2
import scipy.optimize
import subprocess
import numpy as np

#tab = TableReader(0,0,start=(-1,7),end=(None,None),delim=",")
#functionVal = tab.read("history_direct.csv")

# This is a Python implementation of the config file, should be done with pywrapper in the future
config = SU2.io.Config("config_CFD.cfg")
print(config._filename)
designparams = copy.deepcopy(config['DV_VALUE_OLD'])
print(designparams)
print(len(designparams))

#ffd = InputVariable(0.0,PreStringHandler("DV_VALUE= "),9,1.0,-15.0,15.0)
var = InputVariable(np.array(designparams),ArrayLabelReplacer("__X__"))

pType_direct = Parameter(["DIRECT"],LabelReplacer("__MATH_PROBLEM__"))
pType_adjoint = Parameter(["DISCRETE_ADJOINT"],LabelReplacer("__MATH_PROBLEM__"))
pType_mesh_filename_original = Parameter(["mesh_NACA0012_inv.su2"],LabelReplacer("__MESH_FILENAME__"))
pType_mesh_filename_deformed = Parameter(["mesh_NACA0012_inv_def.su2"],LabelReplacer("__MESH_FILENAME__"))

from mpi4py import MPI      # use mpi4py for parallel run (also valid for serial)
mpiComm = MPI.COMM_WORLD

su2MeshDeformationObject = SU2MeshDeformationWrapperSkipFirstIteration(config, 1, mpiComm)

internalMeshDeformationRun = InternalRun("DEFORM",su2MeshDeformationObject,True)
internalMeshDeformationRun.addConfig("config_tmpl.cfg")
internalMeshDeformationRun.addData("mesh_NACA0012_inv.su2")
internalMeshDeformationRun.addParameter(pType_direct)
internalMeshDeformationRun.addParameter(pType_mesh_filename_original)

  
su2CFDObject = SU2CFDSingleZoneDriverWrapperWithRestartOption(config, 1, mpiComm) #SU2CFDSingleZoneDriverWrapper(config, 1, mpiComm)
  
internalDirectRun = InternalRun("DIRECT",su2CFDObject,True)
internalDirectRun.addConfig("config_tmpl.cfg")
internalDirectRun.addData("DEFORM/mesh_NACA0012_inv_def.su2")
internalDirectRun.addParameter(pType_direct)
internalDirectRun.addParameter(pType_mesh_filename_deformed)

#directRun = ExternalRun("DIRECT","SU2_CFD config_tmpl.cfg",True)
#directRun.addConfig("config_tmpl.cfg")
#directRun.addData("mesh_NACA0012_inv.su2")
#directRun.addParameter(pType_direct)

su2CFDADObject = SU2CFDDiscAdjSingleZoneDriverWrapper(config, 1, mpiComm)

internalAdjointRun = InternalRun("ADJOINT",su2CFDADObject,True)
internalAdjointRun.addConfig("config_tmpl.cfg")
internalAdjointRun.addData("DEFORM/mesh_NACA0012_inv_def.su2")
internalAdjointRun.addData("DIRECT/restart_flow.dat")
internalAdjointRun.addParameter(pType_adjoint)
internalAdjointRun.addParameter(pType_mesh_filename_deformed)

#adjointRun = ExternalRun("ADJOINT","SU2_CFD_AD config_tmpl.cfg",True)
#adjointRun.addConfig("config_tmpl.cfg")
#adjointRun.addData("mesh_NACA0012_inv.su2")
#adjointRun.addData("DIRECT/restart_flow.dat")
#adjointRun.addParameter(pType_adjoint)

su2DotProductObject = SU2DotProductWrapper(config, 1, mpiComm)

internalDotProductRun = InternalRun("DOT",su2DotProductObject,True)
internalDotProductRun.addConfig("config_tmpl.cfg")
internalDotProductRun.addData("DEFORM/mesh_NACA0012_inv_def.su2")
internalDotProductRun.addData("ADJOINT/restart_adj_cd.dat")
internalDotProductRun.addParameter(pType_adjoint)
internalDotProductRun.addParameter(pType_mesh_filename_deformed)

#dotProduct = ExternalRun("DOT","SU2_DOT_AD config_tmpl.cfg",True)
#dotProduct.addConfig("config_tmpl.cfg")
#dotProduct.addData("mesh_NACA0012_inv.su2")
#dotProduct.addData("ADJOINT/restart_adj_cd.dat")
#dotProduct.addParameter(pType_adjoint)

fun = Function("DRAG","DIRECT/history_direct.csv",TableReader(0,0,start=(-1,7),end=(None,None),delim=","))
fun.addInputVariable(var,"DOT/of_grad.dat",TableReader(None,0,start=(1,0),end=(None,None)))
#fun.addPreProcessStep(preDirectRun)
fun.addValueEvalStep(internalMeshDeformationRun)
fun.addValueEvalStep(internalDirectRun)
fun.addGradientEvalStep(internalAdjointRun)
fun.addGradientEvalStep(internalDotProductRun)

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

driver.addDataFileToFetchAfterValueEval("DIRECT/restart_flow.dat")
driver.addDataFileToFetchAfterGradientEval("ADJOINT/solution_adj_cd.dat")

funcVal = driver.fun(np.array(designparams))
grad = driver.grad(np.array(designparams))

print ('Finished')



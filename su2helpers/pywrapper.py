import os
import shutil

import pysu2
import pysu2ad
import SU2

from evaluation import BasePyWrapper

class SU2CFDSingleZoneDriver(BasePyWrapper):
    def __init__(self, mainConfigName="config_tmpl.cfg", nZone=1, mpiComm=None):
        BasePyWrapper.__init__(self, mainConfigName, nZone, mpiComm)
    #end
        
    def run(self):
        # Initialize the corresponding driver of SU2, this includes solver preprocessing
        try:
            SU2Driver = pysu2.CSinglezoneDriver(self._mainConfigName, self._nZone, self._mpiComm)
        except TypeError as exception:
            print('A TypeError occured in pysu2.CDriver : ',exception)
            raise
          
        # Launch the solver for the entire computation
        SU2Driver.StartSolver()
        
        # Postprocess the solver and exit cleanly
        SU2Driver.Postprocessing()
        
        if SU2Driver != None:
          del SU2Driver
    #end
      
class SU2CFDSingleZoneDriverWithRestartOption(SU2CFDSingleZoneDriver):
    def __init__(self, mainConfigName="config_tmpl.cfg", nZone=1, mpiComm=None):
        SU2CFDSingleZoneDriver.__init__(self, mainConfigName, nZone, mpiComm)
        self._numberOfSuccessfulRuns = 0 #this variable will be used to indicate whether the restart option in config should be YES or NO
    #end    
    
    def preProcess(self):
        #by default RESTART_SOL=NO as on the initial step we don't have prior information
        #after the first iteration, this should be changed to YES
        if self._numberOfSuccessfulRuns > 0:
              #we are already inside the DIRECT folder, fetch the config and change the RESTART_SOL parameter
              config = SU2.io.Config(self._mainConfigName)
              config['RESTART_SOL'] = 'YES'
              config.dump(self._mainConfigName)
    #end
    
    def postProcess(self):
        self._numberOfSuccessfulRuns += 1
        #here one has to rename restart file to solution file that the adjoint solver can use
        #RESTART TO SOLUTION
        config = SU2.io.Config(self._mainConfigName)
        
        restart  = config.RESTART_FILENAME
        solution = config.SOLUTION_FILENAME
        if os.path.exists(restart):
            shutil.move( restart , solution )
    #end
#end

class SU2CFDDiscAdjSingleZoneDriver(BasePyWrapper):
    def __init__(self, mainConfigName="config_tmpl.cfg", nZone=1, mpiComm=None):
        BasePyWrapper.__init__(self, mainConfigName, nZone, mpiComm)
    #end
        
    def run(self):
        # Initialize the corresponding driver of SU2, this includes solver preprocessing
        try:
            SU2Driver = pysu2ad.CDiscAdjSinglezoneDriver(self._mainConfigName, self._nZone, self._mpiComm)
        except TypeError as exception:
            print('A TypeError occured in pysu2.CDriver : ',exception)
            raise
          
        # Launch the solver for the entire computation
        SU2Driver.StartSolver()
        
        # Postprocess the solver and exit cleanly
        SU2Driver.Postprocessing()
        
        if SU2Driver != None:
          del SU2Driver
    #end
    

class SU2CFDDiscAdjSingleZoneDriverWithRestartOption(SU2CFDDiscAdjSingleZoneDriver):
    def __init__(self, mainConfigName="config_tmpl.cfg", nZone=1, mpiComm=None):
        SU2CFDDiscAdjSingleZoneDriver.__init__(self, mainConfigName, nZone, mpiComm)
        self._numberOfSuccessfulRuns = 0 #this variable will be used to indicate whether the restart option in config should be YES or NO
    #end
    
    def preProcess(self):
        if self._numberOfSuccessfulRuns > 0:
              #we are already inside the ADJOINT folder, fetch the config and change the RESTART_SOL parameter
              config = SU2.io.Config(self._mainConfigName)
              config['RESTART_SOL'] = 'YES'
              config.dump(self._mainConfigName)
    #end
          
    def postProcess(self):
        self._numberOfSuccessfulRuns += 1
        #RESTART TO SOLUTION
        config = SU2.io.Config(self._mainConfigName)
        restart  = config.RESTART_ADJ_FILENAME
        solution = config.SOLUTION_ADJ_FILENAME
        # add suffix
        func_name = config.OBJECTIVE_FUNCTION
        suffix    = SU2.io.get_adjointSuffix(func_name)
        restart   = SU2.io.add_suffix(restart,suffix)
        solution  = SU2.io.add_suffix(solution,suffix)
        
        if os.path.exists(restart):
            shutil.move( restart , solution )
    #end
#end

class SU2DotProduct(BasePyWrapper):
    def __init__(self, mainConfigName="config_tmpl.cfg", nZone=1, mpiComm=None):
        BasePyWrapper.__init__(self, mainConfigName, nZone, mpiComm)
    #end
        
    def run(self):
        # Initialize the corresponding driver of SU2, this includes solver preprocessing
        try:
            SU2DotProduct = pysu2ad.CGradientProjection(self._mainConfigName, self._mpiComm)
        except TypeError as exception:
            print('A TypeError occured in pysu2ad.CGradientProjection : ',exception)
            raise
          
        # Launch the dot product
        SU2DotProduct.Run()
        
        if SU2DotProduct != None:
          del SU2DotProduct
    #end
#end
      
class SU2MeshDeformationSkipFirstIteration(BasePyWrapper):
    def __init__(self, mainConfigName="config_tmpl.cfg", nZone=1, mpiComm=None):
        BasePyWrapper.__init__(self, mainConfigName, nZone, mpiComm)
        self._isAlreadyCalledForTheFirstTime = False
    #end
        
    def run(self):
        if self._isAlreadyCalledForTheFirstTime: 
            try:
                SU2MeshDeformation = pysu2.CMeshDeformation(self._mainConfigName, self._mpiComm)
            except TypeError as exception:
                print('A TypeError occured in pysu2ad.CMeshDeformation : ',exception)
                raise
          
            # Launch the mesh deformation
            SU2MeshDeformation.Run()
        
            if SU2MeshDeformation != None:
              del SU2MeshDeformation
        else:
            config = SU2.io.Config(self._mainConfigName)
            mesh_name = config['MESH_FILENAME']
            mesh_out_name = config['MESH_OUT_FILENAME']
            if os.path.exists(mesh_name):
                shutil.copy( mesh_name , mesh_out_name )
                
            self._isAlreadyCalledForTheFirstTime = True
    #end
#end
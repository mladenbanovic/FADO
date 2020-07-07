import os
import shutil

import pysu2
import pysu2ad
import SU2

from evaluation import BasePyWrapper

class SU2CFDSingleZoneDriverWrapper(BasePyWrapper):
    def __init__(self,mainConfig=None,nZone=1,mpiComm=None):
        BasePyWrapper.__init__(self,"config_tmpl.cfg",mainConfig,nZone,mpiComm)
        
    def run(self):
        # Initialize the corresponding driver of SU2, this includes solver preprocessing
        try:
            cwd = os.getcwd()
            print(cwd)
            SU2Driver = pysu2.CSinglezoneDriver(self._configName, self._nZone, self._mpiComm)
        except TypeError as exception:
            print('A TypeError occured in pysu2.CDriver : ',exception)
            raise
          
        # Launch the solver for the entire computation
        SU2Driver.StartSolver()
        
        # Postprocess the solver and exit cleanly
        SU2Driver.Postprocessing()
        
        if SU2Driver != None:
          del SU2Driver
      
class SU2CFDSingleZoneDriverWrapperWithRestartOption(SU2CFDSingleZoneDriverWrapper):
    def __init__(self,mainConfig=None,nZone=1,mpiComm=None):
        SU2CFDSingleZoneDriverWrapper.__init__(self,mainConfig,nZone,mpiComm)
        self._numberOfSuccessfulRuns = 0 #this variable will be used to indicate whether the restart option in config should be YES or NO
    def preProcess(self):
        #by default RESTART_SOL=NO as on the initial step we don't have prior information
        #after the first iteration, this should be changed to YES
        if self._numberOfSuccessfulRuns > 0:
              #we are already inside the DIRECT folder, fetch the config and change the RESTART_SOL parameter
              config = SU2.io.Config(self._configName)
              config['RESTART_SOL'] = 'YES'
              config.dump(self._configName)
    
    def postProcess(self):
        self._numberOfSuccessfulRuns += 1
        #here one has to rename restart file to solution file that the adjoint solver can use
        #RESTART TO SOLUTION
        restart  = self._mainConfObject.RESTART_FILENAME
        solution = self._mainConfObject.SOLUTION_FILENAME
        if os.path.exists(restart):
            shutil.move( restart , solution )

class SU2CFDDiscAdjSingleZoneDriverWrapper(BasePyWrapper):
    def __init__(self,mainConfig=None,nZone=1,mpiComm=None):
        BasePyWrapper.__init__(self,"config_tmpl.cfg",mainConfig,nZone,mpiComm)
        
    def run(self):
        # Initialize the corresponding driver of SU2, this includes solver preprocessing
        try:
            SU2Driver = pysu2ad.CDiscAdjSinglezoneDriver(self._configName, self._nZone, self._mpiComm)
        except TypeError as exception:
            print('A TypeError occured in pysu2.CDriver : ',exception)
            raise
          
        # Launch the solver for the entire computation
        SU2Driver.StartSolver()
        
        # Postprocess the solver and exit cleanly
        SU2Driver.Postprocessing()
        
        if SU2Driver != None:
          del SU2Driver
    

class SU2CFDDiscAdjSingleZoneDriverWrapperWithRestartOption(SU2CFDDiscAdjSingleZoneDriverWrapper):
    def __init__(self,mainConfig=None,nZone=1,mpiComm=None):
        SU2CFDDiscAdjSingleZoneDriverWrapper.__init__(self,mainConfig,nZone,mpiComm)
        self._numberOfSuccessfulRuns = 0 #this variable will be used to indicate whether the restart option in config should be YES or NO
    
    def preProcess(self):
        if self._numberOfSuccessfulRuns > 0:
              #we are already inside the ADJOINT folder, fetch the config and change the RESTART_SOL parameter
              config = SU2.io.Config(self._configName)
              config['RESTART_SOL'] = 'YES'
              config.dump(self._configName)
          
    def postProcess(self):
        self._numberOfSuccessfulRuns += 1
        #RESTART TO SOLUTION
        restart  = self._mainConfObject.RESTART_ADJ_FILENAME
        solution = self._mainConfObject.SOLUTION_ADJ_FILENAME
        # add suffix
        func_name = self._mainConfObject.OBJECTIVE_FUNCTION
        suffix    = SU2.io.get_adjointSuffix(func_name)
        restart   = SU2.io.add_suffix(restart,suffix)
        solution  = SU2.io.add_suffix(solution,suffix)
        
        if os.path.exists(restart):
            shutil.move( restart , solution )

class SU2DotProductWrapper(BasePyWrapper):
    def __init__(self,mainConfig=None,nZone=1,mpiComm=None):
        BasePyWrapper.__init__(self,"config_tmpl.cfg",mainConfig,nZone,mpiComm)
        print("SU2DotProductWrapper constructor")
    
    def preProcess(self):
        pass
        
    def run(self):
        # Initialize the corresponding driver of SU2, this includes solver preprocessing
        try:
            SU2DotProduct = pysu2ad.CGradientProjection(self._configName, self._mpiComm)
        except TypeError as exception:
            print('A TypeError occured in pysu2ad.CGradientProjection : ',exception)
            raise
          
        # Launch the dot product
        SU2DotProduct.Run()
        
        if SU2DotProduct != None:
          del SU2DotProduct
          
    def postProcess(self):
        pass
      
class SU2MeshDeformationWrapperSkipFirstIteration(BasePyWrapper):
    def __init__(self,mainConfig=None,nZone=1,mpiComm=None):
        BasePyWrapper.__init__(self,"config_tmpl.cfg",mainConfig,nZone,mpiComm)
        print("SU2MeshDeformationWrapperSkipFirstIteration constructor")
        self._isAlreadyCalledForTheFirstTime = False
    
    def preProcess(self):
        pass
        
    def run(self):
        if self._isAlreadyCalledForTheFirstTime: 
            try:
                SU2MeshDeformation = pysu2.CMeshDeformation(self._configName, self._mpiComm)
            except TypeError as exception:
                print('A TypeError occured in pysu2ad.CMeshDeformation : ',exception)
                raise
          
            # Launch the mesh deformation
            SU2MeshDeformation.Run()
            print ("SU2MeshDeformation successfully evaluated")
        
            if SU2MeshDeformation != None:
              del SU2MeshDeformation
        else:
            config = SU2.io.Config(self._configName)
            mesh_name = config['MESH_FILENAME']
            mesh_out_name = config['MESH_OUT_FILENAME']
            if os.path.exists(mesh_name):
                shutil.copy( mesh_name , mesh_out_name )
                
            self._isAlreadyCalledForTheFirstTime = True
            
          
    def postProcess(self):
        pass
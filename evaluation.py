#  Copyright 2019-2020, Pedro Gomes.
#
#  This file is part of FADO.
#
#  FADO is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  FADO is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with FADO.  If not, see <https://www.gnu.org/licenses/>.

import os
import shutil
import subprocess as sp
import abc

class BaseRun(abc.ABC):
    def __init__(self,workDir,useSymLinks=False):
        self._dataFiles = []
        self._confFiles = []
        self._expectedFiles = []
        self._workDir = workDir
        self._symLinks = useSymLinks
        self._maxTries = 1
        self._numTries = 0
        self._variables = set()
        self._parameters = []
        self._stdout = None
        self._stderr = None
        self.finalize()
        
    @abc.abstractmethod
    def initialize(self):
        return NotImplemented
      
    @abc.abstractmethod
    def run(self):
        return NotImplemented
      
    #perhaps one should define poll also here for parallel runs
        
    def _addAbsoluteFile(self,file,flist):
        file = os.path.abspath(file)
        if not os.path.isfile(file):
            raise ValueError("File '"+file+"' not found.")
        flist.append(file)

    def addData(self,file,location="auto"):
        """
        Adds a "data" file to the run, an immutable dependency of the process.

        Parameters
        ----------
        file     : Path to the file.
        location : Type of path, "relative" (to the parent of "dir"), "absolute" (the path
                   is immediately converted to an absolute path, the file must exist),
                   or "auto" (tries "absolute" first, reverts to "relative"). 
        """
        if location is "relative":
            self._dataFiles.append(file)
        else:
            try:
                self._addAbsoluteFile(file,self._dataFiles)
            except:
                if location is "absolute": raise
                # in "auto" mode, if absolute fails consider relative
                else: self._dataFiles.append(file)
            #end
        #end
    #end

    def addConfig(self,file):
        """Add a "configuration" file to the run, a mutable dependency onto which
        Parameters and Variables are written. The path ("file") is converted
        to absolute immediately."""
        self._addAbsoluteFile(file,self._confFiles)

    def addParameter(self,param):
        """Add a parameter to the run. Parameters are written to the configuration
        files before variables."""
        self._parameters.append(param)

    def addExpected(self,file):
        """Add an expected (output) file of the run, the presence of all expected
        files in the working subdirectory indicates that the run succeeded."""
        self._expectedFiles.append(os.path.join(self._workDir,file))

    def setMaxTries(self,num):
        """Sets the maximum number of times a run is re-tried should it fail."""
        self._maxTries = num

    def getParameters(self):
        return self._parameters

    def updateVariables(self,variables):
        """
        Update the set of variables associated with the run. This method is intended
        to be part of the preprocessing done by driver classes. Unlike addParameter,
        users do not need to call it explicitly.
        """
        self._variables.update(variables)
        
    def isIni(self):
        """Return True if the run was initialized."""
        return self._isIni

    def isRun(self):
        """Return True if the run has finished."""
        return self._isRun
    
    def finalize(self):
        """Reset "lazy" flags, close the stdout and stderr of the process."""
        try:
            self._stdout.close()
            self._stderr.close()
        except:
            pass
        self._isIni = False
        self._isRun = False
        self._retcode = -100
    #end

    # check whether expected files were created
    def _success(self):
        for file in self._expectedFiles:
            if not os.path.isfile(file): return False
        return True
    #end

class ExternalRun(BaseRun):
    """
    Defines the execution of an external code (managed via Popen).
    A lazy execution model is used, once run, a new process will not be started
    until the "lazy" flags are explicitly cleared via "finalize()".

    Parameters
    ----------
    dir         : The subdirectory within which the command will be run.
    command     : The shell command used to create the external process.
    useSymLinks : If set to True, symbolic links are used for "data" files instead of copies.
    """
    def __init__(self,workDir,command,useSymLinks=False):
        BaseRun.__init__(self, workDir, useSymLinks)
        self._command = command
        self._process = None

    def initialize(self):
        """
        Initialize the run, create the subdirectory, copy/symlink the data and
        configuration files, and write the parameters and variables to the latter.
        """
        if self._isIni: return

        os.mkdir(self._workDir)
        for file in self._dataFiles:
            target = os.path.join(self._workDir,os.path.basename(file))
            (shutil.copy,os.symlink)[self._symLinks](os.path.abspath(file),target)

        for file in self._confFiles:
            target = os.path.join(self._workDir,os.path.basename(file))
            shutil.copy(file,target)
            for par in self._parameters:
                par.writeToFile(target)
            for var in self._variables:
                var.writeToFile(target)

        self._createProcess()
        self._isIni = True
        self._isRun = False
        self._numTries = 0
    #end

    def _createProcess(self):
        self._stdout = open(os.path.join(self._workDir,"stdout.txt"),"w")
        self._stderr = open(os.path.join(self._workDir,"stderr.txt"),"w")

        self._process = sp.Popen(self._command,cwd=self._workDir,
                        shell=True,stdout=self._stdout,stderr=self._stderr)
    #end

    def run(self,timeout=None):
        """Start the process and wait for it to finish."""
        if not self._isIni:
            raise RuntimeError("Run was not initialized.")
        if self._numTries == self._maxTries:
            raise RuntimeError("Run failed.")
        if self._isRun:
            return self._retcode

        self._retcode = self._process.wait(timeout)
        self._numTries += 1

        if not self._success():
            self.finalize()
            self._createProcess()
            self._isIni = True
            return self.run(timeout)
        #end

        self._numTries = 0
        self._isRun = True
        return self._retcode
    #end

    def poll(self):
        """Polls the state of the process, does not wait for it to finish."""
        if not self._isIni:
            raise RuntimeError("Run was not initialized.")
        if self._numTries == self._maxTries:
            raise RuntimeError("Run failed.")
        if self._isRun:
            return self._retcode

        if self._process.poll() is not None:
            self._numTries += 1

            if not self._success():
                self.finalize()
                self._createProcess()
                self._isIni = True
                return self.poll()
            #end

            self._numTries = 0
            self._retcode = self._process.returncode
            self._isRun = True
        #end

        return self._retcode
    #end
#end

class BasePyWrapper(abc.ABC):
    def __init__(self,configName="config_tmpl.cfg",mainConfig=None,nZone=1,mpiComm=None):
        self._configName = configName
        self._mainConfObject = mainConfig
        self._nZone = nZone
        self._mpiComm = mpiComm
        print("BaseWrapper constructor")
        
    def preProcess(self):
        pass
    
    @abc.abstractmethod
    def run(self):
        return NotImplemented
    
    def postProcess(self):
        pass
    
    def setMainConfig(self,config):
        self._mainConfObject = config
        print("Config provided")


class InternalRun(BaseRun):
    """
    Defines execution of an internal code via pywrappers.
    """
    def __init__(self,workDir,pywrapperObject,useSymLinks=False):
        if not isinstance(pywrapperObject, BasePyWrapper):
            raise TypeError('Expected instance of BasePyWrapper; got %s' % type(pywrapperObject).__name__)
        BaseRun.__init__(self, workDir, useSymLinks)
        self._pywrapperObject = pywrapperObject

    def initialize(self):
        """
        Initialize the run, create the subdirectory, copy/symlink the data and
        configuration files, and write the parameters and variables to the latter.
        """
        if self._isIni: return

        os.mkdir(self._workDir)
        for file in self._dataFiles:
            target = os.path.join(self._workDir,os.path.basename(file))
            (shutil.copy,os.symlink)[self._symLinks](os.path.abspath(file),target)

        for file in self._confFiles:
            target = os.path.join(self._workDir,os.path.basename(file))
            shutil.copy(file,target)
            for par in self._parameters:
                par.writeToFile(target)
            for var in self._variables:
                var.writeToFile(target)

        self._isIni = True
        self._isRun = False
        self._numTries = 0
    #end

    def run(self):
        """Start the process and wait for it to finish."""
        if not self._isIni:
            raise RuntimeError("Run was not initialized.")
        if self._numTries == self._maxTries:
            raise RuntimeError("Run failed.")
        if self._isRun:
            return self._retcode
        
        try:
            preExecutionDir = os.getcwd()
            #change to workDir
            os.chdir(self._workDir)
            #execute preProcess
            self._pywrapperObject.preProcess()
            #execute run method
            self._pywrapperObject.run()
            #execute postProcess
            self._pywrapperObject.postProcess()
            #after run is executed, go back
            os.chdir(preExecutionDir)
            self._retcode = 1
        except TypeError as exception:
            self._retcode = -1
            print('A TypeError occured: ',exception)
            
        self._numTries += 1

        if not self._success():
            self.finalize()
            self._isIni = True
            return self.run()
        #end

        self._numTries = 0
        self._isRun = True
        return self._retcode
    #end
#end
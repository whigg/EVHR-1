
import subprocess

from EvhrEngine.models import EvhrError

#-------------------------------------------------------------------------------
# class SystemCommand
#-------------------------------------------------------------------------------
class SystemCommand(object):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cmd, inFile, logger, constituent = None):

        self.cmd        = cmd
        self.logger     = logger
        self.returnCode = None
        
        process = subprocess.Popen(self.cmd, 
                                   shell = True,
                                   stderr = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   close_fds = True)

        self.returnCode = process.returncode
        
        if self.returnCode:
            
            err = EvhrError(constituent, inFile, cmd, process.communicate()[1])
            err.save()

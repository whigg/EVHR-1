
import subprocess

from EvhrEngine.models import EvhrError

#-------------------------------------------------------------------------------
# class SystemCommand
#-------------------------------------------------------------------------------
class SystemCommand(object):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cmd, inFile, logger, request = None, 
                 raiseException = False):

        self.cmd    = cmd
        self.logger = logger
        
        process = subprocess.Popen(self.cmd, 
                                   shell = True,
                                   stderr = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   close_fds = True)

        self.returnCode = process.returncode
        self.msg = process.communicate()[1]
        
        if self.returnCode:
            
            err = EvhrError(request, inFile, cmd, self.msg)
            err.save()
            
            if raiseException:
                
                msg = 'A system command error occurred.  ' + str(self.msg)
                raise RuntimeError(msg)

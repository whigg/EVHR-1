
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

        if logger:
            logger.info(cmd)
            
        process = subprocess.Popen(cmd, 
                                   shell = True,
                                   stderr = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   close_fds = True)

        self.returnCode = process.returncode
        self.msg = process.communicate()[1]
        
        if logger:

            logger.info('Return code: ' + str(self.returnCode))
            logger.info('Message: ' + str(self.msg))
            
        if self.returnCode:
            
            err = EvhrError(request, inFile, cmd, self.msg)
            err.save()
            
            if raiseException:
                
                msg = 'A system command error occurred.  ' + str(self.msg)
                raise RuntimeError(msg)

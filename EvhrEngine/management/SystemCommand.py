
import subprocess

from EvhrEngine.models import EvhrError

#-------------------------------------------------------------------------------
# class SystemCommand
#-------------------------------------------------------------------------------
class SystemCommand(object):

    ERROR_STRINGS_TO_TEST = [ \
        'traceback',
        'error',
        'command not found',
        'stale file handle',
        'failed to access']
        
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
            
        #---
        # There are cases where the shell command fails and still returns a 0,
        # causing returnCode to be None.  To detect this, check if msg contains
        # and error text.
        #---
        lcMsg = self.msg.lower()
        hasErrorString = False
        
        for eMsg in SystemCommand.ERROR_STRING_TO_TEST:
            
            if lcMsg.find(eMsg) != -1:

                hasErrorString = True
                break
        
        # if self.returnCode or self.msg.startswith('Traceback'):
        if self.returnCode or hasErrorString:
            
            err             = EvhrError()
            err.request     = request
            err.inputFile   = inFile
            err.errorOutput = self.msg
            err.command     = cmd
            err.save()
            
            if raiseException:
                
                msg = 'A system command error occurred.  ' + str(self.msg)
                raise RuntimeError(msg)

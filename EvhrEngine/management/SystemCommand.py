
import logging
import subprocess

from django.conf import settings

from EvhrEngine.models import EvhrError
from EvhrEngine.models import EvhrNode
from EvhrEngine.models import EvhrNodeGroup
from EvhrEngine.models import EvhrNodePID

#-------------------------------------------------------------------------------
# class SystemCommand
#-------------------------------------------------------------------------------
class SystemCommand(object):

    NODE_FAILURE_MSG = 'ssh exited with exit code 255'
    RANSAC_MSG = 'ransac'
    
    # These must be in lower case.
    ERROR_STRINGS_TO_TEST = [ \
        'aborted',
        'command not found',
        'exiting',
        'error',
        'failed to access',
        NODE_FAILURE_MSG,
        'no such file or directory',
        RANSAC_MSG,
        'segmentation fault',
        'stale file handle',
        'stereogrammetry unsuccessful',
        'traceback']
        
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cmd, inFile, logger, request=None, raiseException=False,
                 distribute=False):

        self.msg = None
        self.returnCode = None
        self.stdOut = None

        if not logger:
            logger = logging.getLogger('console') # standard output.
            
        if distribute:
            self.distribute(cmd, inFile, logger, request, raiseException)
            
        else:
            self.runSingleProcess(cmd, inFile, logger, request, raiseException)
            
    #---------------------------------------------------------------------------
    # distribute
    #---------------------------------------------------------------------------
    def distribute(self, cmd, inFile, logger, request, raiseException):
        
        origCmd = cmd
        
        # Get the candidate nodes on which to run.
        nodes = []
        
        if hasattr(settings, 'NODE_GROUP'):

            # Ensure the node group exists and is enabled.
            if EvhrNodeGroup.objects.filter(name=settings.NODE_GROUP,
                                            enabled=True).count() == 0:
                
                msg = 'Node group, ' + \
                      str(settings.NODE_GROUP) + \
                      ', does not exist or is disabled.'
                      
                if logger:
                    logger.error(msg)
                    
                if raiseException:
                    raise RuntimeError(msg)
                
            # Get the nodes in the group.                                 
            nodes = EvhrNode.objects.filter(group=settings.NODE_GROUP,
                                            enabled=True)
            
        # Decide which node is least busy and use it.
        nodeToUse = None
        maxPIDs = 10000

        for node in nodes:
            
            nodePIDs = EvhrNodePID.objects.filter(node=node)
            numPIDs = len(nodePIDs)
            
            if numPIDs == 0:
                
                nodeToUse = node
                break
                
            elif numPIDs < maxPIDs:
                
                maxPIDs = numPIDs
                nodeToUse = node
            
        if nodeToUse == None:
           
           if logger:
               logger.info('Unable to choose a node for pdsh to use, so ' + \
                           'running on the local node.')
        else: 
                      
            if logger:
                logger.info('Using node ' + str(nodeToUse.name)) 

            # Wrap the command in pdsh and inside single quotes
            cmd = "pdsh -w {} '{}'".format(nodeToUse.name, cmd)

        # Run the pdsh version using runSingleProcess.
        self.runSingleProcess(cmd, inFile, logger, request, raiseException, 
                              nodeToUse)
        
    #---------------------------------------------------------------------------
    # runSingleProcess
    #---------------------------------------------------------------------------
    def runSingleProcess(self, cmd, inFile, logger, request, raiseException,
                         node=None):
        
        if logger:
            logger.info('Cmd: ' + str(cmd))
            
        # Launch the command.
        process = subprocess.Popen(cmd, 
                                   shell = True,
                                   stderr = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   close_fds = True)

        # If a node was passed, save its PID.  This tracks node usage.
        nodePID = None
        
        if node:
            
            nodePID = EvhrNodePID()
            nodePID.node = node
            nodePID.pid = process.pid
            nodePID.save()
            
        self.returnCode = process.returncode
        stdOutStdErr = process.communicate()    # This makes Popen block.
        self.stdOut = stdOutStdErr[0]
        self.msg = stdOutStdErr[1]
        
        #---
        # The process blocked on the communicate statement, so now it has
        # finished and the PID must be deleted to indicate less use of the node.
        #---
        if nodePID:
            nodePID.delete()
            
        if logger:

            logger.info('Return code: ' + str(self.returnCode))
            logger.info('Message: ' + str(self.msg))
            
        #---
        # There are cases where the shell command fails and still returns a 0,
        # causing returnCode to be None.  To detect this, check if msg contains
        # and error text.
        #---
        lcMsg = self.msg.lower()
        lcStdOut = self.stdOut.lower()
        error = None
        
        for eMsg in SystemCommand.ERROR_STRINGS_TO_TEST:
            
            if lcMsg.find(eMsg) != -1:

                if SystemCommand.NODE_FAILURE_MSG in lcMsg:
                    logger.warning('Node failed. ' + str(self.msg))
                    
                error = self.msg
                break
        
            elif lcStdOut.find(eMsg) != -1:

                if SystemCommand.NODE_FAILURE_MSG in lcStdOut:
                    logger.warning('Node failed. ' + str(self.stdOut))
                    
                error = self.stdOut
                break
        
        if self.returnCode or error:
            
            if request != None:
            
                err             = EvhrError()
                err.request     = request
                err.inputFile   = inFile
                err.errorOutput = error
                err.command     = cmd
                err.save()
            
            if raiseException:
                
                msg = 'A system command error occurred.  ' + \
                      error + \
                      ' Command: ' + str(cmd)
                      
                raise RuntimeError(msg)

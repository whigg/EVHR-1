
from ProcessingEngine.management.ConstituentProcessor \
    import ConstituentProcessor

from ProcessingEngine.management.Distributor import Distributor

#-------------------------------------------------------------------------------
# PythonMapDistributor
#-------------------------------------------------------------------------------
class PythonMapDistributor(Distributor):
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cpList, maxRunning, logger):
        
        super(PythonMapDistributor, self).__init__(cpList, maxRunning, logger)

    #---------------------------------------------------------------------------
    # myDistribute
    #---------------------------------------------------------------------------
    def myDistribute(self):

        # Python's map() needs a list of the first args, second args, etc.
        retrieverArgs        = []
        inputFileArgs        = []
        constituentFilesArgs = []
        constituentArgs      = []
        parentArgs           = []
        loggerArgs           = []
        errorQueueArgs       = []
    
        for cp in self.constituentProcessors:

            retrieverArgs.append(cp.retriever)
            inputFileArgs.append(cp.inputFile)
            constituentFilesArgs.append(cp.constituentFiles)
            constituentArgs.append(cp.constituent)
            parentArgs.append(cp.parent)
            loggerArgs.append(cp.logger)
            errorQueueArgs

        mapArgs = [retrieverArgs, 
                   inputFileArgs, 
                   constituentFilesArgs, 
                   constituentArgs,
                   parentArgs,
                   loggerArgs]

        try:
            map(ConstituentProcessor.process, *mapArgs)

        except Exception as e:

            msg = traceback.format_exc()

            if logger:
                logger.info(msg)
            
            else:
                print msg
                
            return False
        
        return True
            
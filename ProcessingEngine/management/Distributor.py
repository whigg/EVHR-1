
import multiprocessing

#-------------------------------------------------------------------------------
# Distributor
#-------------------------------------------------------------------------------
class Distributor(object):
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cpList, maxRunning = 1, logger = None):
        
        self.constituentProcessors = cpList
        self.logger = logger
        self.maxRunning = maxRunning

        #---
        # Use a queue to collect failure status from distributed 
        # ConstituentProcessors.
        #---
        self.errorQueue = multiprocessing.Queue()
            
    #---------------------------------------------------------------------------
    # distribute
    #
    # This method, called by RequestProcessor, tracks the overall success of
    # its Constituents, returning False when an error occurs.
    #---------------------------------------------------------------------------
    def distribute(self):

        success = False
        
        #---
        # Short circuit the distribution, if the retriever can only handle 
        # sequential processing.
        #---
        if self.maxRunning == 1:
        
            for cp in self.constituentProcessors:
                cp(self.errorQueue)

            success = self.errorQueue.empty()
            
        else:
        
            success = self.myDistribute()
            
        return success

    #---------------------------------------------------------------------------
    # myDistribute
    #---------------------------------------------------------------------------
    def myDistribute(self):
        
        raise RuntimeError('This must be implemented by subclasses.')

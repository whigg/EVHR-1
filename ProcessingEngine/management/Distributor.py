
import multiprocessing

#-------------------------------------------------------------------------------
# Distributor
#-------------------------------------------------------------------------------
class Distributor(object):
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cpList, maxRunning, logger = None):
        
        self.constituentProcessors = cpList
        self.logger = logger
        self.maxRunning = maxRunning
        
        if self.maxRunning == -1:
            self.maxRunning = len(cpList)

        if self.logger:
            
            self.logger.info('Distributor will run up to ' + \
                             str(self.maxRunning) + \
                             ' constituents simultaneously because' + \
                             ' maxRunning = ' + \
                             str(maxRunning) + \
                             ' and there are ' + \
                             str(len(cpList)) + \
                             ' constituents.')

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

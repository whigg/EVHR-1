
import multiprocessing
import time
import traceback

from django import db

from ProcessingEngine.management.Distributor import Distributor

#-------------------------------------------------------------------------------
# PythonMultiprocessingDistributor
#-------------------------------------------------------------------------------
class PythonMultiprocessingDistributor(Distributor):
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, cpList, maxRunning, logger):
        
        super(PythonMultiprocessingDistributor, self).__init__(cpList, 
                                                               maxRunning, 
                                                               logger)
        
    #---------------------------------------------------------------------------
    # myDistribute
    #---------------------------------------------------------------------------
    def myDistribute(self):

        # Queue the predictor files that need to run.
        return self.processQueue()

    #---------------------------------------------------------------------------
    # processQueue
    #---------------------------------------------------------------------------
    def processQueue(self):
        
        try:
            threads = []

            while len(self.constituentProcessors) > 0:

                # Track when threads finish.
                numRunning = 0

                for thread in threads:
                    
                    if thread.is_alive():
                        
                        numRunning += 1
                        
                    else:
                        threads.remove(thread)

                if self.logger:
                    self.logger.info(str(numRunning) + \
                                     ' of ' + \
                                     str(self.maxRunning) + \
                                     ' maximum constituents running.')

                # Spawn threads.
                for i in range(numRunning, self.maxRunning):

                    if len(self.constituentProcessors) < 1:
                        break
                        
                    constituentProcessor = self.constituentProcessors.pop()
                    
                    thread = multiprocessing.\
                             Process(target=constituentProcessor,
                                     args=(self.errorQueue,))
                    
                    threads.append(thread)
                    db.connections.close_all()
                    thread.start()

                time.sleep(1)
        
        except Exception as e:
            
            if self.logger:
                self.logger.info(traceback.format_exc())

            raise e

        # Await the final threads.
        for thread in threads:
            thread.join()
        
        return self.errorQueue.empty()

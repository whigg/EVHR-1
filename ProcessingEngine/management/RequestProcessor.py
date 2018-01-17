
import importlib            # for import_module
import logging
import multiprocessing
import os
import time
import traceback

from django import db

from ProcessingEngine.management.ConstituentProcessor import ConstituentProcessor
from ProcessingEngine.models import Constituent
from ProcessingEngine.models import RequestProcess

#-------------------------------------------------------------------------------
# RequestProcessor
#
# This class manages the processing of one Request.
#-------------------------------------------------------------------------------
class RequestProcessor():
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, numProcs = 1, logger = None):
        
        if not request:
            raise RuntimeError('A request must be provided.')
            
        self.logger                = logger
        self.numProcs              = numProcs
        self.constituentProcessors = []
        self.process               = None
        self.request               = request
        self.retriever             = None

    #---------------------------------------------------------------------------
    # __call__
    #---------------------------------------------------------------------------
    def __call__(self):
        
        # Register that this instance is running.
        if self.logger:
            self.logger.info('Registering process for ' +  self.request.name)
        
        self.process         = RequestProcess()
        self.process.request = self.request
        self.process.pid     = os.getpid()
        self.process.save()

        self.request.started = True
        self.request.save(update_fields = ['started'])

        try:

            self.retriever = self.chooseRetriever()

            #---
            # Retrievers can set the maximum processors they allow.  For
            # example, MODIS can only support one at a time because its
            # access uses FTP.  When multiple processes are attempted,
            # you are asking MODIS to work out of multiple FTP directories
            # from a single connection.
            #---
            self.maxRunning = min(self.retriever.maxProcesses, self.numProcs)

            # Set up the retriever.
            if self.logger:
                self.logger.info('Getting constituents for ' +self.request.name)
        
            constituentFileDict = self.retriever.listConstituents()
            aggregateDict       = dict(constituentFileDict)
        
            if not constituentFileDict or len(constituentFileDict) == 0:
                raise RuntimeError('No constituents files found.')
                
            if self.logger:
                self.logger.info('Constituents: ' + str(constituentFileDict))
                
            #---
            # Instantiate the ConstituentProcessors, so the Constituents
            # will exist in the database and report the correct status.
            #---
            while len(constituentFileDict) > 0:
                
                oneConstituentAndFiles = constituentFileDict.popitem()

                cProcessor = ConstituentProcessor(self.request,
                                                  self.retriever, 
                                                  self.process,   
                                                  oneConstituentAndFiles,
                                                  self.logger)
                                                  
                self.constituentProcessors.append(cProcessor)
                
            # Queue the predictor files that need to run.
            exceptionOccurred = self.processQueue()
        
            if exceptionOccurred:
                
                raise RuntimeError('RequestProcessor.processQueue() thinks ' +
                                   'an exception occurred.  It should be ' +
                                   'logged.')

            # Reduce the constituentss to the final result.
            if self.logger:
                self.logger.info('Aggregating constituents for ' + 
                                 self.request.name)
    
            aggFile = self.retriever.aggregate(aggregateDict)

            # If aggregation returns a file, create a Constituent for it.
            if aggFile != None:
                
                ac             = Constituent()
                ac.request     = self.request
                ac.destination = aggFile
                ac.started     = True
                ac.save()
            
            self.request.aggregationComplete = True
            self.request.save(update_fields = ['aggregationComplete'])
                
        except Exception as e:
            
            if self.logger:

                self.logger.info(traceback.format_exc())

            else:
                print traceback.format_exc()
                
            self.cleanUp()
            raise e
            
        # Register that this instance is not running.
        if self.logger:
            self.logger.info('Completed request process for ' + 
                             self.predictor.name)
        
        self.process.delete()

    #---------------------------------------------------------------------------
    # chooseRetriever
    #---------------------------------------------------------------------------
    def chooseRetriever(self):
        
        mod = importlib.import_module(self.request.endPoint.protocol.module)
        classObj = getattr(mod, self.request.endPoint.protocol.className)
        return classObj(self.request, self.logger)
            
    #---------------------------------------------------------------------------
    # cleanUp
    #
    # Certain events, like <Ctrl-c>, bypass this classes efforts to clean
    # up after itself.  Python's __del__ is unreliable because there is
    # no guarantee of the order of deletion of data members.  The process
    # data member could be deleted from the class before it can be 
    # deleted from the database.  
    #---------------------------------------------------------------------------
    def cleanUp(self):
        
        if self.logger:
            self.logger.info('In RequestProcessor.cleanUp()')
            
        if self.process and self.process.id != None:

            for constituentProcessor in self.constituentProcessors:
                constituentProcessor.cleanUp()
                
            if self.logger:
                self.logger.info('Deregistering request process for ' + 
                                 self.request.name)

            self.process.delete()
        
    #--------------------------------------------------------------------
    # processQueue
    #--------------------------------------------------------------------
    def processQueue(self):
        
        errorQueue = multiprocessing.Queue()
        
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

                # Spawn threads.
                for i in range(numRunning + 1, self.maxRunning + 1):

                    if len(self.constituentProcessors) < 1:
                        break
                        
                    constituentProcessor = self.constituentProcessors.pop()
                    
                    thread = multiprocessing.\
                        Process(target = constituentProcessor,
                                args   = (errorQueue,))
                    
                    threads.append(thread)
                    db.connections.close_all()
                    thread.start()

                time.sleep(1)
        
        except Exception as e:
            
            if self.logger:
                self.logger.info(traceback.format_exc())

            self.cleanUp()
            raise e

        # Await the final threads.
        for thread in threads:
            thread.join()
        
        return not errorQueue.empty()
    
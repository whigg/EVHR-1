
import logging
import os
import signal
import traceback

from ProcessingEngine.models import Constituent
from ProcessingEngine.models import ConstituentProcess

#-------------------------------------------------------------------------------
# ConstituentProcessor
#
# This class manages the processing of one constituent.
#-------------------------------------------------------------------------------
class ConstituentProcessor():
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, retriever, requestProcess,
                 oneConstituentAndFiles, logger = None):
        
        if not request:
            raise RuntimeError('A request must be provided.')
            
        if not retriever:
            raise RuntimeError('A retriever must be provided.')
            
        if not oneConstituentAndFiles:
            raise RuntimeError('A constituent to file list must be provided.')
                               
        if not requestProcess:
            raise RuntimeError('A RequestProcess must be provided.')
            
        #---
        # Constituent files are a list of all the files comprising
        # this one Constituent.  For example, MODIS is comprised of many
        # tiles mosaicked into one Constituent.  The tiles are its files.
        #---
        self.constituentFiles = oneConstituentAndFiles[1]

        #---
        # The RequestProcess is passed so this class can associate the
        # ConstituentProcesses it creates with their parent.  This relationship
        # exists, so the database can cascade RequestProcess deletions
        # through its children.
        #---
        self.parent = requestProcess
        
        # Create the Constituent.
        self.constituent         = Constituent()
        self.constituent.request = request
        self.constituent.save()
        
        self.retriever = retriever
        self.inputFile = oneConstituentAndFiles[0]
        self.logger    = logger
        self.constituentProcess = None
        
    #---------------------------------------------------------------------------
    # __call__
    #---------------------------------------------------------------------------
    def __call__(self, errorQueue):
        
        success = ConstituentProcessor.process(self.retriever,
                                               self.inputFile,
                                               self.constituentFiles,
                                               self.constituent,
                                               self.parent,
                                               self.logger)
                                               
        if errorQueue and not success:
            errorQueue.put(True)
        
    #---------------------------------------------------------------------------
    # cleanUp
    #---------------------------------------------------------------------------
    @staticmethod
    def cleanUp(constituentProcess, constituent, logger):
        
        if constituentProcess and constituentProcess.id != None:

            #---
            # This should be unnecessary; however, there is a case where
            # constituent state goes from running to failed to complete.  This
            # is the only place where its process is deleted.  A constituent
            # with no process that is unavailable has failed.  Does it have an
            # actual file here?
            #---
            cID = constituent.id
            
            try:
                constituent = Constituent.objects.get(id = cID)
                
                if not constituent.destination or \
                   constituent.destination == '' or \
                   not os.path.exists(constituent.destination.name):
                   
                    msg = 'Constituent ' + str(cID) + ' has no ' + \
                          'actual file.  Constituent: ' + \
                          str(constituent.destination.name)
                         
                    if logger:
                        logger.info(msg)
                        
                    else:
                        print msg
                
            except:
                
                msg = 'Unable to read constituent ' + str(cID)
                
                if logger:

                    logger.info(msg)
                    logger.info(traceback.format_exc())
                    
                else:

                    print msg
                    print traceback.format_exc()

            msg = 'Deregistering constituent process for ' + \
                  constituent.getName()
                  
            if logger:
                logger.info(msg)
                
            else:
                print msg

            constituentProcess.delete()

    #---------------------------------------------------------------------------
    # process
    #
    # This static version is used for distributed processing in some cases.
    #---------------------------------------------------------------------------
    @staticmethod
    def process(retriever, inputFile, constituentFiles, constituent, parent, 
                logger):
        
        success = False
        
        try:

            # Register that this instance is running.
            if logger:
                logger.info('Registering constituent process for ' + 
                            constituent.getName())
        
            cProcess             = ConstituentProcess()
            cProcess.constituent = constituent
            cProcess.parent      = parent
            cProcess.pid         = os.getpid()
            cProcess.save()

            constituent.started = True
            constituent.save(update_fields = ['started'])
        
            constituent.destination = \
                retriever.retrieveOne(inputFile, constituentFiles)
                                          
            constituent.save()
            success = True
        
        except Exception as e:

            msg = traceback.format_exc()

            if logger:
                logger.info(msg)
                
            else:
                print msg
                
        ConstituentProcessor.cleanUp(cProcess, constituent, logger)

        return success
        

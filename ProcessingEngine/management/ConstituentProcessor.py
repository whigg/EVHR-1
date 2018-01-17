
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
        self.process   = None
        
    #---------------------------------------------------------------------------
    # __call__
    #---------------------------------------------------------------------------
    def __call__(self, errorQueue):
        
        self.process = None
        
        try:

            # Register that this instance is running.
            if self.logger:
                self.logger.info('Registering constituent process for ' + 
                                 self.constituent.getName())
        
            self.process             = ConstituentProcess()
            self.process.constituent = self.constituent
            self.process.parent      = self.parent
            self.process.pid         = os.getpid()
            self.process.save()

            self.constituent.started = True
            self.constituent.save(update_fields = ['started'])
        
            self.constituent.destination = \
                self.retriever.retrieveOne(self.inputFile, \
                                           self.constituentFiles)
                                          
            self.constituent.save()
        
        except Exception as e:

            msg = traceback.format_exc()

            if self.logger:
                self.logger.info(msg)
                
            else:
                print msg
                
            errorQueue.put(True)

        self.cleanUp()
        
    #---------------------------------------------------------------------------
    # cleanUp
    #---------------------------------------------------------------------------
    def cleanUp(self):
        
        if self.process and self.process.id != None:

            #---
            # This should be unnecessary; however, there is a case where
            # constituent state goes from running to failed to complete.  This
            # is the only place where its process is deleted.  A constituent
            # with no process that is unavailable has failed.  Does it have an
            # actual file here?
            #---
            cID = self.constituent.id
            
            try:
                constituent = Constituent.objects.get(id = cID)
                
                if not constituent.destination or \
                   constituent.destination == '' or \
                   not os.path.exists(constituent.destination.name):
                   
                    msg = 'Constituent ' + str(cID) + ' has no ' + \
                          'actual file.  Constituent: ' + \
                          str(constituent.destination.name)
                         
                    if self.logger:
                        self.logger.info(msg)
                        
                    else:
                        print msg
                
            except:
                
                msg = 'Unable to read constituent ' + str(cID)
                
                if self.logger:

                    self.logger.info(msg)
                    self.logger.info(traceback.format_exc())
                    
                else:

                    print msg
                    print traceback.format_exc()

            msg = 'Deregistering constituent process for ' + \
                  self.constituent.getName()
                  
            if self.logger:
                self.logger.info(msg)
                
            else:
                print msg

            self.process.delete()
            self.process = None


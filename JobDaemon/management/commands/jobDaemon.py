import logging
import multiprocessing
import os
import sys
import time
import traceback

from django import db
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import InterfaceError

from ProcessingEngine.management.RequestProcessor import RequestProcessor
from ProcessingEngine.models import ConstituentProcess
from ProcessingEngine.models import Request
from ProcessingEngine.models import RequestProcess

from JobDaemon import models
from JobDaemon.management.commands import purgeRequests
from JobDaemon.management.commands import purgeRequestDirs
from JobDaemon.management.commands import purgeZipFiles

requestTypes = []

if 'GeoProcessingEngine' in settings.INSTALLED_APPS:

    from GeoProcessingEngine.models import GeoRequest
    requestTypes.append('georequest')
    
if 'Loader' in settings.INSTALLED_APPS:
    
    from Loader.models import LoaderRequest
    requestTypes.append('loaderrequest')
    
#-------------------------------------------------------------------------------
# Command
#
# manage.py jobDaemon
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self):
    
        super(Command, self).__init__()

        self.logger = logging.getLogger('jobDaemon')
        self.logger.setLevel(logging.INFO)
        
        self.maxProcesses = 10
        self.requestProcesses = 1
        
        for jdp in models.JobDaemonProcess.objects.iterator():
            
            if not jdp.pidRunning():
                
                self.logger.info('Deleting job daemon process whose ' + 
                                 'pid is not running.')
                jdp.delete()

        # Indicate this JD is running.
        self.process = models.JobDaemonProcess()
        self.process.pid = os.getpid()
        self.process.save()
        
    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):
    
        # Loop until <ctrl-c> is encountered.
        loop = True
        loopsUntilHousekeeping = 10
        loopNum = 0
        
        while loop:
        
            try:
                # Count the RequestProcesses. 
                numRunning = RequestProcess.objects.values('request').count()
                numToRun = self.maxProcesses - numRunning

                # Get numToRun requests that are PENDING.
                pendingReqs = Request.objects.   \
                              filter(started = False).  \
                              order_by('created')[:numToRun]

                # pendingReqs = Request.objects.                           \
                #               filter(started = False).                   \
                #               order_by('created').                       \
                #               select_related(selectRelatedString)
                #
                # pendingReqs = pendingReqs[:numToRun]

                for requestType in requestTypes:
                    pendingReqs = pendingReqs.select_related(requestType)

                # Launch them.
                for baseReq in pendingReqs:
                    
                    # Create a logger.
                    reqLogger = logging.getLogger('request.' + str(baseReq.id))
                    
                    logFile = os.path.join(baseReq.destination.name,
                                           baseReq.name + '.log')
                    
                    if not os.path.exists(logFile):
                        
                        open(logFile, 'a').close()
                        handler = logging.FileHandler(logFile)
                        handler.setLevel(logging.INFO)
                        reqLogger.setLevel(logging.INFO)
                        reqLogger.addHandler(handler)

                    #---
                    # Get the request object as its true type, instead of a
                    # base Request object, so the derived methods are available.
                    #
                    # r = baseReq.georequest or baseReq.loaderrequest or baseReq
                    #---
                    request = baseReq
                    
                    for requestType in requestTypes:

                        try:
                            request = baseReq.__getattribute__(requestType)
                            break

                        except:
                            pass
                        
                    # Create the runner.
                    reqRnr = RequestProcessor(request, \
                                              self.requestProcesses, \
                                              reqLogger)
                    
                    thread = multiprocessing.Process(target = reqRnr)
                    db.connections.close_all()
                    thread.start()
                    
                # Is it time to perform housekeeping?
                loopNum += 1
                
                if loopNum >= loopsUntilHousekeeping:
                    
                    loopNum = 0
                    self.housekeeping()
                
                # Take a break.
                time.sleep(1)
 
            except KeyboardInterrupt:
                self.logger.info('\n<Ctrl-c> detected')
                loop = False

            except InterfaceError:
                db.connections.close_all()
                
            except:
                self.logger.info(traceback.format_exc())
                
        self.process.delete()
   
    #--------------------------------------------------------------------
    # housekeeping
    #--------------------------------------------------------------------
    def housekeeping(self):
        
        rps = RequestProcess.objects.all()
        
        for rp in rps:
            if not rp.pidRunning():
                rp.delete()
        
        cps = ConstituentProcess.objects.all()
        
        for cp in cps:
            if not cp.pidRunning():
                cp.delete()

        purgeZipFiles.purgeZipFiles()
        purgeRequests.purgeRequests()
        purgeRequestDirs.purgeRequestDirs()
            

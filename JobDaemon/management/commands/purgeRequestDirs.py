
import glob
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from ProcessingEngine.models import Request

#-------------------------------------------------------------------------------
# Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(self, **options):
    
        purgeRequestDirs()
        
#-------------------------------------------------------------------------------
# purgeReqDirs
#-------------------------------------------------------------------------------
def purgeRequestDirs():

        workDir = settings.WORK_DIRECTORY
        onDisk  = glob.glob(workDir + '/*')
        inDb    = Request.objects.values_list('destination', flat = True)
        notInDb = []
        
        for diskFile in onDisk:

            if not os.path.isdir(diskFile):
                continue

            found = False
            
            for dbFile in inDb:
            
                if diskFile == dbFile or diskFile == os.path.split(dbFile)[0]:
            
                    found = True
                    break
                        
            if not found:
                
                print 'Removing orphaned directory: ' + str(diskFile)
                shutil.rmtree(diskFile)


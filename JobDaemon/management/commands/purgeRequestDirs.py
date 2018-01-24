
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

            for dbFile in inDb:
                
                if diskFile == dbFile:
                    break

                if diskFile == os.path.split(dbFile)[0]:
                    break
                    
                notInDb.append(diskFile)

        print 'Orphaned request directories to be deleted: ' + str(notInDb)

        for d in notInDb:
            if os.path.isdir(d):
                shutil.rmtree(d)

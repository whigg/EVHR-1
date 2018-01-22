
import glob
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from ProcessingEngine.models import Request

#------------------------------------------------------------------------
# Command
#------------------------------------------------------------------------
class Command(BaseCommand):

    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):
    
        purgeRequestDirs()
        
#--------------------------------------------------------------------
# purgeReqDirs
#--------------------------------------------------------------------
def purgeRequestDirs():

        workDir = settings.WORK_DIRECTORY
        onDisk  = glob.glob(workDir + '/*')
        inDb    = Request.objects.values_list('destination', flat = True)
        notInDb = [d for d in onDisk if d not in inDb]

        print 'Orphaned request directories to be deleted: ' + str(notInDb)
    
        for d in notInDb:
            shutil.rmtree(d)
    
    
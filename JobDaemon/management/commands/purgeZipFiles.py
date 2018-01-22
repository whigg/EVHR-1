
import glob
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand

#------------------------------------------------------------------------
# Command
#------------------------------------------------------------------------
class Command(BaseCommand):

    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):

        purgeZipFiles()
        
#--------------------------------------------------------------------
# purgeZipFiles
#--------------------------------------------------------------------
def purgeZipFiles():

    zipDir     = settings.DOWNLOAD_DIR
    globStr    = 'WRANGLER-*.zip'
    zips       = glob.glob(zipDir + '/' + globStr)
    maxMinutes = 20
    maxSeconds = maxMinutes * 60

    print 'Zip files considered for purge: ' + str(zips)

    for zipFile in zips:
        if time.time() - os.path.getmtime(zipFile) > maxSeconds:
            os.remove(zipFile)



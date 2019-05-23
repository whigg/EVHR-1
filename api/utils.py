
import glob # Part of the kludge below.
import os
import time
import zipfile

from wsgiref.util import FileWrapper

from django.conf import settings
from django.http import HttpResponse

from ProcessingEngine.models import Constituent
from GeoProcessingEngine.models import GeoRequest # Part of the kludge below.

#-------------------------------------------------------------------------------
# downloadRequest
#-------------------------------------------------------------------------------
def downloadRequest(requestId):

    cons = Constituent.objects.filter(request = requestId)

    if cons:

        zipName = 'EVHR-REQUEST-' + str(requestId) + '-' + \
                  str(time.time()) + '.zip'
                  
        archiveFile = os.path.join(settings.DOWNLOAD_DIR, zipName)
      
        zf = zipfile.ZipFile(archiveFile, 'w', zipfile.ZIP_DEFLATED)
        atLeastOneFileZipped = False

        # ---
        # The following is a kludge used until the mosaic process is complete.
        # This first part of the "if" statement is the kludge to be removed.
        # ---
        request = Request.objects.get(id = requestId)
        
        if request.endPoint.name == 'EVHR Mosaic':
            
            toaPath = os.path.join(request.destination.name, '6-toas')
            toas = glob.glob(toaPath + '*-TOA.tif')
            
            if len(toas):
                atLeastOneFileZipped = True

            for toa in toas:
                
                dirName, fileName = os.path.split(con.destination.name)
                os.chdir(dirName)
                zf.write(fileName)

        else:
            
            # ---
            # This is the permanent part that remains after the kludge is
            # unnecessary.
            # ---
            
            # Zip the file for each COMPLETE and enabled constituent.
            for con in cons:

                if con.state() == 'CPT':

                    atLeastOneFileZipped = True
                    dirName, fileName = os.path.split(con.destination.name)
                    os.chdir(dirName)
                    zf.write(fileName)
                
        zf.close()

        response = None

        if atLeastOneFileZipped:

            # fileName = os.path.basename(archiveFile)
            # response = HttpResponse(FileWrapper(open(archiveFile)), content_type='application/x-zip-compressed')
            # response['Content-Length'] = os.path.getsize(archiveFile)
            # response['Content-Disposition'] = "attachment; filename=%s" % fileName
            # return response

            #---
            # Do not bother making an HTTP response, when we can retrieve the
            # file via the file system.
            #---
            return archiveFile

    return None


import os
import time
import zipfile

from wsgiref.util import FileWrapper

from django.conf import settings
from django.http import HttpResponse

from ProcessingEngine.models import Constituent

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

            fileName = os.path.basename(archiveFile)
            response = HttpResponse(FileWrapper(open(archiveFile)), content_type='application/x-zip-compressed')
            response['Content-Length'] = os.path.getsize(archiveFile)
            response['Content-Disposition'] = "attachment; filename=%s" % fileName
            return response

    return None

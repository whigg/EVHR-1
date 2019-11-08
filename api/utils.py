
import os
import time
import zipfile

from wsgiref.util import FileWrapper

from django.conf import settings
from django.http import HttpResponse

from ProcessingEngine.models import Constituent
from ProcessingEngine.models import Request

#-------------------------------------------------------------------------------
# downloadRequest
#-------------------------------------------------------------------------------
def downloadRequest(requestId):

    cons = Constituent.objects.filter(request = requestId)

    if cons:

        zipName = 'EVHR-REQUEST-' + str(requestId) + '-' + \
                  str(time.time()) + '.zip'
                  
        archiveFile = os.path.join(settings.DOWNLOAD_DIR, zipName)
      
        zf = zipfile.ZipFile(archiveFile, 
                             'w', 
                             zipfile.ZIP_DEFLATED, 
                             allowZip64=True)
                             
        atLeastOneFileZipped = False

        # Zip the file for each COMPLETE and enabled constituent.
        for con in cons:

            if con.state() == 'CPT':

                atLeastOneFileZipped = True
                dirName, fileName = os.path.split(con.destination.name)
                os.chdir(dirName)
                zf.write(fileName)
                
        # ---
        # Get the request, determine if it is a ToA or DEM, and add the
        # relevant read-me file.
        # ---
        readMeDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 '../EVHR/documents')
                         
        os.chdir(readMeDir)

        req = Request.object.get(id=requestId)
        protocol = req.endPoint.name
                
        if protocol == 'EVHR DEM':

            zf.write('readme-dem.txt')            
            
        elif protocol == 'EVHR ToA':
            
            zf.write('readme-toa.txt')

        else:
            print 'No read-me file for ' + str(protocol)
            
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

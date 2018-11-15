
import os
import tempfile
from xml.dom import minidom

from django.conf import settings

from EvhrEngine.management.FootprintsScene import FootprintsScene
from EvhrEngine.management.SystemCommand import SystemCommand

#-------------------------------------------------------------------------------
# class Footprints
#-------------------------------------------------------------------------------
class Footprints(object):

    BASE_QUERY = 'ogr2ogr -f "GML" --debug on '

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, footprintsFile=settings.FOOTPRINTS_FILE, logger=None):
        
        # Verify the existence of Footprints.  You never know.
        if not os.path.exists(footprintsFile):
            
            raise RuntimeError('Footprints file, ' + \
                               footprintsFileE + \
                               ' does not exist.')
                               
        self.footprintsFile = footprintsFile
        self.logger = logger
    
    #---------------------------------------------------------------------------
    # _query
    #---------------------------------------------------------------------------
    def _query(self, cmd):
        
        queryResult = tempfile.mkstemp()[1]
        cmd += ' "' + queryResult + '"  "' + self.footprintsFile + '" '
        SystemCommand(cmd, None, self.logger, None, True)
        return minidom.parse(tempClipFile)
        
    #---------------------------------------------------------------------------
    # sceneFromNtf
    #---------------------------------------------------------------------------
    def sceneFromNtf(self, ntfPath):
    
        if not ntfPath:
            raise RuntimeError('An NITF file must be specified.')

        #---
        # It is acceptable to pass an NITF file that does not exist.  It could
        # have been erroneously deleted from the file system.
        #---
        cmd = Footprints.BASEQUERY + '-where "S_FILEPATH=' + "'" + ntfPath+"'\""
        gml = self._query(cmd)
        scene = FootprintsScene(gml)
        
        return scene      

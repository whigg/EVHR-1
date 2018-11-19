
import os
import tempfile
from xml.dom import minidom

from django.conf import settings

from EvhrEngine.management.FootprintsScene import FootprintsScene
from EvhrEngine.management.SystemCommand import SystemCommand

#-------------------------------------------------------------------------------
# class FootprintsQuery
#-------------------------------------------------------------------------------
class FootprintsQuery(object):

    BASE_QUERY = 'ogr2ogr -f "GML" --debug on'
    RUN_SENSORS = ['WV01', 'WV02', 'WV03']
    
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
        self.maxScenes = None
        self.pairsOnly = False
        self.scenes = []
        self.sensors = []
        
        self.ulx = None
        self.uly = None
        self.lrx = None
        self.lry = None
        self.srs = None
        
    #---------------------------------------------------------------------------
    # addAoI
    #---------------------------------------------------------------------------
    def addAoI(self, ulx, uly, lrx, lry, srs):
        
        self.ulx = ulx
        self.uly = uly
        self.lrx = lrx
        self.lry = lry
        self.srs = srs
        
    #---------------------------------------------------------------------------
    # addScenesFromNtf
    #---------------------------------------------------------------------------
    def addScenesFromNtf(self, ntfPaths = []):
    
        #---
        # It is acceptable to pass an NITF file that does not exist.  It could
        # have been erroneously deleted from the file system.
        #---
        self.scenes.extend(ntfPaths)
        
    #---------------------------------------------------------------------------
    # addSensors
    #---------------------------------------------------------------------------
    def addSensors(self, sensors = []):
        
        self.sensors.extend(sensors)
        
    #---------------------------------------------------------------------------
    # _buildWhereClause
    #---------------------------------------------------------------------------
    def _buildWhereClause(self):
        
        # Add pairs only, the start of a where clause.    
        whereClause = ''
        
        if self.pairsOnly:
            
            whereClause += ' pairname IS NOT NULL'

        # Add scene list.
        first = True
        
        for scene in self.scenes:
        
            if first:
                
                first = False

                if whereClause != '':
                    whereClause += ' AND '
                    
                whereClause += ' ('

            else:

                whereClause += ' OR '

            whereClause += 'S_FILEPATH=' + "'" + str(scene) + "'"

        if not first:
            whereClause += ')'

        # Add sensor list.
        first = True

        for sensor in FootprintsQuery.RUN_SENSORS:

            if first:

                first = False

                if whereClause != '':
                    whereClause += ' AND '
                    
                whereClause += ' ('

            else:
                whereClause += ' OR '

            whereClause += 'SENSOR=' + "'" + sensor + "'"

        if not first:
            whereClause += ')'

        return whereClause
        
    #---------------------------------------------------------------------------
    # getScenes
    #---------------------------------------------------------------------------
    def getScenes(self):
        
        # Compose query.
        cmd = FootprintsQuery.BASE_QUERY
        
        if self.maxScenes:
            cmd += ' -limit ' + str(self.maxScenes)

        if self.ulx and self.uly and self.lrx and self.lry and self.srs:

            #---
            # To filter scenes that only overlap the AoI slightly, decrease both
            # corners of the query AoI.
            #---
            MIN_OVERLAP_IN_DEGREES = 0.02
            ulx = float(ulx) + MIN_OVERLAP_IN_DEGREES
            uly = float(uly) - MIN_OVERLAP_IN_DEGREES
            lrx = float(lrx) - MIN_OVERLAP_IN_DEGREES
            lry = float(lry) + MIN_OVERLAP_IN_DEGREES
        
        
            cmd += ' -spat'                         + \
                   ' ' + str(ulx)                   + \
                   ' ' + str(lry)                   + \
                   ' ' + str(lrx)                   + \
                   ' ' + str(uly)                   + \
                   ' -spat_srs'                     + \
                   ' "' + srs.ExportToProj4() + '"'

        whereClause = self._buildWhereClause()
        
        if whereClause:
            cmd += ' -where "' + whereClause + '"'

        queryResult = tempfile.mkstemp()[1]
        cmd += ' "' + queryResult + '"  "' + self.footprintsFile + '" '

        import pdb
        pdb.set_trace()

        SystemCommand(cmd, None, self.logger, None, True)
        resultGML = minidom.parse(queryResult)
        
        # scene = FootprintsScene(gml)

    #---------------------------------------------------------------------------
    # setMaximumScenes
    #---------------------------------------------------------------------------
    def setMaximumScenes(self, maximum):
        
        self.maxScenes = maximum
        
    #---------------------------------------------------------------------------
    # setPairsOnly
    #---------------------------------------------------------------------------
    def setPairsOnly(self, pairsOnly = True):
        
        self.pairsOnly = pairsOnly
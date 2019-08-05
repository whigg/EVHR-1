
import os
import psycopg2
import tempfile
from xml.dom import minidom

from osgeo.osr import CoordinateTransformation
from osgeo.osr import SpatialReference

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
                               footprintsFile + \
                               ' does not exist.')
                               
        self.footprintsFile = footprintsFile
        self.logger = logger
        self.catalogIDs = []
        self.maxScenes = None
        self.minOverlapInDegrees = 0.0
        self.pairsOnly = False
        self.scenes = []
        self.sensors = []

        self.useMultispectral = True
        self.usePanchromatic = True
        
        self.ulx = None
        self.uly = None
        self.lrx = None
        self.lry = None
        self.srs = None
        
        #---
        # Queries must be in geographic coordinates because this class uses
        # the ogr2ogr option -sql to sort the results.  When -sql is used
        # -spat_srs cannot be used.
        #---
        self.targetSRS = SpatialReference()
        self.targetSRS.ImportFromEPSG(4326)
        
    #---------------------------------------------------------------------------
    # addAoI
    #---------------------------------------------------------------------------
    def addAoI(self, ulx, uly, lrx, lry, srs):
        
        if not srs.IsSame(self.targetSRS):
            
            xform = CoordinateTransformation(srs, self.targetSRS)
            ulPt = xform.TransformPoint(ulx, uly)
            lrPt = xform.TransformPoint(lrx, lry)
            
            ulx = ulPt[0]
            uly = ulPt[1]
            lrx = lrPt[0]
            lry = lrPt[1]
            
        self.ulx = ulx
        self.uly = uly
        self.lrx = lrx
        self.lry = lry
        self.srs = srs
        
    #---------------------------------------------------------------------------
    # addCatalogID
    #---------------------------------------------------------------------------
    def addCatalogID(self, catalogIDs = []):
        
        self.catalogIDs.extend(catalogIDs)
        
    #---------------------------------------------------------------------------
    # addEvhrScenes
    #---------------------------------------------------------------------------
    def addEvhrScenes(self, evhrScenes = []):

        for scene in evhrScenes:
            self.scenes.append(scene.sceneFile.name)
        
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
        
        # Add level-1 data only, the start of a where clause.    
        whereClause = "where (prod_short='1B')"
        
        # Add sensor list.
        first = True
        sensors = self.sensors if self.sensors else FootprintsQuery.RUN_SENSORS
        
        for sensor in sensors:

            if first:

                first = False
                whereClause += ' AND ('

            else:
                whereClause += ' OR '

            whereClause += 'SENSOR=' + "'" + sensor + "'"

        if not first:
            whereClause += ')'

        # Add scene list.
        first = True
        
        for scene in self.scenes:
    
            if first:

                first = False

                whereClause += ' AND ('
                
            else:
                whereClause += ' OR '

            whereClause += 'S_FILEPATH=' + "'" + scene + "'"

        if not first:
            whereClause += ')'

        # Add pairs only clause.
        if self.pairsOnly:
            whereClause += ' AND (pairname IS NOT NULL)'

        # Add the catalog ID list.
        first = True
        
        for catID in self.catalogIDs:

            if first:

                first = False
                whereClause += ' AND ('

            else:
                whereClause += ' OR '

            whereClause += 'CATALOG_ID=' + "'" + catID + "'"

        if not first:
            whereClause += ')'
            
        # Set panchromatic or multispectral.
        if not self.usePanchromatic:
            whereClause += ' AND (SPEC_TYPE <> \'Panchromatic\' )'  
          
        if not self.useMultispectral:
            whereClause += ' AND (SPEC_TYPE <> \'Multispectral\')'

        return unicode(whereClause)
        
    #---------------------------------------------------------------------------
    # _buildWhereClausePostgres
    #---------------------------------------------------------------------------
    def _buildWhereClausePostgres(self):
        
        # Add level-1 data only, the start of a where clause.    
        whereClause = "where (prod_code like '_1B_')"
        
        # Add sensor list.
        first = True
        sensors = self.sensors if self.sensors else FootprintsQuery.RUN_SENSORS
        
        for sensor in sensors:

            if first:

                first = False
                whereClause += ' AND ('

            else:
                whereClause += ' OR '

            whereClause += 'SENSOR=' + "'" + sensor + "'"

        if not first:
            whereClause += ')'

        # Add scene list.
        first = True
        
        for scene in self.scenes:
    
            if first:

                first = False

                whereClause += ' AND ('
                
            else:
                whereClause += ' OR '

            whereClause += 'S_FILEPATH=' + "'" + scene + "'"

        if not first:
            whereClause += ')'

        # Add pairs only clause.
        if self.pairsOnly:
            whereClause += ' AND (pairname IS NOT NULL)'

        # Add the catalog ID list.
        first = True
        
        for catID in self.catalogIDs:

            if first:

                first = False
                whereClause += ' AND ('

            else:
                whereClause += ' OR '

            whereClause += 'CATALOG_ID=' + "'" + catID + "'"

        if not first:
            whereClause += ')'
            
        # Set panchromatic or multispectral.
        if not self.usePanchromatic:
            whereClause += ' AND (SPEC_TYPE <> \'Panchromatic\' )'  
          
        if not self.useMultispectral:
            whereClause += ' AND (SPEC_TYPE <> \'Multispectral\')'

        return unicode(whereClause)
        
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
            # MIN_OVERLAP_IN_DEGREES = 0.02
            # ulx = float(self.ulx) + MIN_OVERLAP_IN_DEGREES
            # uly = float(self.uly) - MIN_OVERLAP_IN_DEGREES
            # lrx = float(self.lrx) - MIN_OVERLAP_IN_DEGREES
            # lry = float(self.lry) + MIN_OVERLAP_IN_DEGREES

            ulx = float(self.ulx) + self.minOverlapInDegrees
            uly = float(self.uly) - self.minOverlapInDegrees
            lrx = float(self.lrx) - self.minOverlapInDegrees
            lry = float(self.lry) + self.minOverlapInDegrees
        
            cmd += ' -spat'                         + \
                   ' ' + str(ulx)                   + \
                   ' ' + str(lry)                   + \
                   ' ' + str(lrx)                   + \
                   ' ' + str(uly)                   
                   # ' -spat_srs'                     + \
                   # ' "' + self.srs.ExportToProj4() + '"'

        where = self._buildWhereClause()

        if len(where):
            
            cmd += unicode(' -sql "select * from nga_inventory_canon ') + \
                   where + \
                   unicode(' order by ACQ_DATE DESC"')
        
        queryResult = tempfile.mkstemp()[1]
        cmd += ' "' + queryResult + '"  "' + self.footprintsFile + '" '

        SystemCommand(cmd, inFile=None, logger=self.logger, request=None, 
                      raiseException=True, distribute=False)
                      
        resultGML = minidom.parse(queryResult)
        features = resultGML.getElementsByTagName('gml:featureMember')
        scenes = []
        
        for feature in features:
            scenes.append(FootprintsScene(feature))

        return scenes
        
    #---------------------------------------------------------------------------
    # getScenesFromPostgres
    #---------------------------------------------------------------------------
    def getScenesFromPostgres(self):
        
        # Establish a DB connection.
        connection = psycopg2.connect(user='rlgill',
                                      password='vcKpgkA08Wu0gD2y33Py',
                                      host='arcdb02.atss.adapt.nccs.nasa.gov',
                                      database='arcgis')
        
        cursor = connection.cursor()
        
        # Run the query.
        fields = ('sensor', 'acq_time', 'catalog_id', 'stereopair', 
                  's_filepath')
        
        cmd = 'select ' + \
              ', '.join(fields) + \
              ' from nga_footprint ' + \
              self._buildWhereClausePostgres() + \
              ' order by acq_time desc'
        
        if self.maxScenes:
            cmd += ' -limit ' + str(self.maxScenes)

        if self.logger:
            self.logger.info(cmd)
            
        cursor.execute(cmd)
        
        # Store the results in FootprintScenes.
        scenes = []

        for record in cursor:
            scenes.append(FootprintsScene(record))
            
        # Close connections.
        if(connection):
            
            cursor.close()
            connection.close()  
            
        return scenes          

    #---------------------------------------------------------------------------
    # setMaximumScenes
    #---------------------------------------------------------------------------
    def setMaximumScenes(self, maximum):
        
        self.maxScenes = maximum
        
    #---------------------------------------------------------------------------
    # setMinimumOverlapInDegrees
    #---------------------------------------------------------------------------
    def setMinimumOverlapInDegrees(self, minimum=0.02):
        
        self.minOverlapInDegrees = minimum
        
    #---------------------------------------------------------------------------
    # setPairsOnly
    #---------------------------------------------------------------------------
    def setPairsOnly(self, pairsOnly = True):
        
        self.pairsOnly = pairsOnly

    #---------------------------------------------------------------------------
    # setPanchromaticOff
    #---------------------------------------------------------------------------
    def setPanchromaticOff(self):
        
        self.usePanchromatic = False
        
    #---------------------------------------------------------------------------
    # setMultispectralOff
    #---------------------------------------------------------------------------
    def setMultispectralOff(self):
        
        self.useMultispectral = False
        
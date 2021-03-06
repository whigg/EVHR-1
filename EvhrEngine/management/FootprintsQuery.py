
from datetime import datetime
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
                               
        self.endDate = datetime.today()
        self.footprintsFile = footprintsFile
        self.logger = logger
        self.catalogIDs = []
        self.maxScenes = -1
        self.minOverlapInDegrees = 0.0
        self.numBands = -1
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
    def _buildWhereClause(self, scenes=[]):
        
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
        
        for scene in scenes:
    
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
            
        # Set bands.
        if self.numBands > 0:
            whereClause += ' AND (BANDS=\'' + str(self.numBands) + '\')'
            
        # Set end date.  "2018/07/02 00:00:00"
        whereClause += ' AND (ACQ_DATE<\'' + \
                       self.endDate.strftime("%Y-%m-%d %H:%M:%S") + \
                       '\')'

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

        self.scenes = list(set(self.scenes))
        
        #---
        # If there are too many scenes, the command line will be too long.  To
        # work around this, break up the scene list into manageable chunks.
        # Use "xargs --show-limits" to see 
        # "Size of command buffer we are actually using: 131072".  Use a bit
        # less to allow for the rest of the command.
        #---
        MAX_CHARS = 10000
        curLen = 0
        curList = []
        sceneLists = []
        
        for scene in self.scenes:
            
            if curLen + len(scene) > MAX_CHARS:
                
                sceneLists.append(curList)
                curLen = 0
                curList = []
                
            curList.append(scene)
            curLen += len(scene) + 14   # 14 for ' OR S_FILEPATH='
            
        sceneLists.append(curList)
        
        if self.logger:
            
            self.logger.info('Split scenes into ' + \
                             str(len(sceneLists)) + \
                             ' lists for querying.')
            
        #---
        # For testing, ensure every scene in self.scenes is represented in 
        # sceneLists.  Eventually, remove this.
        #---
        sortedScenes = sorted(self.scenes)
        aggregatedSceneList = []
        
        for sceneList in sceneLists:
            aggregatedSceneList += sceneList
            
        aggregatedSceneList.sort()
        
        if sortedScenes == aggregatedSceneList:
            
            print 'Scene list splitting was successful.'
            
        else:
            print 'Scene list splitting failed.'

        # Get the scenes for each list and add the to the result.
        scenes = []
        
        for sceneList in sceneLists:
            scenes.extend(self._getBatchOfScenes(sceneList))
            
        return scenes
        
    #---------------------------------------------------------------------------
    # _getBatchOfScenes
    #---------------------------------------------------------------------------
    def _getBatchOfScenes(self, sceneList):
        
        # Compose query.
        cmd = FootprintsQuery.BASE_QUERY
        
        if self.maxScenes > 0:
            cmd += ' -limit ' + str(self.maxScenes)

        if self.ulx and self.uly and self.lrx and self.lry and self.srs:

            #---
            # To filter scenes that only overlap the AoI slightly, decrease both
            # corners of the query AoI.
            #---
            ulx = float(self.ulx) + self.minOverlapInDegrees
            uly = float(self.uly) - self.minOverlapInDegrees
            lrx = float(self.lrx) - self.minOverlapInDegrees
            lry = float(self.lry) + self.minOverlapInDegrees
        
            cmd += ' -spat'                         + \
                   ' ' + str(ulx)                   + \
                   ' ' + str(lry)                   + \
                   ' ' + str(lrx)                   + \
                   ' ' + str(uly)                   
                   
        where = self._buildWhereClause(sceneList)

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
        
        if self.maxScenes > 0:
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
    # setEndDate
    #---------------------------------------------------------------------------
    def setEndDate(self, endDateStr):

        endDate = datetime.strptime(endDateStr, '%Y-%m-%d')
        self.endDate = endDate

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
    # setMultispectralOff
    #---------------------------------------------------------------------------
    def setMultispectralOff(self):
        
        self.useMultispectral = False
        
    #---------------------------------------------------------------------------
    # setNumBands
    #---------------------------------------------------------------------------
    def setNumBands(self, numBands):
        
        self.numBands = numBands

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
        
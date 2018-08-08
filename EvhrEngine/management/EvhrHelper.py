
from xml.dom import minidom

from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# class EvhrHelper
#-------------------------------------------------------------------------------
class EvhrHelper(object):

    # FOOTPRINTS_FILE = '/att/pubrepo/NGA/INDEX/Footprints/current/10_05_2017/geodatabase/nga_inventory_10_05_2017.gdb'
    FOOTPRINTS_FILE = '/att/pubrepo/NGA/INDEX/Footprints/current/05_09_2018/geodatabase/nga_inventory.gdb'
    RUN_SENSORS = ['WV01', 'WV02', 'WV03']
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, logger):

        self.logger = logger

    #---------------------------------------------------------------------------
    # clipShp
    #---------------------------------------------------------------------------
    def clipShp(self, shpFile, ulx, uly, lrx, lry, srs, extraQueryParams = ''):

        if self.logger:
            self.logger.info('Clipping Shapefile.')

        # Create a temporary file for the clip output.
        tempClipFile = tempfile.mkstemp()[1]
        
        #---
        # To filter scenes that only overlap the AoI slightly, decrease both
        # corners of the query AoI.
        #---
        MIN_OVERLAP_IN_DEGREES = 0.2
        ulx = float(ulx) + MIN_OVERLAP_IN_DEGREES
        uly = float(uly) - MIN_OVERLAP_IN_DEGREES
        lrx = float(lrx) - MIN_OVERLAP_IN_DEGREES
        lry = float(lry) + MIN_OVERLAP_IN_DEGREES

        # Clip.  The debug option somehow prevents an occasional seg. fault!
        cmd = 'ogr2ogr'                        + \
              ' -f "GML"'                      + \
              ' -spat'                         + \
              ' ' + str(ulx)                   + \
              ' ' + str(lry)                   + \
              ' ' + str(lrx)                   + \
              ' ' + str(uly)                   + \
              ' -spat_srs'                     + \
              ' "' + srs.ExportToProj4() + '"' + \
              ' --debug on'                    + \
              ' ' + str(extraQueryParams)      + \
              ' "' + tempClipFile + '"'        + \
              ' "' + shpFile + '"'

        sCmd = SystemCommand(cmd, shpFile, self.logger, self.request, True)

        xml      = minidom.parse(tempClipFile)
        features = xml.getElementsByTagName('gml:featureMember')

        return features

    #---------------------------------------------------------------------------
    # getScenes
    #---------------------------------------------------------------------------
    def getScenes(self):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = self.request)
        scenes = []

        if evhrScenes:
            
            for es in evhrScenes:
                scenes.append(es.sceneFile.name)

        else:
            
            MAX_FEATS = 100

            # AoI + FOOTPRINTS = scenes
            scenes = self.queryFootprints(self.retrievalUlx,
                                          self.retrievalUly,
                                          self.retrievalLrx,
                                          self.retrievalLry,
                                          self.retrievalSRS,
                                          MAX_FEATS)
                                          
            for scene in scenes:
                
                evhrScene = EvhrScene()
                evhrScene.request = self.request
                evhrScene.sceneFile = scene
                evhrScene.save()
                
        return scenes

    #---------------------------------------------------------------------------
    # queryFootprints
    #---------------------------------------------------------------------------
    def queryFootprints(self, ulx, uly, lrx, lry, srs, maxFeatures = None):

        whereClause = '-where "'
        first = True

        for sensor in EvhrHelper.RUN_SENSORS:

            if first:
                first = False
            else:
                whereClause += ' OR '

            whereClause += 'SENSOR=' + "'" + sensor + "'"

        whereClause += '"'

        features = self.clipShp(EvhrHelper.FOOTPRINTS_FILE, \
                                ulx, uly, lrx, lry, srs,    \
                                whereClause)

        # Put them into a list of (row, path) tuples.
        nitfs = []
        featureCount = 0

        for feature in features:

            featureCount += 1

            if maxFeatures and featureCount > maxFeatures:
                break

            nitf = str(feature. \
                       getElementsByTagName('ogr:S_FILEPATH')[0]. \
                       firstChild. \
                       data)

            nitfs.append(nitf)

        return nitfs



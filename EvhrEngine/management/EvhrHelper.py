
import math
import tempfile
from xml.dom import minidom

from django.conf import settings

from osgeo.osr import CoordinateTransformation

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from EvhrEngine.management.SystemCommand import SystemCommand

#-------------------------------------------------------------------------------
# class EvhrHelper
#-------------------------------------------------------------------------------
class EvhrHelper(object):

    RUN_SENSORS = ['WV01', 'WV02', 'WV03']
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, logger):

        self.logger = logger

    #---------------------------------------------------------------------------
    # clipShp
    #---------------------------------------------------------------------------
    def clipShp(self, shpFile, ulx, uly, lrx, lry, srs, request, \
                extraQueryParams = ''):

        if self.logger:
            self.logger.info('Clipping Shapefile.')

        # Create a temporary file for the clip output.
        tempClipFile = tempfile.mkstemp()[1]
        
        #---
        # To filter scenes that only overlap the AoI slightly, decrease both
        # corners of the query AoI.
        #---
        MIN_OVERLAP_IN_DEGREES = 0.02
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
              ' ' + str(extraQueryParams)
              
        if hasattr(settings, 'MAXIMUM_SCENES'):
            cmd += ' -limit ' + str(settings.MAXIMUM_SCENES)
            
        cmd += ' "' + tempClipFile + '"'        + \
               ' "' + shpFile + '"'

        sCmd = SystemCommand(cmd, shpFile, self.logger, request, True)

        xml      = minidom.parse(tempClipFile)
        features = xml.getElementsByTagName('gml:featureMember')

        return features

    #---------------------------------------------------------------------------
    # getUtmSrs
    #
    # This method finds the UTM zone covering the most of the request's AoI.
    # It does this by finding the centroid of the AoI and choosing that zone.
    #---------------------------------------------------------------------------
    def getUtmSrs(self, request):

        # Centroid, called below, doesn't preserve the SRS.
        srs = GeoRetriever.constructSrs(request.srs)
        
        center = GeoRetriever.bBoxToPolygon(request.ulx,
                                            request.uly,
                                            request.lrx,
                                            request.lry,
                                            srs).Centroid()
        
        # If request is already in WGS84 UTM...
        if srs.IsProjected() and 'UTM' in srs.GetAttrValue('PROJCS'):
            return request.srs

        # If the center is not in geographic projection, convert it.
        xValue = None

        if not GeoRetriever.GEOG_4326.IsSame(srs):

            xform = CoordinateTransformation(srs, GeoRetriever.GEOG_4326)
            xPt = xform.TransformPoint(center.GetX(), center.GetY())
            xValue = float(xPt.GetX())

        else:
            xValue = float(center.GetX())

        # Initally, use the UTM zone of the upper-left corner of the AoI.
        zone = (math.floor((xValue + 180.0) / 6) % 60) + 1
        BASE_UTM_EPSG = '326'
        epsg = int(BASE_UTM_EPSG + str(int(zone)))
        srs = GeoRetriever.constructSrsFromIntCode(epsg)
        return srs.ExportToWkt()

    #---------------------------------------------------------------------------
    # queryFootprints
    #---------------------------------------------------------------------------
    def queryFootprints(self, ulx, uly, lrx, lry, srs, request, \
                        pairsOnly = False):

        whereClause = '-where "('
        first = True

        for sensor in EvhrHelper.RUN_SENSORS:

            if first:
                first = False
            else:
                whereClause += ' OR '

            whereClause += 'SENSOR=' + "'" + sensor + "'"

        whereClause += ')'
        
        if pairsOnly:
            whereClause += ' AND pairname IS NOT NULL'
        
        whereClause += '"'

        features = self.clipShp(settings.FOOTPRINTS_FILE,
                                ulx, 
                                uly, 
                                lrx, 
                                lry, 
                                srs,
                                request,
                                whereClause)

        # # Put them into a list of (row, path) tuples.
        # nitfs = []
        #
        # for feature in features:
        #
        #     nitf = str(feature. \
        #                getElementsByTagName('ogr:S_FILEPATH')[0]. \
        #                firstChild. \
        #                data)
        #
        #     nitfs.append(nitf)
        #
        # return nitfs

        return features


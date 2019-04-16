import os
import tempfile
from osgeo import ogr
#from osgeo.osr import SpatialReference

from EvhrEngine.management.SystemCommand import SystemCommand
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from osgeo.osr import CoordinateTransformation

#-------------------------------------------------------------------------------
# UTM
#-------------------------------------------------------------------------------
class UTM():

    UTM_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'UTM_Zone_Boundaries/UTM_Zone_Boundaries.shp')

    #---------------------------------------------------------------------------
    # proj4
    #---------------------------------------------------------------------------
    @staticmethod
    def proj4(ulx, uly, lrx, lry, srs, logger = None):

        # If SRS is not 4326, convert coordinates
        srs = GeoRetriever.constructSrs(srs)
        targetSRS = GeoRetriever.GEOG_4326
        
        if not srs.IsSame(targetSRS):
            coordTransform = CoordinateTransformation(srs, targetSRS)
            ulx, uly = coordTransform.TransformPoint(ulx, uly)[0:2]
            lrx, lry = coordTransform.TransformPoint(lrx, lry)[0:2]

        # Check if AOI is within UTM boundary
        if uly >= 84.0 or lry <= -80.0:
            raise RuntimeError('Cannot process request with AOI outside of (-80, 84) degrees latitude')        

        # Clip the UTM Shapefile for this bounding box.
        clipFile = tempfile.mkdtemp()

        cmd = 'ogr2ogr'                        + \
              ' -clipsrc'                      + \
              ' ' + str(ulx)                   + \
              ' ' + str(lry)                   + \
              ' ' + str(lrx)                   + \
              ' ' + str(uly)                   + \
              ' -f "ESRI Shapefile"'           + \
              ' -select "Zone_Hemi"'           + \
              ' "' + clipFile   + '"'          + \
              ' "' + UTM.UTM_FILE + '"'

        SystemCommand(cmd, inFile=None, logger=None, request=None,
                      raiseException=True, distribute=False)

        # Read clipped shapefile
        driver = ogr.GetDriverByName("ESRI Shapefile")
        ds = driver.Open(clipFile, 0)
        layer = ds.GetLayer()

        maxArea = 0
        for feature in layer:
            area = feature.GetGeometryRef().GetArea()
            if area > maxArea:
                maxArea = area
                zone, hemi = feature.GetField('Zone_Hemi').split(',')

        # Configure proj.4 string
        proj4 = '+proj=utm +zone={} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
        if hemi.upper() == 'S': proj4 += ' +south'

        # Remove temporary clipFile and its auxiliary files
        driver.DeleteDataSource(clipFile)


        return proj4


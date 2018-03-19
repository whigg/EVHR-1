
import glob
import os

from osgeo import gdal
from osgeo import gdalconst
from osgeo import ogr
from osgeo.osr import SpatialReference

from django.core.management.base import BaseCommand

from GeoProcessingEngine.models import GeoRequest

#-------------------------------------------------------------------------------
# class Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('-r', help = 'Request ID')

    #---------------------------------------------------------------------------
    # constructSrs
    #---------------------------------------------------------------------------
    def constructSrs(self, srsString):
        
        srs = SpatialReference(str(srsString))  # str() in case it's unicode
        
        #---
        # The SRS can exist, but be invalid such that any method called on it
        # will raise an exception.  Use Fixup because it will either reveal
        # this error or potentially improve the object.
        #---
        try:
            srs.Fixup()
        
        except TypeError, e:
            
            raise RuntimeError('Invalid SRS object created for ' + srsString)

        if srs.Validate() != ogr.OGRERR_NONE:
            raise RuntimeError('Unable to construct valid SRS for ' + srsString)

        return srs
        
    #---------------------------------------------------------------------------
    # cornersToPolygon
    #---------------------------------------------------------------------------
    @staticmethod
    def cornersToPolygon(self, ulx, uly, lrx, lry, srs):
        
        fUlx = float(ulx)
        fUly = float(uly)
        fLrx = float(lrx)
        fLry = float(lry)

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(fUlx, fUly)
        ring.AddPoint(fLrx, fUly)
        ring.AddPoint(fLrx, fLry)
        ring.AddPoint(fUlx, fLry)
        
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        poly.AssignSpatialReference(self.constructSrs(srs))
        
        return poly
        
    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        # Get the request.
        request = GeoRequest.objects.get(id = options['r'])
        
        # Create the output Shapefile.
        outDriver = ogr.GetDriverByName('ESRI Shapefile')
        gridFile = os.path.join(str(request.destination.name), 'grids.shp')
        outDataSource = outDriver.CreateDataSource(gridFile)
        outLayer = outDataSource.CreateLayer(gridFile, geom_type=ogr.wkbPolygon)
        layerDefn = outLayer.GetLayerDefn()
        
        # Add the request's corners as a polygon feature.
        polygon = Command.cornersToPolygon(request.ulx, 
                                           request.uly, 
                                           request.lrx,
                                           request.lry,
                                           request.srs)

        outFeature = ogr.Feature(layerDefn)
        outFeature.SetGeometry(polygon)
        outLayer.CreateFeature(outFeature)
        
        # Create features for each tile.
        tileDir = os.path.join(request.destination.name, 'tileTemplates')
        tiles   = glob.glob(os.path.join(tileDir, 'tileTemplate*.tif'))
        
        for tile in tiles:
    
            polygon = Command.tifToPolygon(tile)
            outFeature = ogr.Feature(layerDefn)
            outFeature.SetGeometry(polygon)
            outLayer.CreateFeature(outFeature)

        # Add the UTM zones.
        
    #---------------------------------------------------------------------------
    # tifToPolygon
    #---------------------------------------------------------------------------
    @staticmethod
    def tifToPolygon(self, tif):
        
    	dataset = gdal.Open(inFile, gdalconst.GA_ReadOnly)
        
    	if not dataset:
            raise RuntimeError('Unable to open ' + str(tif))
            
    	# Get the basics.
    	xform  = dataset.GetGeoTransform()
    	xScale = xform[1]
    	yScale = xform[5]
    	width  = dataset.RasterXSize
    	height = dataset.RasterYSize
    	ulx = xform[0]
    	uly = xform[3]	
    	lrx = ulx + width  * xScale
    	lry = uly + height * yScale
        
        return self.cornerToPolygon(ulx, uly, lrx, lry, dataset.GetProjection())
        
        
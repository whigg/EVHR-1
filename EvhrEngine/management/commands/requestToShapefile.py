
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

        parser.add_argument('--id', help = 'Request ID')

    #---------------------------------------------------------------------------
    # constructSrs
    #---------------------------------------------------------------------------
    @staticmethod
    def constructSrs(srsString):
        
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
    def cornersToPolygon(ulx, uly, lrx, lry, srs):
        
        fUlx = float(ulx)
        fUly = float(uly)
        fLrx = float(lrx)
        fLry = float(lry)

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(fUlx, fUly)
        ring.AddPoint(fLrx, fUly)
        ring.AddPoint(fLrx, fLry)
        ring.AddPoint(fUlx, fLry)
        ring.AddPoint(fUlx, fUly)   # Repeating makes it a closed polygon.
        
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        poly.AssignSpatialReference(srs)
        
        return poly
        
    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        # Get the request.
        request = GeoRequest.objects.get(id = options['id'])
        
        # Create the output Shapefile.
        outDriver = ogr.GetDriverByName('ESRI Shapefile')
        
        tileDir = os.path.join(str(request.destination.name), '1-tiles')
        gridFile = os.path.join(tileDir, 'grids.shp')
        
        outDataSource = outDriver.CreateDataSource(gridFile)
        srs = Command.constructSrs(request.srs)

        outLayer = outDataSource.CreateLayer(gridFile, 
                                             srs, 
                                             geom_type = ogr.wkbPolygon)

        layerDefn = outLayer.GetLayerDefn()
        
        # Add the request's corners as a polygon feature.
        polygon = Command.cornersToPolygon(request.ulx, 
                                           request.uly, 
                                           request.lrx,
                                           request.lry,
                                           srs)

        outFeature = ogr.Feature(layerDefn)
        outFeature.SetGeometry(polygon)
        outLayer.CreateFeature(outFeature)
        
        # Create features for each tile.
        tiles = glob.glob(os.path.join(tileDir, 'tile*.tif'))
        
        for tile in tiles:
    
            polygon = Command.tifToPolygon(tile)
            outFeature = ogr.Feature(layerDefn)
            outFeature.SetGeometry(polygon)
            outLayer.CreateFeature(outFeature)

        # Create features for each band file.
        bandDir = os.path.join(str(request.destination.name), '2-bands')
        bands = glob.glob(os.path.join(bandDir, '*.tif'))
        
        for band in bands:
    
            polygon = Command.tifToPolygon(band)
            outFeature = ogr.Feature(layerDefn)
            outFeature.SetGeometry(polygon)
            outLayer.CreateFeature(outFeature)
        
        # Add the UTM zones.
        
    #---------------------------------------------------------------------------
    # tifToPolygon
    #---------------------------------------------------------------------------
    @staticmethod
    def tifToPolygon(tif):
        
    	dataset = gdal.Open(tif, gdalconst.GA_ReadOnly)
        
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
        
        return Command.cornersToPolygon(ulx, 
                                        uly, 
                                        lrx, 
                                        lry, 
                                        Command.constructSrs(dataset. \
                                                             GetProjection()))
        
        
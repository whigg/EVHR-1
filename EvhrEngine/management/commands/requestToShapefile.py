
import glob
import json
import os

from osgeo import gdal
from osgeo import gdalconst
from osgeo import ogr
from osgeo.osr import SpatialReference

from django.core.management.base import BaseCommand

from EvhrEngine.management.GdalFile import GdalFile
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
        
        parser.add_argument('--noTiles', 
                            help = 'Do not include tiles', 
                            action = 'store_true')
                            
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-b', help = 'Full path to band file')

        group.add_argument('--noBands', 
                           help = 'Do not include bands', 
                           action = 'store_true')
                            
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
        
        # Create features for each scene.
        sceneFile = os.path.join(request.destination.name, 'scenes.txt')
        with open(sceneFile) as f: sceneString = f.read()
        scenes = json.loads(sceneString)
        self.tifsToFeature(scenes, outFeature)
        
        # Create features for each tile.
        if options['t']:
        
            tiles = glob.glob(os.path.join(tileDir, 'tile*.tif'))
            self.tifsToFeature(tiles, outFeature)

        # Create features for each band file.
        bands = []
        
        if options['b']:
            
            bands = [options['b']]
            
        elif not options['noBands']:
            
            bandDir = os.path.join(str(request.destination.name), '2-bands')
            bands = glob.glob(os.path.join(bandDir, '*.tif'))
        
        self.tifsToFeature(bands, outFeature)
        
        # Add the UTM zones.
        
    #---------------------------------------------------------------------------
    # tifsToFeature
    #---------------------------------------------------------------------------
    def tifsToFeature(tifs, outLayer):
        
        for tif in tifs:
            
            gf = GdalFile(tif)
            
            polygon = Command.cornersToPolygon(gf.ulx, 
                                               gf.uly, 
                                               gf.lrx, 
                                               gf.lry, 
                                               gf.srs)
            
            outFeature = ogr.Feature(layerDefn)
            outFeature.SetGeometry(polygon)
            outLayer.CreateFeature(outFeature)
        

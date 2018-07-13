
import glob
import json
import os

from osgeo import gdal
from osgeo import gdalconst
from osgeo import ogr
from osgeo.osr import SpatialReference

from django.core.management.base import BaseCommand

from EvhrEngine.management.GdalFile import GdalFile
from EvhrEngine.models import EvhrScene
from GeoProcessingEngine.models import GeoRequest

#-------------------------------------------------------------------------------
# class Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    fieldDef = ogr.FieldDefn('Name', ogr.OFTString )
    fieldDef.SetWidth(160)

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
    # createFeature
    #---------------------------------------------------------------------------
    @staticmethod
    def createFeature(ulx, uly, lrx, lry, srs, name, layer):
        
        polygon = Command.cornersToPolygon(ulx, uly, lrx, lry, srs)
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('Name', name)      
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        #---
        # Get the request.
        #---
        request = GeoRequest.objects.get(id = options['id'])
        
        #---
        # Create the output Shapefile.
        #---
        gridDir = os.path.join(str(request.destination.name), 'grids')
        
        if not os.path.isdir(gridDir):
            os.mkdir(gridDir)
            
        gridFile = os.path.join(gridDir, 'aoi.shp')
        outDriver = ogr.GetDriverByName('ESRI Shapefile')
        dataSource = outDriver.CreateDataSource(gridFile)
        srs = SpatialReference(str(request.srs))  # str() in case it's unicode

        #---
        # Add the request's corners as a layer with a polygon feature. 
        #---
        polygon = Command.cornersToPolygon(request.ulx, 
                                           request.uly, 
                                           request.lrx,
                                           request.lry,
                                           srs)

        layer = dataSource.CreateLayer('AoI', srs, geom_type = ogr.wkbPolygon)
        layer.CreateField(Command.fieldDef)
        
        Command.createFeature(request.ulx,
                              request.uly,
                              request.lrx,
                              request.lry,
                              srs,
                              'AoI',
                              layer)
        
        #---
        # Create features for each scene.
        #---
        # sceneFile = os.path.join(request.destination.name, 'scenes.txt')
        # with open(sceneFile) as f: sceneString = f.read()
        # scenes = json.loads(sceneString)
        # Command.filesToFeatures('scenes', scenes, srs, dataSource)
        
        scenes = EvhrScene.objects.values_list('sceneFile', flat = True) \
                                  .filter(request = request.id)

        Command.filesToFeatures('scenes', scenes, srs, dataSource)
        
        #---
        # Create features for each tile.
        #---
        if not options['noTiles']:
        
            tileDir = os.path.join(str(request.destination.name), '1-tiles')
            tiles = glob.glob(os.path.join(tileDir, 'tile*.tif'))
            Command.filesToFeatures('tiles', tiles, srs, dataSource)

        #---
        # Create features for each band file.
        #---
        bands = []
        
        if options['b']:
            
            bands = [options['b']]
            
        elif not options['noBands']:
            
            bandDir = os.path.join(str(request.destination.name), '2-bands')
            bands = glob.glob(os.path.join(bandDir, '*.tif'))
        
        Command.filesToFeatures('bands', bands, srs, dataSource)
        
        #---
        # Add the UTM zones.
        #---
        
    #---------------------------------------------------------------------------
    # filesToFeatures
    #---------------------------------------------------------------------------
    @staticmethod
    def filesToFeatures(name, tifs, masterSRS, dataSource):
        
        if not len(tifs):
            return
            
        layer = dataSource.CreateLayer(name, masterSRS,geom_type=ogr.wkbPolygon)
        layer.CreateField(Command.fieldDef)

        for tif in tifs:
            
            gf = GdalFile(tif)
            
            if not gf.srs.IsSame(masterSRS):
                raise RuntimeError('SRS is different from the master SRS.')
            
            Command.createFeature(gf.ulx,
                                  gf.uly,
                                  gf.lrx,
                                  gf.lry,
                                  gf.srs,
                                  gf.fileName,
                                  layer)

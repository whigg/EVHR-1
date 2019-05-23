
import os
import tempfile

from osgeo import ogr 

from django.core.management.base import BaseCommand

from EvhrEngine.management.commands.requestToShapefile import ShapefileHelper
from EvhrEngine.management.GdalFile import GdalFile

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
     
        parser.add_argument('-f', help = 'Full path to file.')
    
    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):
        
        gf = GdalFile(options['f'])
        outDir = tempfile.mkdtemp()
        shapeFile = os.path.join(outDir, os.path.basename(gf.fileName) +'.shp')        
        outDriver = ogr.GetDriverByName('ESRI Shapefile')
        dataSource = outDriver.CreateDataSource(shapeFile)
        layer = dataSource.CreateLayer('tif', gf.srs ,geom_type=ogr.wkbPolygon)
        layer.CreateField(Command.fieldDef)
        
        ShapefileHelper.createFeature(gf.ulx,
                                      gf.uly,
                                      gf.lrx,
                                      gf.lry,
                                      gf.srs,
                                      gf.fileName,
                                      layer)
        
        
        print 'Created: ' + shapeFile
         
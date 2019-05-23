
import os
import tempfile

from osgeo import ogr

from django.core.management.base import BaseCommand

from EvhrEngine.management.commands.requestToShapefile import Command as rts
from EvhrEngine.management.GdalFile import GdalFile

#-------------------------------------------------------------------------------
# class Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
     #---------------------------------------------------------------------------
     # add_arguments
     #---------------------------------------------------------------------------
     def add_arguments(self, parser):
        
         parser.add_argument('-f', help = 'Full path to file.')
 
     #---------------------------------------------------------------------------
     # handle
     #---------------------------------------------------------------------------
     def handle(*args, **options):
     
         gdalFile = GdalFile(options['f'])
         outDir = tempfile.mkdtemp()
         
         shapeFile = os.path.join(outDir, 
                                  os.path.basename(gdalFile.fileName) + '.shp')
         
         outDriver = ogr.GetDriverByName('ESRI Shapefile')
         dataSource = outDriver.CreateDataSource(shapeFile)
         rts.filesToFeatures('tif', [fileName], gdalFile.srs, dataSource)
         
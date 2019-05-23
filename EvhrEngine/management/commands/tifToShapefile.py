
import os
import tempfile

from django.core.management.base import BaseCommand

import EvhrEngine.management.commands.requestToShapeFile import Command as rts
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
         shapeFile = os.path.join(gridDir, os.path.basename(fileName) + '.shp')
         outDriver = ogr.GetDriverByName('ESRI Shapefile')
         dataSource = outDriver.CreateDataSource(shapeFile)
         rts.filesToFeatures('tif', [fileName], gdalFile.srs, dataSource)
         
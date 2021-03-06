
from glob import glob
import os

from osgeo import gdal

from django.core.management.base import BaseCommand

from ProcessingEngine.models import Request
from EvhrEngine.management.GdalFile import GdalFile

#-------------------------------------------------------------------------------
# compareDemRequests
#
# ./manage.py compareDemRequests 632 633
# 
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('request1')
        parser.add_argument('request2')

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):
        
        req1 = Request.objects.get(id=options['request1'])
        req2 = Request.objects.get(id=options['request2'])
        
        if not os.path.exists(str(req1.destination)):

            raise RuntimeError('Request directory, ' + 
                               str(req1.destination) + 
                               ' does not exist.')
        
        if not os.path.exists(str(req2.destination)):

            raise RuntimeError('Request directory, ' + 
                               str(req2.destination) + 
                               ' does not exist.')
        
        reqDir1 = os.path.join(str(req1.destination), 'dems')
        reqDir2 = os.path.join(str(req2.destination), 'dems')

        # Check for the same pairs.
        req1PairDirs = [os.path.basename(f) for f in glob(reqDir1 + '/W*') \
                        if os.path.isdir(f)]
                        
        req2PairDirs = [os.path.basename(f) for f in glob(reqDir2 + '/W*') \
                        if os.path.isdir(f)]
        
        req1PairDirs.sort()
        req2PairDirs.sort()
        
        if req1PairDirs == req2PairDirs:
            
            print 'Both requests have the same pairs.'

        else:
            print 'The requests do not have the same pairs.'
            print 'Request 1 pairs: ' + str(req1PairDirs)
            print 'Request 2 pairs: ' + str(req2PairDirs)      
            
        # Check the corresponding DEMs pixel by pixel.
        req1Dems = [f for f in glob(reqDir1 + '/W*.tif')]      
        req2Dems = [f for f in glob(reqDir2 + '/W*.tif')]
        
        for i in range(len(req1Dems)):
            
            print 'Comparing ' + req1Dems[i] + ' and ' + req2Dems[i]
            
            cmd = 'gdalcompare.py ' + req1Dems[i] + ' ' + req2Dems[i]
            result = os.system(cmd)  
            
            if result != 0:
                
                print 'DEMs differ.'
                dem1 = GdalFile(req1Dems[i])
                dem2 = GdalFile(req2Dems[i])
                
                raster1 = dem1.dataset.ReadAsArray(0, 0)
                raster2 = dem2.dataset.ReadAsArray(0, 0)
                rows = len(raster1)
                cols = len(raster1[0])
                numPixels = rows * cols
                
                print 'There are ' + str(numPixels) + ' pixels.'
                
                if rows != len(raster2):
                    
                    print 'Rasters have different numbers of rows.'
                    
                elif cols != len(raster2[0]):
                    
                    print 'Rasters have different numbers of columns.'
                    
                else:
                    
                    difference = 0
                    
                    for r in range(rows):
                        for c in range(cols):
                            
                            difference += abs(float(raster1[r][c]) - \
                                              float(raster2[r][c]))
                        
                    print 'The cumulative difference in pixel values is ' + \
                          str(difference)
                        
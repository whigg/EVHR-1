
from osgeo.osr import SpatialReference

from django.test import TestCase

from EvhrEngine.management.TilerIdentity import TilerIdentity

#--------------------------------------------------------------------------------
# TestTilerIdentity
#--------------------------------------------------------------------------------
class TestTilerIdentity(TestCase):

    #---------------------------------------------------------------------------
    # testDefineGrid 
    #---------------------------------------------------------------------------
    def testDefineGrid(self):

        ulx = -113.39250146
        uly = 43.35041085
        lrx = -112.80953835
        lry = 42.93059617
        srs = SpatialReference()
        srs.ImportFromEPSG(4326)
        
        ti = TilerIdentity(ulx, uly, lrx, lry, srs, None)
        grid = ti.defineGrid()
        
        self.assertEqual(ulx, grid[0])
        self.assertEqual(uly, grid[1])
        self.assertEqual(lrx, grid[2])
        self.assertEqual(lry, grid[3])


from osgeo.osr import SpatialReference

from django.test import TestCase

from EvhrEngine.management.TilerHalfDegree import TilerHalfDegree

#--------------------------------------------------------------------------------
# TestTilerHalfDegree
#--------------------------------------------------------------------------------
class TestTilerHalfDegree(TestCase):

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
        
        ti = TilerHalfDegree(ulx, uly, lrx, lry, srs, None)
        tiles = ti.defineGrid()

        self.assertEqual(len(tiles), 2)

        self.assertEqual(ulx,           tiles[0][0])
        self.assertEqual(uly,           tiles[0][1])
        self.assertEqual(-112.89250146, tiles[0][2])
        self.assertEqual(  42.85041085, tiles[0][3])

        self.assertEqual(-112.89250146, tiles[1][0])
        self.assertEqual(  43.35041085, tiles[1][1])
        self.assertEqual(-112.39250146, tiles[1][2])
        self.assertEqual(  42.85041085, tiles[1][3])

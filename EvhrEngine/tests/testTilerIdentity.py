
from osgeo.osr import SpatialReference

from django.test import TestCase

from EvhrEngine.management.TilerIdentity import TilerIdentity

#--------------------------------------------------------------------------------
# TestTilerIdentity
#--------------------------------------------------------------------------------
class TestTilerIdentity(TestCase):

    #---------------------------------------------------------------------------
    # setUpTestData
    #---------------------------------------------------------------------------
    @classmethod
    def setUpTestData(cls):
        
        cls.ulx = -113.39250146
        cls.uly = 43.35041085
        cls.lrx = -112.80953835
        cls.lry = 42.93059617
        cls.srs = SpatialReference()
        cls.srs.ImportFromEPSG(4326)
        
        cls.ti = TilerIdentity(cls.ulx, cls.uly, cls.lrx, cls.lry, cls.srs,None)

    #---------------------------------------------------------------------------
    # testDefineGrid 
    #---------------------------------------------------------------------------
    def testDefineGrid(self):

        grid = TestTilerIdentity.ti.defineGrid()
        
        self.assertEqual(TestTilerIdentity.ulx, grid[0][0])
        self.assertEqual(TestTilerIdentity.uly, grid[0][1])
        self.assertEqual(TestTilerIdentity.lrx, grid[0][2])
        self.assertEqual(TestTilerIdentity.lry, grid[0][3])

    #---------------------------------------------------------------------------
    # testGridsToPolygons
    #---------------------------------------------------------------------------
    def testGridToPolygons(self):

        grid = TestTilerIdentity.ti.defineGrid()
        polygons = TestTilerIdentity.ti.gridToPolygons(grid)
        
        geom = polygons[0].GetGeometryRef(0)
        self.assertEqual(5, geom.GetPointCount())
        self.assertEqual(TestTilerIdentity.ulx, geom.GetPoint(0)[0])
        self.assertEqual(TestTilerIdentity.uly, geom.GetPoint(0)[1])
        self.assertEqual(TestTilerIdentity.lrx, geom.GetPoint(2)[0])
        self.assertEqual(TestTilerIdentity.lry, geom.GetPoint(2)[1])

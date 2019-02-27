
from osgeo.osr import SpatialReference

from django.test import TestCase

from EvhrEngine.management.FootprintsQuery import FootprintsQuery

#--------------------------------------------------------------------------------
# TestFootprintsQuery
#
# ./manage.py test EvhrEngine.tests.test_FootprintsQuery --failfast
#--------------------------------------------------------------------------------
class TestFootprintsQuery(TestCase):

    #---------------------------------------------------------------------------
    # testInit 
    #---------------------------------------------------------------------------
    def testInit(self):
        
        FootprintsQuery()

    #---------------------------------------------------------------------------
    # testAddAoI
    #---------------------------------------------------------------------------
    def testAddAoI(self):
        
        ulx = 374187
        uly = 4202663
        lrx = 501598
        lry = 4100640
        
        srs = SpatialReference()
        srs.ImportFromEPSG(32612)
        
        fpq = FootprintsQuery()
        fpq.addAoI(ulx, uly, lrx, lry, srs)
        fpq.getScenes()
        
    #---------------------------------------------------------------------------
    # testConsistentResults 
    #---------------------------------------------------------------------------
    def testConsistentResults(self):
        
        ulx = 94.2
        uly = 19.4
        lrx = 94.6
        lry = 19.1
        srs = SpatialReference()
        srs.ImportFromEPSG(4326)
        
        fpq = FootprintsQuery()
        fpq.addAoI(ulx, uly, lrx, lry, srs)
        fpq.setPairsOnly()
        fpScenes1 = fpq.getScenes()
        fpScenes2 = fpq.getScenes()
        
        self.assertEqual(len(fpScenes1), len(fpScenes2))
        
        for i in range(len(fpScenes1)):
            self.assertEqual(fpScenes1[i].fileName(), fpScenes2[i].fileName())
            
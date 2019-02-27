
from osgeo.osr import SpatialReference

from django.test import TestCase

from EvhrEngine.management.FootprintsQuery import FootprintsQuery

#--------------------------------------------------------------------------------
# TestFootprintsQuery
#
# ./manage.py test EvhrEngine.tests.test_FootprintsQuery
#--------------------------------------------------------------------------------
class TestFootprintsQuery(TestCase):

    #---------------------------------------------------------------------------
    # testInit 
    #---------------------------------------------------------------------------
    def testInit(self):
        
        FootprintsQuery()

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
        
        assertEqual(len(fpScenes1), len(fpScenes2))
    
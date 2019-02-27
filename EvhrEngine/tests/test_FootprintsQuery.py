from django.test import TestCase

from EvhrEngine.management.FootprintsQuery import FootprintsQuery

#--------------------------------------------------------------------------------
# TestFootprintsQuery
#
# python -m unittest EvhrEngine.tests.test_FootprintsQuery
#--------------------------------------------------------------------------------
class TestFootprintsQuery(TestCase):

    #---------------------------------------------------------------------------
    # testInit 
    #---------------------------------------------------------------------------
    def testInit(self):
        
        FootprintsQuery()
    
    
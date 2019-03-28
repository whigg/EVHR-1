
import os

import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand

#-------------------------------------------------------------------------------
# class Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('-f', help='Fully-qualified path to results.')

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        # Parse and get the features.
        ns = {'gml' : 'http://www.opengis.net/gml',
              'ns1' : 'http://ogr.maptools.org/',
              'ogr' : 'http://ogr.maptools.org/',}

        root = ET.parse(options['f'])
        features = root.findall('gml:featureMember/ogr:nga_inventory', ns)

        # Count the features.
        print 'Number of features: ' + str(len(features)) 
        
        # Aggregate the pairs.
        pairs = {}
        
        for feature in features:

            # pairName = feature.find('ogr:pairname', ns).text
            pairName = feature.find('ogr:stereopair', ns).text
            filePath = feature.find('ogr:S_FILEPATH', ns).text
            
            if not pairName in pairs:
                pairs[pairName] = []
                
            pairs[pairName].append(filePath)
            
        print 'Number of pairs: ' + str(len(pairs))
        
        # ---
        # Print the pairs:
        #
        # Pair name: WV01_20130613_1020010023555200_1020010022CE5C00
        #                          catalog ID       pair ID
        # ---
        for pairName in pairs.iterkeys():
        
            # catId = pairName.split('_')[2]
            # pairId = pairName.split('_')[3]
            scenes = pairs[pairName]
            print '\n' + pairName
            print '\t' + catId1
            printScenesForCatId(pairId, scenes)
            # print '\t' + catId2
            # printScenesForCatId(catId2, scenes)

#---------------------------------------------------------------------------
# printScenesForCatId
#---------------------------------------------------------------------------
def printScenesForCatId(catId, scenes):
    
    hasScene = False
    
    for scene in scenes:
        
        if catId in scene:
        
            print '\t\t' + os.path.basename(scene)
            hasScene = True
            
    if not hasScene:
        print '\t\t** NO SCENES**'

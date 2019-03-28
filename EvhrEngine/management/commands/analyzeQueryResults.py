
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand

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

            pairName = feature.find('ogr:pairname', ns).text
            filePath = feature.find('ogr:S_FILEPATH', ns).text
            
            if not pairName in pairs:
                pairs[pairName] = []
                
            pairs[pairName].append(filePath)
            
        print 'Number of pairs: ' + str(len(pairs))

        # Find pairs without scenes for both channels.
        for pairName in pairs.iterkeys():
            
            catId1 = pairName.split('_')[2]
            catId2 = pairName.split('_')[3]
            catId1HasScene = False
            catId2HasScene = False
            scenes = pairs[pairName]
            
            for scene in scenes:
                
                if catId1 in scene:
                    catId1HasScene = True
                    
                if catId2 in scene:
                    catId1HasScene = True
                    
            if not catId1HasScene:
                print 'No scenes for: ' + catId1
            
            if not catId2HasScene:
                print 'No scenes for: ' + catId2
            
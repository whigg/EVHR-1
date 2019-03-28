
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
        features = root.findall('gml:featureMember', ns)

        # Count the features.
        print 'Number of features: '  + str(len(features)) 
        
        # Aggregate the pairs.
        pairs = {}
        
        for feature in features:

            import pdb
            pdb.set_trace()
            pairName = feature.findall('ns1:pairname', ns)
            print pairName

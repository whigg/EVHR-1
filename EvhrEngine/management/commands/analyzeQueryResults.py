
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
        root = ET.parse(options['f'])
        ns = {'gml' : 'http://www.opengis.net/gml',}
        features = root.findall('gml:featureMember', ns)

        # Count the features.
        print 'Number of features: '  + str(len(features)) 

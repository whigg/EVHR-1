
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

        root = ET.parse(options['f'])

        # Count the features.
        features = root.findall('gml:featureMember')
        print 'Number of features: '  + str(len(features)) 

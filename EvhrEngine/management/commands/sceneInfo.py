from EvhrEngine.management.Footprints import Footprints

from django.core.management.base import BaseCommand

class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('-n', help='Full path to NITF file', required=True)

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        footprints = Footprints()
        scene = footprints.sceneFromNtf(options['n'])
        print 'Pair name:  ' + str(scene.pairName())



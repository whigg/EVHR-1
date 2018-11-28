
from EvhrEngine.management.FootprintsQuery import FootprintsQuery

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

        query = FootprintsQuery()
        query.addScenesFromNtf([options['n']])
        scene = query.getScenes()
        print 'Pair name:  ' + str(scene[0].pairName())



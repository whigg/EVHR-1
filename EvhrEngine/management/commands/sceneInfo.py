
from EvhrEngine.management.FootprintsQuery import FootprintsQuery

from django.core.management.base import BaseCommand

class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-c', help='Catalog ID')
        group.add_argument('-n', help='Full path to NITF file')

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        query = FootprintsQuery()

        if options.c is not None:
            query.addCatalogID([options['c']])
            
        if options.n is not None:
            query.addScenesFromNtf([options['n']])

        scene = query.getScenes()
        
        if not scene:
            raise RuntimeError('Scene does not exist.')
            
        print 'Pair name:  ' + str(scene[0].pairName())



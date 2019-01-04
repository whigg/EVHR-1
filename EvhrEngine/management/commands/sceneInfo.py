
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

        if options['c'] is not None:
            query.addCatalogID(options['c'])
            
        if options['n'] is not None:
            query.addScenesFromNtf([options['n']])

        fpScenes = query.getScenes()
        
        if not fpScenes:
            raise RuntimeError('No matching scenes found in Footprints.')

        for fpscene in fpScenes:
            
            print 'NITF:  ' + str(fpScene.fileName())
            print 'Pair name:  ' + str(scene.pairName())



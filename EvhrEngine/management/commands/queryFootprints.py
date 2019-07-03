from django.core.management.base import BaseCommand

from django.conf import settings

from EvhrEngine.management.FootprintsQuery import FootprintsQuery

#-------------------------------------------------------------------------------
# class Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('--catIDs', help = 'List of catalog IDs')

        parser.add_argument('--multiOnly', 
                            help = 'Only use multispectral',
                            action = 'store_true')
                            
        parser.add_argument('--sensors', help = 'List of sensors, like WV02')
        

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        fpq = FootprintsQuery()

        if options['catIDs']:
            for catID in options['catIDs'].split():
                fpq.addCatalogID(catID)

        if options['multiOnly']:
            fpq.setPanchromaticOff()
            
        if options['sensors']:
            fpq.addSensors(options['sensors'])

        if hasattr(settings, 'MAXIMUM_SCENES'):
            maxScenes = min(maxScenes, settings.MAXIMUM_SCENES)
            
        fpq.setMaximumScenes(maxScenes)
        fpScenes = fpq.getScenes()
        print 'Scenes: ' + str(fpScenes)
        

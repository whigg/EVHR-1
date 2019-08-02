from osgeo.osr import SpatialReference

from django.core.management.base import BaseCommand

from django.conf import settings

from EvhrEngine.management.FootprintsQuery import FootprintsQuery

#-------------------------------------------------------------------------------
# class Command
#
# ./manage.py queryFootprints --catIDs 10300100053F4400 10300100060AF200 10300100064CE200 10300100060DDC00 103001000667BA00 103001001F95E700 103001002047F300 --multiOnly --sensors WV02 WV03
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('--aoi', 
                            help='ulx uly lrx lry epsg',
                            nargs=4)

        parser.add_argument('--catIDs', 
                            help='List of catalog IDs',
                            nargs='+')

        parser.add_argument('--multiOnly', 
                            help='Only use multispectral',
                            action='store_true')
                            
        parser.add_argument('--sensors', 
                            help='List of sensors, like WV02',
                            nargs='+')        

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        fpq = FootprintsQuery()

        if options['aoi']:
            
            ulx, uly, lrx, lry, epsg = options['aoi']
            srs = SpatialReference()
            srs.ImportFromEPSG(epsg)
            fpq.addAoi(ulx, uly, lrx, lry, srs)
            
        if options['catIDs']:
            fpq.addCatalogID(options['catIDs'])
        
        if options['sensors']:
            fpq.addSensors(options['sensors'])

        if options['multiOnly']:
            fpq.setPanchromaticOff()
            
        if hasattr(settings, 'MAXIMUM_SCENES'):
            fpq.setMaximumScenes(settings.MAXIMUM_SCENES)
            
        fpScenes = fpq.getScenes()
        print 'Scenes: ' + str(fpScenes)

        # fpq.getScenesFromPostgres()

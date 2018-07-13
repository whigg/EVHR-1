
import datetime

# from django.conf import settings
from django.core.management.base import BaseCommand

from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.models import GeoRequest
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# Command
#
# ./manage.py sendTestEvhrRequest --reqName 'crystal'
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    REQUESTS = {
        
        'evhrGSENM' : {'epName'   : 'EVHR Mosaic',
                       'ulx'      : '36719',
                       'uly'      : '4209000',
                       'lrx'      : '510000',
                       'lry'      : '4094000',
                       'epsg'     : '32612',
                       'outEpsg'  : '102039',
                       'startDate': datetime.date(2016, 8, 4),
                       'endDate'  : datetime.date(2017, 1, 31)},

        'evhrFairbanksScenes' : {
            'epName'   : 'EVHR Mosaic',
            'ulx'      : '-148',
            'uly'      : '65',
            'lrx'      : '-147.5',
            'lry'      : '64.5',
            'epsg'     : '4326',
            'outEpsg'  : '4326',
            'scenes'   : [ "/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_005733445010_03/WV01_20080228205612_1020010001076500_08FEB28205612-P1BS-005733445010_03_P001.ntf",
                           "/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_052804587010_01/WV01_20080228205612_1020010001076500_08FEB28205612-P1BS-052804587010_01_P001.ntf",
                           "/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_005733445010_03/WV01_20080228205614_1020010001076500_08FEB28205614-P1BS-005733445010_03_P002.ntf"]
            }
    }

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):
        
        parser.add_argument('--reqName',
                            help = 'The name of the request to test.')

    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):

        try:
            params = Command.REQUESTS[options['reqName']]
            
        except KeyError:
            raise RuntimeError('Unknown request: ' + str(options['reqName']))

        request             = GeoRequest()
        request.name        = 'Test Request ' + str(options['reqName'])
        # request.startDate   = params['startDate']
        # request.endDate     = params['endDate']
        request.started     = False
        request.ulx         = params['ulx']
        request.uly         = params['uly']
        request.lrx         = params['lrx']
        request.lry         = params['lry']
    
        ep = EndPoint.objects.filter(name = params['epName'])[0]
        request.endPoint = ep
    
        request.srs = \
            GeoRetriever.constructSrsFromIntCode(params['epsg']).ExportToWkt()
    
        request.outSRS = \
            GeoRetriever.constructSrsFromIntCode(params['outEpsg']). \
            ExportToWkt()
    
        request.save()

        if params.has_key('scenes'):
            
            scenes = params['scenes']

            for scene in scenes:
            
                evhrScene = EvhrScene()
                evhrScene.request = request
                evhrScene.sceneFile = scene
                evhrScene.save()


        

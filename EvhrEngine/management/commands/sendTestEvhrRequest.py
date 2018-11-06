
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

        'evhrDemScenes' : {
            
            'epName'   : 'EVHR Mosaic',
            'ulx'      : '-148',
            'uly'      : '65',
            'lrx'      : '-147.5',
            'lry'      : '64.5',
            'epsg'     : '4326',
            'scenes'   : ["/att/pubrepo/NGA/WV01/1B/2011/057/WV01_1020010011416200_X1BS_052566029090_01/WV01_20110226220005_1020010011416200_11FEB26220005-P1BS-052566029090_01_P001.ntf",
                          "/att/pubrepo/NGA/WV01/1B/2011/057/WV01_1020010011416200_X1BS_052566029090_01/WV01_20110226220006_1020010011416200_11FEB26220006-P1BS-052566029090_01_P002.ntf",
                          "/att/pubrepo/NGA/WV01/1B/2011/057/WV01_10200100123C2600_X1BS_052503589010_01/WV01_20110226220054_10200100123C2600_11FEB26220054-P1BS-052503589010_01_P001.ntf"]
        },
        
        'evhrFairbanksScenes' : {
            'epName'   : 'EVHR Mosaic',
            'ulx'      : '-148',
            'uly'      : '65',
            'lrx'      : '-147.5',
            'lry'      : '64.5',
            'epsg'     : '4326',
            'scenes'   : [ "/att/pubrepo/NGA/WV02/1B/2010/245/WV02_1030010007C2B700_X1BS_052807128030_01/WV02_20100902221603_1030010007C2B700_10SEP02221603-M1BS-052807128030_01_P002.ntf",
                           "/att/pubrepo/NGA/WV02/1B/2010/254/WV02_1030010006788900_X1BS_052807059010_01/WV02_20100911214820_1030010006788900_10SEP11214820-M1BS-052807059010_01_P001.ntf",
                           "/att/pubrepo/NGA/WV02/1B/2010/254/WV02_1030010006788900_X1BS_052807059010_01/WV02_20100911214821_1030010006788900_10SEP11214821-M1BS-052807059010_01_P002.ntf"]
        },

        'evhrFairbanks' : {
            'epName'   : 'EVHR Mosaic',
            'ulx'      : '-148',
            'uly'      : '65',
            'lrx'      : '-147.5',
            'lry'      : '64.5',
            'epsg'     : '4326',
        },

        'evhrGSENM' : {'epName'   : 'EVHR Mosaic',
                       'ulx'      : '36719',
                       'uly'      : '4209000',
                       'lrx'      : '510000',
                       'lry'      : '4094000',
                       'epsg'     : '32612',
                       'outEpsg'  : '102039',
                       'startDate': datetime.date(2016, 8, 4),
                       'endDate'  : datetime.date(2017, 1, 31)
        },
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
    
        if params.has_key('outEpsg'):

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


        

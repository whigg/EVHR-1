
import datetime

# from django.conf import settings
from django.core.management.base import BaseCommand

from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.models import GeoRequest
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

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
        request.startDate   = params['startDate']
        request.endDate     = params['endDate']
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


        

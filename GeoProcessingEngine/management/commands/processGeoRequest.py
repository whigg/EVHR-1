
from osgeo.osr import SpatialReference

from django.core.management.base import BaseCommand

from ProcessingEngine.management.CommandHelper import CommandHelper
from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from GeoProcessingEngine.models import GeoRequest

#-------------------------------------------------------------------------------
# Command
#
# --- Crystal Fire ---
# ./manage.py processGeoRequest --name testCrystal --epName "TestEndPoint" -o ~/Desktop/SystemTesting/GeoRequest/Crystal --ulx -113.39250146 --uly 43.35041085 --lrx -112.80953835 --lry 42.93059617 --epsg 4326 --outEpsg 102039 --startDate 08-04-2016 --endDate 01-31-2017 -n 1
#
# --- GSENM ---
# ./manage.py processGeoRequest --name testGSENM --epName "Biophysical Setting" -o ~/Desktop/SystemTesting/GeoRequest/GSENM --ulx 36719 --uly 4209000 --lrx 510000 --lry 4094000 --epsg 32612 --outEpsg 102039 --startDate 11-01-2010 --endDate 01-31-2011 -n 1
#
# --- Puerto Rico ---
# ./manage.py processGeoRequest --name puertoRico --epName "Landsat" -o ~/Desktop/SystemTesting/GeoRequest/PuertoRico --ulx -68 --uly 18 --lrx -64 --lry 17 --epsg 4326 --outEpsg 102039 --startDate 08-01-2017 --endDate 09-25-2017 -n 1
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):
        
        parser.add_argument('--epName',
                            help = 'The end point name to process.')
        
        parser.add_argument('--ulx',     type = float)
        parser.add_argument('--uly',     type = float)
        parser.add_argument('--lrx',     type = float)
        parser.add_argument('--lry',     type = float)
        parser.add_argument('--epsg',    type = int)
        parser.add_argument('--outEpsg', type = int)

        CommandHelper.addCommonArgs(parser)
                       
    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):
        
        request             = GeoRequest()
        request.name        = options['name']
        request.destination = options['o']
        request.startDate   = options['startDate']
        request.endDate     = options['endDate']
        request.started     = True
        request.ulx         = options['ulx']
        request.uly         = options['uly']
        request.lrx         = options['lrx']
        request.lry         = options['lry']
        
        ep = EndPoint.objects.filter(name = options['epName'])[0]
        request.endPoint = ep
        
        request.srs = \
            GeoRetriever.constructSrsFromIntCode(options['epsg']).ExportToWkt()
        
        request.outSRS = \
            GeoRetriever.constructSrsFromIntCode(options['outEpsg']). \
            ExportToWkt()
        
        request.save()
        
        CommandHelper.handle(request, args, options)


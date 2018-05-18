
from osgeo.osr import SpatialReference

from django.core.management.base import BaseCommand

from ProcessingEngine.management.CommandHelper import CommandHelper
from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from GeoProcessingEngine.models import GeoRequest

from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# Command
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
        
        parser.add_argument('--scenes', 
                            help = 'A comma-separated list of ' \
                                   'fully-qualified scene files.')

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
        
        scenes = options['scenes']
        
        for scene in scenes:
            
            evhrScene = EvhrScene()
            evhrScene.request = request
            evhrScene.sceneFile = scene
            evhrScene.save()
            
        CommandHelper.handle(request, args, options)


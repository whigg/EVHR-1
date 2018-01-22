
from django.core.management.base import BaseCommand

from ProcessingEngine.models import EndPoint
from ProcessingEngine.models import Request
from ProcessingEngine.management.CommandHelper import CommandHelper

#-------------------------------------------------------------------------------
# Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):
        
        parser.add_argument('--epName')
        CommandHelper.addCommonArgs(parser)
                            
    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(self, *args, **options):
        
        endPoint = EndPoint.objects.get(name = options['epName'])

        request             = Request()
        request.name        = options['name']
        request.endPoint    = endPoint
        request.destination = options['o']
        request.startDate   = options['startDate']
        request.endDate     = options['endDate']
        request.started     = True
        request.save()
        
        CommandHelper.handle(request, args, options)
        


from django.core.management.base import BaseCommand

from ProcessingEngine.management.CommandHelper import CommandHelper
from ProcessingEngine.management.RequestProcessor import RequestProcessor

from GeoProcessingEngine.models import GeoRequest

#-------------------------------------------------------------------------------
# Command
#
# ./manage.py reprocessGeoRequest --id 401
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):
        
        CommandHelper.addReprocessingArgs(parser)
        
    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(*args, **options):
       
        request = GeoRequest.objects.get(id = options['id'])
        CommandHelper.handleReprocessing(request, args, options)
           

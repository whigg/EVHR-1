
from datetime import datetime
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

from ProcessingEngine.models import Request

#-------------------------------------------------------------------------------
# Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(self, **options):
    
        purgeRequests()
        
#-------------------------------------------------------------------------------
# purgeReqs
#-------------------------------------------------------------------------------
def purgeRequests():

    timeThreshold = datetime.now() - \
                    timedelta(days = settings.DAYS_UNTIL_REQUEST_PURGE)
                    
    results = Request.objects.filter(created__lt = timeThreshold)
    print 'Purging ' + str(results.count()) + ' request(s).'
    results.delete()
    
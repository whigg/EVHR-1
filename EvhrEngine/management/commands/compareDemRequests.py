
from glob import glob
import os

from django.core.management.base import BaseCommand

from ProcessingEngine.models import Request

#-------------------------------------------------------------------------------
# compareDemRequests
#
# ./manage.py compareDemRequests 632 633
# 
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('request1')
        parser.add_argument('request2')

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):
        
        req1 = Request.objects.get(id=options['request1'])
        req2 = Request.objects.get(id=options['request2'])
        
        if not os.path.exists(str(req1.destination)):

            raise RuntimeError('Request directory, ' + 
                               str(req1.destination) + 
                               ' does not exist.')
        
        if not os.path.exists(str(req2.destination)):

            raise RuntimeError('Request directory, ' + 
                               str(req2.destination) + 
                               ' does not exist.')
        
        reqDir1 = os.path.join(str(req1.destination), 'dems')
        reqDir2 = os.path.join(str(req2.destination), 'dems')

        # Check for the same pairs.
        req1PairDirs = [f for f in glob(reqDir1 + '/W*') if os.path.isdir(f)]
        req2PairDirs = [f for f in glob(reqDir2 + '/W*') if os.path.isdir(f)]
        
        req1PairDirs.sort()
        req2PairDirs.sort()
        
        if req1PairDirs == req2PairDirs:
            
            print 'Both requests have the same pairs.'

        else:
            print 'The requests do not have the same pairs.'
            print 'Request 1 pairs: ' + str(req1PairDirs)
            print 'Request 2 pairs: ' + str(req2PairDirs)            
        

import glob
import os

from django.core.management.base import BaseCommand

#-------------------------------------------------------------------------------
# compareDemRequests
#
# ./manage.py compareDemRequests /att/nobackup/rlgill/evhrDevelopmentOutput/requests/Myanmar_DEM_Roger-bdA0xCH1pfPdvKjkPOdkiP4asDnVAOp1G-vQx_MC /att/nobackup/rlgill/evhrDevelopmentOutput/requests/Myanmar_DEM_Roger-jQK9GA_uur3VfnhxtliITR-oMpGWEn1nwAlJPh1-
# 
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('requestDir1')
        parser.add_argument('requestDir2')

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        reqDir1 = options['requestDir1']
        reqDir2 = options['requestDir2']
        
        if not os.path.exists(reqDir1):

            raise RuntimeError('Request directory, ' + 
                               reqDir1 + 
                               ' does not exist.')
        
        if not os.path.exists(reqDir2):

            raise RuntimeError('Request directory, ' + 
                               reqDir2 + 
                               ' does not exist.')
        
        reqDir1 = os.path.join(reqDir1, 'dems')
        reqDir2 = os.path.join(reqDir2, 'dems')

        # Check for the same pairs.
        req1PairDirs = [f for f in os.listdir(reqDir1) if os.path.isdir(f)]
        print (str(req1PairDirs))

        
        
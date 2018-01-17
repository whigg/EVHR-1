
import glob
import logging
import os

from django.core.management.base import BaseCommand

from GeoProcessingEngine.management.LandsatNbrNdviHelper import LandsatNbrNdviHelper

#-------------------------------------------------------------------------------
# class LandsatNbr
#-------------------------------------------------------------------------------
class LandsatNbr(LandsatNbrNdviHelper):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, outFile, keepBandFiles = False, logger = None):

        super(LandsatNbr, self).__init__(outFile, 'NBR', keepBandFiles, logger)
        
    #---------------------------------------------------------------------------
    # getBandNamesNeeded
    #---------------------------------------------------------------------------
    def getBandNamesNeeded(self, sensor):
        
        bands = ['sr_band7', 'pixel_qa']
        
        if sensor == 'E' or sensor == 'T':
        
            bands.append('sr_band4')

        elif sensor == 'C':
            
            bands.append('sr_band5')
        
        else:
            raise RuntimeError('Unknown sensor: ' + str(sensor))
            
        return bands
            
    #---------------------------------------------------------------------------
    # getNirBandFile
    #---------------------------------------------------------------------------
    def getNirBandFile(self, sensor, bandFiles):
        
        if sensor == 'E' or sensor == 'T':
        
            return self.getBandFileName('sr_band4', bandFiles)

        elif sensor == 'C':
            
            return self.getBandFileName('sr_band5', bandFiles)

        else:
            raise RuntimeError('Unknown sensor: ' + str(sensor))

    #---------------------------------------------------------------------------
    # getRedBandFile
    #---------------------------------------------------------------------------
    def getRedBandFile(self, sensor, bandFiles):

        return self.getBandFileName('sr_band7', bandFiles)
        
#------------------------------------------------------------------------
# Command
#
# Use this to test outside of WranglerProcess.
#
# ./manage.py LandsatNbr /tmp /mnt/data-store/sites/Crystal\ Fire\ GPCP\ 2-eeyGyGOsjlSsARJvbeu6LKaV0Lm0-KYm47L9kDtZ/Landsat/ 2017-01-01 --keepBandFiles
#------------------------------------------------------------------------
class Command(BaseCommand):
    
    #--------------------------------------------------------------------
    # add_arguments
    #--------------------------------------------------------------------
    def add_arguments(self, parser):
        
        parser.add_argument('outDir')
        parser.add_argument('bandDir')
        parser.add_argument('date', help = 'YYYY-MM-DD')
        parser.add_argument('--keepBandFiles', action="store_true")

    #--------------------------------------------------------------------
    # handle_noargs
    #--------------------------------------------------------------------
    def handle(*args, **options):

        logger   = logging.getLogger('console')
        outDir   = options['outDir']
        bandDir  = options['bandDir']
        date     = options['date']
        outFile  = os.path.join(outDir, 'LS_NBR_' + date + '.tif')

        globStmt  = os.path.join(bandDir, date + '_*.tif')
        bandFiles = glob.glob(globStmt)

        lsCreator = LandsatNbr(outFile, options['keepBandFiles'], logger)
        lsCreator.run(bandFiles)





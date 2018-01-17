
import glob
import os

from django.core.management.base import BaseCommand

from GeoProcessingEngine.management.LandsatNbrNdviHelper import LandsatNbrNdviHelper

#-------------------------------------------------------------------------------
# class LandsatNdvi
#-------------------------------------------------------------------------------
class LandsatNdvi(LandsatNbrNdviHelper):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, outFile, keepBandFiles = False, logger = None):

        super(LandsatNdvi, self).__init__(outFile, 'NDVI', keepBandFiles,logger)
        
    #---------------------------------------------------------------------------
    # getBandNamesNeeded
    #---------------------------------------------------------------------------
    def getBandNamesNeeded(self, sensor):
        
        bands = ['sr_band4', 'pixel_qa']
        
        if sensor == 'E' or sensor == 'T':
        
            bands.append('sr_band3')

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

        if sensor == 'E' or sensor == 'T':
        
            return self.getBandFileName('sr_band3', bandFiles)

        elif sensor == 'C':
            
            return self.getBandFileName('sr_band4', bandFiles)

        else:
            raise RuntimeError('Unknown sensor: ' + str(sensor))
        
#-------------------------------------------------------------------------------
# Command
#
# Use this to test outside of WranglerProcess.
#
# ./manage.py LandsatNdvi /tmp /mnt/data-store/sites/Crystal\ Fire\ GPCP\ 2-eeyGyGOsjlSsARJvbeu6LKaV0Lm0-KYm47L9kDtZ/Landsat/ 2017-01-01
#-------------------------------------------------------------------------------
class Command(BaseCommand):
    
    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):
        
        parser.add_argument('outDir')
        parser.add_argument('bandDir')
        parser.add_argument('date')
        parser.add_argument('-d', action="store_true")

    #---------------------------------------------------------------------------
    # handle_noargs
    #---------------------------------------------------------------------------
    def handle(*args, **options):
        
        if options['d']:
            pdb.set_trace()

        logger   = logging.getLogger('console')
        outDir   = options['outDir']
        bandDir  = options['bandDir']
        date     = options['date']
        outFile  = os.path.join(outDir, 'LS_NDVI_' + date + '.tif')

        globStmt  = os.path.join(bandDir, date + '_*.tif')
        bandFiles = glob.glob(globStmt)

        lsCreator = LandsatNdvi(outFile, bandFiles, logger)
        lsCreator.run()





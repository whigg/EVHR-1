
import csv
import datetime
import gzip
import logging
import os
import shutil
import urllib2

from django.core.management.base import BaseCommand

from WranglerProcess import settings
from GeoProcessingEngine.models import LandsatMetadata

#------------------------------------------------------------------------
# Command
#
# crontab -e
# 0 3 * * * /mnt/data-store/WrangleAndMunge/manage.py downloadLandsatMeta
#
# https://landsat.usgs.gov/download-entire-collection-metadata
#------------------------------------------------------------------------
class Command(BaseCommand):
        
    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):
    
        self.logger = logging.getLogger('django')
        self.logger.setLevel(logging.INFO)
        self.logger.info('Running downloadLandsatMeta at ' + 
                         str(datetime.datetime.now()))

        BASE_URL = 'https://landsat.usgs.gov/landsat/metadata_service/bulk_metadata_files'

        # ONE_TIME_URLS = [BASE_URL + '/LANDSAT_ETM_SLC_OFF.csv.gz']
        
        # URLS = [BASE_URL + '/LANDSAT_ETM.csv.gz',
        #         BASE_URL + '/LANDSAT_8.csv.gz']

        URLS = [BASE_URL + '/LANDSAT_ETM_C1.csv.gz',
                BASE_URL + '/LANDSAT_8_C1.csv.gz']

        META_DIR = settings.WRANGLE_SETTINGS['downloadDir']

        for url in URLS:
        
            url  = url.strip()
            name = os.path.basename(url)

            self.logger.info('Downloading ' + url)
                
            # Download
            gzFile = os.path.join(META_DIR, name).strip()
            req    = urllib2.urlopen(url)

            with open(gzFile, 'wb') as f:
                shutil.copyfileobj(req, f)      
        
            # Unzip            
            csvFile = gzFile.rsplit('.', 1)[0]

            with gzip.open(gzFile, 'rb') as f:
                with open(csvFile, 'w') as cf:
                    cf.write(f.read())
                    
            os.remove(gzFile)

            # Update database from CSV file.
            first     = True
            csvReader = csv.reader(open(csvFile), delimiter = ',')
            maxPath   = 0
            maxRow    = 0
            
            for row in csvReader:
            
                if first:
                    first = False
                    continue
                    
                sceneID   = row[2] # row[0]
                productID = row[3]
                tier      = productID.split('_')[-1].lower()
                
                # if sceneID.lower()[0:2] != 'lt':
                if productID.lower()[0:2] != 'lt' and tier == 't1':
                    
                    print 'Saving ' + str(productID)
                    
                    lsm                 = LandsatMetadata()
                    lsm.acquisitionDate = row[5]
                    lsm.productID       = productID
                    lsm.sceneID         = sceneID
                    lsm.path            = int(row[7])
                    lsm.row             = int(row[8])
                    lsm.save()
                    
                    if lsm.path > maxPath:
                        maxPath = lsm.path
                        
                    if lsm.row > maxRow:
                        maxRow = lsm.row
                
            os.remove(csvFile)

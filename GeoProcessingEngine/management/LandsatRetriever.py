
from base64 import b64encode        # submit
import datetime                     # createPfDict
import httplib                      # submit
import json
import os
import shutil
import tarfile                      # unzip
import time
import urllib                       # submit
import urllib2                      # download

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from GeoProcessingEngine.management.WorldReferenceSystem import WorldReferenceSystem
from GeoProcessingEngine.models import LandsatMetadata

from LandsatNbr  import LandsatNbr
from LandsatNdvi import LandsatNdvi

#-------------------------------------------------------------------------------
# class LandsatRetriever
#
# Scene ID:   LE70400302016143EDC00
# TGZ File:   LE70400302016143-SC20160613144318.tar.gz
# Band File:  LE70400302016143_sr_band3.tif
#
# Generalized process:
# Date 1
#   scene0 -> scene0.tgz -> scene0_band1.tif, scene0_band2.tif
#   scene0 -> scene1.tgz -> scene1_band1.tif, scene1_band2.tif
#                                  |                 |
#                                  v                 v
#                           band1_mosaic.tif, band2_mosaic.tif -> ndvi.tif
#
# Wrangler Model Structure
#   Predictor = Landsat
#     PredictorFile = LS_NDVI_2016-03-09.tif
#     PredictorFile = LS_NDVI_2016-03-11.tif
#     ...
#
# http://landsat.usgs.gov/documents/espa_odi_userguide.pdf
# http://landsat.usgs.gov/documents/provisional_lasrc_product_guide.pdf
# https://landsat.usgs.gov/landsat-collections#C1%20Tiers
# https://github.com/USGS-EROS/espa-api
# https://landsat7.usgs.gov/sites/default/files/documents/lasrc_product_guide.pdf
# https://landsat.usgs.gov/wrs-2-pathrow-latitudelongitude-converter
#-------------------------------------------------------------------------------
class LandsatRetriever(GeoRetriever):
    
    # BANDS = ('sr_band3', 'sr_band4', 'sr_band5', 'sr_band7', 'pixel_qa')

    BASE_NAMES                   = ['LS_NBR_', 'LS_NDVI_']
    # COMPLETION_TIME_OUT_IN_HOURS = 24
    DOWNLOAD_URLS_FILE_NAME      = 'DownloadedUrls.txt'
    KEEP_BAND_FILES              = False
    KEEP_TGZ_FILES               = False
    ORDER_NUM_FILE_NAME          = 'OrderNum.txt'
    PRODUCT                      = 'sr'
    TEST_MODE                    = False
    URL_FILE_NAME                = 'OrderUrl.txt'

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger):

        # Landsat gets its own subdirectory because it can have multiple files.
        if not os.path.basename(request.destination.name) == 'Landsat':

            request.destination.name = \
                os.path.join(request.destination.name, 'Landsat')
            
            request.save(update_fields = ['destination'])

        if not os.path.exists(request.destination.name):
            os.mkdir(request.destination.name)

        super(LandsatRetriever, self).__init__(request, logger)
                     
        # Set up the API connection to ESPA.
        ep = self.request.endPoint.url
        
        if '//' in ep:
            protocol, ep = ep.split('//')

        self.conn = httplib.HTTPSConnection(ep + ':443')
        
        userAndPass = b64encode(b'recover.dummy@gmail.com:R3COVERdummy'). \
                      decode('ascii')
        
        self.headers = {'Authorization' : 'Basic %s' % userAndPass}
                                    
    #---------------------------------------------------------------------------
    # awaitCompletion
    #
    # This returns when all scenes are available.  RunOnePredFile() will find 
    # some scenes are already downloaded and extracted.
    #
    # Statuses from ESPA:  submitted, oncache, onorder, queued, processing,
    # error, retry, complete, unavailable
    #---------------------------------------------------------------------------
    def awaitCompletion(self, orderNum):

        atLeastOneNotReady = True
        returnUrls = []
        
        while atLeastOneNotReady:
            
            if self.logger:
                self.logger.info('Awaiting ESPA order completion ...')
                
            atLeastOneNotReady = False
            
            # Get the status of all the products in the order.
            response = self.sendRequest('GET', \
                                        '/api/v1/item-status/' + str(orderNum))

            productStatus = response[orderNum]
            
            for product in productStatus:
                
                status = product['status']
                
                if status == 'submitted'  or \
                   status == 'oncache'    or \
                   status == 'onorder'    or \
                   status == 'queued'     or \
                   status == 'processing':
                    
                    atLeastOneNotReady = True
                    
                elif status == 'complete':
                    
                    url = product['product_dload_url']

                    if not url in returnUrls:
                        
                        returnUrls.append(url)

                elif status == 'unavailable':
                    pass
                        
                elif status == 'retry':
                    pass
                       
                else:
                    raise RuntimeError('Unknown status: ' + status)
                        
            time.sleep(10)
                        
        #---
        # Write the order urls to a file, so we can rerun this job without
        # starting from scratch.
        #---
        urlFile = os.path.join(self.request.destination.name, \
                               LandsatRetriever.DOWNLOAD_URLS_FILE_NAME)

        with open(urlFile, 'w') as fp:
            for url in returnUrls:
                fp.write(url + os.linesep)

        return returnUrls
        
    #---------------------------------------------------------------------------
    # createPfDict
    #
    # {LS_NDVI_2016-03-22.tif, [LE070400302017021801T2-SC20170506132801.tar.gz,
    #                           LE070390302016120901T2-SC20170506132829.tar.gz]
    # {LS_NBR_2016-03-22.tif,  [LC080390302017021901T1-SC20170506123744.tar.gz,
    #                           LC080390302017042401T2-SC20170506123917.tar.gz]
    #  ...}
    #---------------------------------------------------------------------------
    def createPfDict(self, urls):

        predFiles = {}

        for url in urls:

            #---
            # A URL looks like:
            # https://.../LC080400302016112201T1-SC20170508142157.tar.gz
            #---
            nonstandardID = os.path.basename(url).split('-')[0]
            
            year    = int(nonstandardID[10:14])
            month   = int(nonstandardID[14:16])
            day     = int(nonstandardID[16:18])
            date    = datetime.date(year, month, day)
            dateStr = date.strftime('%Y-%m-%d')

            for baseName in LandsatRetriever.BASE_NAMES:
                
                fileName = baseName + dateStr + '.tif'
                fullName = os.path.join(self.request.destination.name, fileName)
                
                if not predFiles.has_key(fullName):
                    predFiles[fullName] = []

                predFiles[fullName].append(url)
                
            if LandsatRetriever.TEST_MODE:
                break

        return predFiles
        
    #---------------------------------------------------------------------------
    # download
    #---------------------------------------------------------------------------
    def download(self, urls):

        files = []

        for url in urls:

            if self.logger:
                self.logger.info('URL: ' + str(url))
                
            url     = url.strip()
            name    = os.path.basename(url)
            outFile = os.path.join(self.request.destination.name, name)
            files.append(outFile)

            if not os.path.exists(outFile):

                req = urllib2.urlopen(url)
        
                with open(outFile.strip(), 'wb') as fp:
                    shutil.copyfileobj(req, fp)      

        return files
        
    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # getProductIDs
    # 
    # https://landsat.usgs.gov/wrs-2-pathrow-latitudelongitude-converter
    #---------------------------------------------------------------------------
    def getProductIDs(self, ulx, uly, lrx, lry, srs, maxIds = 200):
        
        pathRows = WorldReferenceSystem.pathRows(ulx, uly, lrx, lry, srs)
        paths    = [pathRow[0] for pathRow in pathRows]
        rows     = [pathRow[1] for pathRow in pathRows]
        
        minPath = min(paths)
        maxPath = max(paths)
        minRow  = min(rows)
        maxRow  = max(rows)
        
        # Query the scene IDs.
        lsMeta = LandsatMetadata.objects.filter(path__gte = minPath, 
                                                path__lte = maxPath, 
                                                row__gte  = minRow,  
                                                row__lte  = maxRow)
        
        # Filter for the dates.
        lsMeta = lsMeta.filter(acquisitionDate__gte = self.request.startDate, 
                               acquisitionDate__lte = self.request.endDate)

        # Extract just the product IDs from the model.
        allProductIDs = [lm.productID for lm in lsMeta]
        
        #---
        # Filter the scenes for availability.  Plus, ESPA says to avoid all
        # 'RT' scenes.  Avoid 'T2', too.  These should never make it into
        # LandsatMetadata.
        #---
        productIDs = []

        for productID in allProductIDs:
            
            category = productID.split('_')[-1].upper()
            
            if category == 'RT' or category == 'T2':
                continue
            
            orderDict = {'inputs' : [productID]}
            orderParams = json.dumps(orderDict)
            
            response = self.sendRequest('GET', 
                                        '/api/v1/available-products', 
                                        orderParams)
            
            # Ensure there is at least one collection.
            if len(response.keys()) == 0:

                raise RuntimeError('Product, ' + \
                                   productID + \
                                   ', is not in any collections.')
                
            # Each product should only be associated with one collection.
            isDateRestricted = 1 if 'date_restricted' in response.keys() else 0

            if len(response.keys()) - isDateRestricted > 1:
                
                raise RuntimeError('Product, ' + \
                                   productID + \
                                   ', is unexpectedly in multiple collections.')

            # If the retriever's product is available, add it to the list.
            if LandsatRetriever.PRODUCT in response.values()[0]['products']:
                productIDs.append(productID)

        if self.logger:
            self.logger.info('Product IDs: ' + str(productIDs))
            
        return productIDs
        
    #---------------------------------------------------------------------------
    # listConstituents
    #
    # This determines the predictor files that will be produced, and orders the
    # scenes from ESPA.
    #
    #   Returns:
    #     {LS_NDVI_2016-02-23.tif : [LE70390302016054, LE70390302116054],
    #      LS_NDVI_2016-03-01.tif : [LE70390302016062, LE70390302016062],
    #      ...}
    #---------------------------------------------------------------------------
    def listConstituents(self):
        
        productIDs = self.getProductIDs(self.retrievalUlx,
                                        self.retrievalUly,
                                        self.retrievalLrx,
                                        self.retrievalLry,
                                        self.retrievalSRS)

        #---
        # Order Number: returns order number, like RECOVER-1454596673.1
        #---
        orderNumFile = \
            os.path.join(self.request.destination.name, \
                         LandsatRetriever.ORDER_NUM_FILE_NAME)
    
        orderNum = None

        if not os.path.exists(orderNumFile):
        
            orderNum = self.submitOrder(productIDs)

        else:

            with open(orderNumFile, 'r') as fp:
                orderNum = fp.readlines()[0].rstrip()
            
            if self.logger:
                self.logger.info('Using existing order number: ' + orderNum)

        #---
        # Await completion of the order.
        #---
        downloadUrlsFile = \
            os.path.join(self.request.destination.name, \
                         LandsatRetriever.DOWNLOAD_URLS_FILE_NAME)

        urls = None

        if not os.path.exists(downloadUrlsFile):

            urls = self.awaitCompletion(orderNum)

        else:
            with open(downloadUrlsFile, 'r') as fp:
                urls = fp.readlines()

            self.logger.info('Using download urls: ' + downloadUrlsFile)

        # Create the dictionary of PredictorFiles to their constituents.
        predFiles = self.createPfDict(urls)

        return predFiles
        
    #---------------------------------------------------------------------------
    # logIn
    #---------------------------------------------------------------------------
    def logIn(self):
        
        LOGIN_URL = 'https://espa.cr.usgs.gov/login'
        
        self.driver.get(LOGIN_URL)
        
        # Ensure we can find all the fields on the form before continuing.
        userNameElem = self.driver.find_element_by_name('username')
        passwordElem = self.driver.find_element_by_name('password')
        
        # Log in.
        userNameElem.send_keys('recover.dummy@gmail.com')
        passwordElem.send_keys('R3COVERdummy', Keys.TAB, Keys.ENTER)
        self.driver.implicitly_wait(10)

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):
        
        if self.logger:
            self.logger.info('Running ' + constituentFileName)

        if os.path.exists(constituentFileName):

            if self.logger:
                self.logger.info(constituentFileName + \
                                 ' already exists.')
                
            return constituentFileName

        # Get the base file name for the clipped mosaics.
        fileNoExt, ext = os.path.splitext(constituentFileName)
        path, fileName = os.path.split(fileNoExt)
        dateStr        = fileName.split('_')[2]
        baseName       = os.path.join(path, dateStr)
        
        #---
        # Download all constituent zip files at once because their bands must be
        # mosaicked.  
        # Download --> LE70310282016144-SC20160603131921.tar.gz.
        #---
        tgzFiles = self.download(fileList)

        # Get the bands required for this predictor file. 
        lsCreator = None
        
        if 'NDVI' in constituentFileName:
            
            lsCreator = LandsatNdvi(constituentFileName, 
                                    LandsatRetriever.KEEP_BAND_FILES, 
                                    self.logger)
        
        elif 'NBR' in constituentFileName:
            
            lsCreator = LandsatNbr(constituentFileName, 
                                   LandsatRetriever.KEEP_BAND_FILES, 
                                   self.logger)
                            
        sensor = os.path.basename(tgzFiles[0])[1:2]      
        bands = lsCreator.getBandNamesNeeded(sensor)
        
        # Extract, mosaic and clip each band.
        clippedMosaics = []
        
        for band in bands:
            
            # Extract a set of band file for this mosaic.
            bandTifsForMosaic = self.unzip(tgzFiles, [band]).items()[0][1]
            
            # Are all the tifs from the same sensor?
            for tif in bandTifsForMosaic:

                sensor = None
                thisSensor = os.path.basename(tif)[1:2]      
            
                if not sensor:
                
                    sensor = thisSensor

                elif sensor != thisSensor:

                    #---
                    # "'Can you mosaic LE7 and LC8 into the same output file'
                    # the answer to that is definitely no.  The date of
                    # overpass and the responses of the sensors are too
                    # different to be able to make them work together in the
                    # same file without significant djustment of the
                    # reflectance values.  8 and 7 should have different
                    # overpass dates, so you should not see this condition
                    # anyway."
                    #---
                    raise RuntimeError(constituentFileName + \
                                       ' has scenes from multiple sensors.' + \
                                       '   One is ' + str(thisSensor) + \
                                       ', and the other is ' + \
                                       str(sensor) + '.')
                
            # Mosaic (delete band files) and clip (delete mosaic).
            mosName  = baseName + '_' + sensor + '_' + band + '_mosaic.tif'
            clipName = baseName + '_' + sensor + '_' + band + '.tif'
        
            if not os.path.exists(clipName):
            
                self.mosaic(bandTifsForMosaic, 
                            mosName, 
                            LandsatRetriever.KEEP_BAND_FILES)


                self.xformOutput(mosName, clipName)
                os.remove(mosName)
            
            else:
                if not LandsatRetriever.KEEP_BAND_FILES:
                    for tif in bandTifsForMosaic:
                        os.remove(tif)
        
            clippedMosaics.append(clipName)

        # All the bands are extracted, mosaicked and clipped.  Delete zips.
        if not LandsatRetriever.KEEP_TGZ_FILES:
            for tgzFile in tgzFiles:
                os.remove(tgzFile)
            
        #---
        # Aggregate bands into NDVI and NBR here, so we can delete the mosaics
        # to save disk space.
        #---
        lsCreator.run(clippedMosaics)
        del lsCreator
        lsCreator = None

        if not LandsatRetriever.KEEP_BAND_FILES:

            for bf in clippedMosaics:
                try:
                    os.remove(bf)
                except OSError:
                    pass
            
        return constituentFileName
        
    #---------------------------------------------------------------------------
    # sendRequest
    #---------------------------------------------------------------------------
    def sendRequest(self, method, opUrl, params = None):
        
        self.conn.connect()
        self.conn.request(method, opUrl, params, headers = self.headers)
        response = self.conn.getresponse()
        responseMsg = response.read()
        self.conn.close()
        
        if response.status != 200 and response.status != 201:

            raise RuntimeError('status: ' + str(response.status) + ' msg: ' + \
                               responseMsg)
            
        return json.loads(responseMsg)
            
    #---------------------------------------------------------------------------
    # submitOrder
    #
    # https://github.com/USGS-EROS/espa-api/tree/1.0.0
    #
    # curl -v --user recover.dummy@gmail.com:R3COVERdummy -d '{"olitirs8": {"inputs": ["LC81342142016298LGN00", "LC80400302016295LGN00"], "products": ["sr"]}, "etm7": {"inputs": ["LE70390302016296EDC00", "LE70400302016287EDC01"], "products": ["sr"]}, "format": "gtiff"}' https://espa.cr.usgs.gov/api/v1/order
    #---------------------------------------------------------------------------
    def submitOrder(self, sceneIDs):
        
        # Get the scene ID lists, one for Landsat 4-7, another for Landsat 8.
        lcList = []
        leList = []
        
        for sceneId in sceneIDs:
            
            sceneId = sceneId.strip()
            prefix  = sceneId[0:2].lower()
        
            if prefix == 'lc':
        
                lcList.append(sceneId)
            
            elif prefix == 'le':
            
                leList.append(sceneId)
            
            else:
                
                if self.logger:
                    self.logger.info('Unknown prefix, ' + str(prefix) + \
                                     ', found in ' + \
                                     'LandsatRetriever.submitOrder().')
                                       
        # Build the order description.
        orderDict = {'format' : 'gtiff'}
        LC8_KEY   = 'olitirs8_collection' #'olitirs8'
        LE7_KEY   = 'etm7_collection' #'etm7'
        
        if len(lcList) > 0:
            
            if LandsatRetriever.TEST_MODE:
                lcList = lcList[:1]
                
            orderDict[LC8_KEY] = {'inputs' : lcList, 
                                  'products' : [LandsatRetriever.PRODUCT]}

        if len(leList) > 0:
            
            if LandsatRetriever.TEST_MODE:
                leList = leList[:1]
                
            orderDict[LE7_KEY] = {'inputs' : leList, 
                                  'products' : [LandsatRetriever.PRODUCT]}
        
        # If there are no inputs, stop.
        if not LC8_KEY in orderDict and not LE7_KEY in orderDict:
            raise RuntimeError('No Landsat inputs requested.')
        
        orderParams = json.dumps(orderDict)
        
        if self.logger:
            self.logger.info('Order desc.: ' + str(orderParams))

        # Post the order.
        response = self.sendRequest('POST', '/api/v1/order', orderParams)
        orderNum = response['orderid']
        
        #---
        # Write the order description to a file, so we can rerun this job
        # without starting from scratch.
        #---
        orderDescFile = os.path.join(self.request.destination.name, \
                                     LandsatRetriever.ORDER_NUM_FILE_NAME)

        with open(orderDescFile, 'w') as fp:
            fp.write(orderNum)
        
        return orderNum
        
    #---------------------------------------------------------------------------
    # unzip
    # 
    # Input:  (LE70390202016136-SC20160518150801.tar.gz, ...)
    #
    # Output:  {'band4', [LE70310282016144EDC00_toa_band4.tif, ...],
    #           'band5', [LE70310282016144EDC00_toa_band5.tif, ...],
    #           ...}
    #---------------------------------------------------------------------------
    def unzip(self, tgzFiles, bands):

        # Set up the dictionary of bands.
        bandDict = {}
        
        for band in bands:
            bandDict[band] = []
        
        # Extract the bands, and add them to the dictionary.
        atLeastOneBandFound = False

        for tgzFile in tgzFiles:

            tar = tarfile.open(tgzFile)
        
            for f in tar.getnames():
            
                path, ext = os.path.splitext(f)
                
                if ext.upper() == '.TIF':
                    
                    band = '_'.join(path.split('_')[7:])
                    
                    if band in bands:

                        atLeastOneBandFound = True
                        
                        extractedName = \
                            os.path.join(self.request.destination.name,
                                         os.path.basename(f))
            
                        if ext.lower() == '.tif':

                            if not os.path.exists(extractedName):
                                tar.extract(f, self.request.destination.name)
                                
                            bandDict[band].append(extractedName)

            tar.close()

            if not atLeastOneBandFound:
                raise RuntimeError('No bands found in ' + str(tgzFile))

        return bandDict

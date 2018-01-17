
from datetime import date
import ftplib
import math
import os
import shutil

import gdal

from owslib.crs import Crs

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from ModisNdvi import ModisNdvi

#-------------------------------------------------------------------------------
# class ModisRetriever
#
# Overview:
#   This produces mosaics of NDVI files: one mosaic for all the tiles for each
#   date in the date range.
#
# Wrangler Model Structure
#
#   Predictor = MODIS
#     Predictor File = MOD13Q1.A2015337.tif
#     Predictor File = MOD13Q1.A2015353.tif
#     ...
#     Predictor File = MODIS.NDVI.A2016130.tif    These are the computed
#     Predictor File = MODIS.NDVI.A2016131.tif    NDVIs.
#     ...
#
# Stepping through a run:  (paths removed for conciseness)
#
#   getPredFiles()
#     {NDVI.A2016081.tif: [MOD13Q1.A2016081.h09v04.005.2016105122006.hdf'],    
#      NDVI.A2016155.tif: [MOD09GQ.A2016155.h09v04.005.2016157064840.hdf],
#      ...}
#
#   runOnePredFile()
#
#     runOneMod13()
#       MOD13Q1.A2016081.h09v04.005.2016105122006.hdf
#         MOD13Q1.A2016081.h09v04.005.2016105122006-reproj.tif       <-- extract
#           NDVI.A2016081.tif                                        <-- mosaic
#
#     runOneMod9()
#       MOD09GQ.A2016155.h09v04.005.2016157064840.hdf
#         MOD09GQ.A2016155.h09v04.005.2016157064840.band1-reproj.tif <-- extract
#         MOD09GQ.A2016155.h09v04.005.2016157064840.band2-reproj.tif <-- extract
#         MOD09GQ.A2016154.h09v04.005.2016156063216.qa-reproj.tif    <-- extract
#
#           NDVI.A2016154.band1.tif                                  <-- mosaic
#           NDVI.A2016154.band2.tif                                  <-- mosaic
#           NDVI.A2016154.qa.tif                                     <-- mosaic
#
#             NDVI.A2016154.tif                                      <-- ndviCre
#-------------------------------------------------------------------------------
class ModisRetriever(GeoRetriever):

    MAX_PROCESSES        = 1
    KEEP_ANCILLARY_FILES = False
    TEST_MODE            = False
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger):

        #---
        # Strip the protocol from the end point.  Django's URL type adds one
        # automatically.
        #---
        protocol, ep = request.endPoint.url.split('//')
        ep = ep.replace('/', '')
        
        if logger:
            logger.info('FTP log in URL: ' + str(ep))
        
        self.baseDir = '/allData/6/MOD13Q1'
        self.dirList = []

        # Log in to the ftp server.
        username = 'anonymous'
        password = '@anonymous'
        self.ftp = ftplib.FTP(ep, username, password)
        self.ftp = ftplib.FTP(ep)
        # self.ftp.set_debuglevel(2)
        self.ftp.login()

        # MODIS gets its own subdirectory because it can have multiple files.
        request.destination.name = os.path.join(request.destination.name,'MODIS')
        request.save(update_fields = ['destination'])

        if not os.path.exists(request.destination.name):
            os.mkdir(request.destination.name)
        
        super(ModisRetriever, self).__init__(request, logger)

    #---------------------------------------------------------------------------
    # composeMosaicName
    #
    # This determines the mosaic name into which an HDF file feeds.  This is
    # where the two types of mosaic names (MOD13Q1.A2015337.tif and
    # MODIS.NDVI.A2016130.tif) originate.
    #---------------------------------------------------------------------------
    def composeMosaicName(self, hdfName):
        
        fileParts      = hdfName.split('.')
        prodDate       = fileParts[1]
        baseName       = 'NDVI.' + prodDate + '.tif'
        mosaicFileName = os.path.join(self.request.destination.name, baseName)

        return mosaicFileName
        
    #---------------------------------------------------------------------------
    # dirCollectorCb
    #---------------------------------------------------------------------------
    def dirCollectorCb(self, line = ''):

        self.dirList.append(line)

    #---------------------------------------------------------------------------
    # extractMod9
    #---------------------------------------------------------------------------
    def extractMod9(self, hdfFile):
        
        #---
        # Reproject to the output SRID.  BaseRetriever has it.  Get bands 1, 2
        # and QA.  That is indexes 0, 1, 3.
        #---
        band1 = self.extractReprojClip(hdfFile, 'sur_refl_b01_1', '.band1')
        band2 = self.extractReprojClip(hdfFile, 'sur_refl_b02_1', '.band2')
        qa    = self.extractReprojClip(hdfFile, 'QC_250m_1',      '.qa')
        
        return band1, band2, qa
        
    #---------------------------------------------------------------------------
    # extractReprojClip
    #---------------------------------------------------------------------------
    def extractReprojClip(self, hdfFile, dsName = 'NDVI', fileSuffix = ''):
        
        # Determine the position of the NDVI data set within the file.
        f           = gdal.Open(hdfFile)
        subDataSets = f.GetSubDatasets()
        dsName      = dsName.upper()
        
        for ds in subDataSets:
            if dsName in ds[1].upper():
                break
        
        # Reproject to the output SRID.  BaseRetriever has it.
        path, ext   = os.path.splitext(hdfFile)
        path       += fileSuffix
        reprojFile  = path + '-reproj.tif'
        
        cmd = 'gdalwarp '    + \
              '-multi '      + \
              '-nomd '       + \
              '-tr 250 250 ' + \
              '-s_srs "' + self.retrievalSRS.ExportToProj4()  + '" ' + \
              '-t_srs "' + self.outSRS.ExportToProj4() + '" ' + \
              "'" + \
              ds[0] + "' \"" + \
              reprojFile + '"'
        
        if self.logger != None:
            self.logger.info(cmd)
            
        result = os.system(cmd)

        if result != 0:
            raise RuntimeError('gdalwarp failed.')

        outFile = path + '.tif'

        if not ModisRetriever.KEEP_ANCILLARY_FILES:

            shutil.move(reprojFile, outFile)

        else:
            shutil.copyfile(reprojFile, outFile)
            
        return outFile

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.MODIS_SINUSOIDAL_6842]

    #---------------------------------------------------------------------------
    # getFtpDirs
    #---------------------------------------------------------------------------
    def getFtpDirs(self):
    
        ftpDirs = []
        
        # This is depth-first search.
        yearDirs = self.readFtpDir(self.baseDir)
        
        for yearDir in yearDirs:
            
            try:
                year = int(yearDir)

                if year >= self.request.startDate.year and \
                   year <= self.request.endDate.year:
                
                    yearDirFullPath = self.baseDir + '/' + yearDir
                    dayDirs         = self.readFtpDir(yearDirFullPath)
                    daysUpToYear    = date(year, 1, 1).toordinal() - 1
                
                    for dayDir in dayDirs:
                    
                        daysUpToDir = daysUpToYear + int(dayDir)
                        dirDate     = date.fromordinal(daysUpToDir)
                    
                        if dirDate >= self.request.startDate and \
                           dirDate <= self.request.endDate:
                        
                            ftpDirs.append(yearDirFullPath + '/' + dayDir)
            except ValueError:
                # Skip dirs that do not represent years.
                pass
                
        return ftpDirs
    
    #---------------------------------------------------------------------------
    # getLatestDirs
    #---------------------------------------------------------------------------
    def getLatestDirs(self, baseDir, numToGet):
        
        # Get the latest year.
        dirs = self.readFtpDir(baseDir)
        intDirs = []
        
        for oneDir in dirs:
            
            try:
                intDirs.append(int(oneDir))

            except:
                
                # If the item is not an int, skip it.
                pass
                
        intDirs = sorted(intDirs)[-1 * numToGet :]
        strDirs = []
        
        for intDir in intDirs:
            strDirs.append(os.path.join(baseDir, str(intDir).zfill(3)))
        
        return strDirs
                
    #---------------------------------------------------------------------------
    # listConstituents
    #
    # This is tricky.  This method is required to return a list of files that
    # will ultimately become PredictorFile objects.  In this case, those are the
    # mosaics of every tile covering the AoI for each date.  These will actually
    # be created in aggregatePredFiles().  Each final mosaic consists of a set
    # of HDF files.  These HDF files are the starting point for 
    # runOnePredFile().  
    #
    # This returns a map of predictor file names mapped to their constituent
    # predictor files.
    #
    # /path/to/mosaic1.tif
    #    /path/to/constituent1.hdf
    #    /path/to/constituent2.hdf
    #    /path/to/constituent3.hdf
    # /path/to/mosaic2.tif
    #    /path/to/constituent1.hdf
    #    /path/to/constituent2.hdf
    #    /path/to/constituent3.hdf
    #
    # Returns:
    #  {PredictorFile1: [hdf1, hdf2, ...], 
    #   PredictorFile2: [hdf1, hdf2, ...], 
    #   ...}
    #
    # Example:
    #   {u'/mnt/data-store/sites/
    #    testCrystal Fire-aIkXsWxHKDcO0hCugLu_8-ZJXGHTwBCC_qrB41k4/
    #      MODIS/NDVI.A2016081.tif':
    #     ['/allData/5/MOD13Q1/2016/081/
    #     MOD13Q1.A2016081.h09v04.005.2016105122006.hdf'],...
    #
    #    u'/mnt/data-store/sites/
    #      testCrystal Fire-aIkXsWxHKDcO0hCugLu_8-ZJXGHTwBCC_qrB41k4/
    #      MODIS/NDVI.A2016049.tif': 
    #      ['/allData/5/MOD13Q1/2016/049/
    #      MOD13Q1.A2016049.h09v04.005.2016106092640.hdf'],...}
    #---------------------------------------------------------------------------
    def listConstituents(self):
        
        # Get the bounding box in terms of the tile indicies.
        ulHid, ulVid, lrHid, lrVid = \
            self.getTileIndexBbox(self.retrievalUlx,
                                  self.retrievalUly,
                                  self.retrievalLrx,
                                  self.retrievalLry)

        #---
        # Build a list of all the tile IDs covering the bounding box described
        # by ulHid, ulVid, lrHid, lrVid.
        #---
        tileIds = []

        for h in range(ulHid, lrHid + 1):
            
            for v in range(ulVid, lrVid + 1):

                tileIds.append(('h' + str(h).zfill(2) + \
                                'v' + str(v).zfill(2)).lower())
        
        #---
        # Get the FTP directories by filtering on the start and end dates.
        # These Predictor names will be like MOD13Q1.A2016113.tif.
        #---
        dateDirs = self.getFtpDirs()
        mod13Pfs = self.predFilesFromDateDirs(dateDirs, tileIds)
        
        #---
        # The tiles from MOD13Q1 can be up to sixteen days old.  Get ten days
        # of current imagery.  These Predictor names will be like
        # NDVI.A2016113.tif.
        #---
        baseDir          = '/allData/6/MOD09GQ'
        latestYearDir    = self.getLatestDirs(baseDir, 1)
        baseDir          = os.path.join(baseDir, latestYearDir[0])
        latestTenDayDirs = self.getLatestDirs(baseDir, 10)
        mod09Pfs         = self.predFilesFromDateDirs(latestTenDayDirs, tileIds)

        # Combine the two dictionaries.
        predFiles = mod13Pfs.copy()
        predFiles.update(mod09Pfs)

        if not self.logger:
            self.logger.info('Constituent files: ' + str(predFiles))
            
        return predFiles

    #---------------------------------------------------------------------------
    # getTileIndexBbox   
    #---------------------------------------------------------------------------
    def getTileIndexBbox(self, ulx, uly, lrx, lry):
    
        pixelsPerTile = 4800
        resolution    = 231.656358
        
        X_MIN = -20015109
        Y_MAX = 10007555
        T     = 1111950
        
        ulHid = int(math.floor((ulx - X_MIN) / T))
        ulVid = int(math.floor((Y_MAX - uly) / T))
        lrHid = int(math.floor((lrx - X_MIN) / T))
        lrVid = int(math.floor((Y_MAX - lry) / T))

        if self.logger:
            
            self.logger.info('ModisRetriever.getTileIndexBbox()')
            
            self.logger.info('Request ul    = ' + str(self.request.ulx) + \
                             ', ' + str(self.request.uly))

            self.logger.info('Retrieval ul  = ' + str(self.retrievalUlx) + \
                             ', ' + str(self.retrievalUly))

            self.logger.info('ulHid         = ' + str(ulHid))
            self.logger.info('ulVid         = ' + str(ulVid))

            self.logger.info('Request lr    = ' + str(self.request.lrx) + \
                             ', ' + str(self.request.lry))

            self.logger.info('Retrieval lr  = ' + str(self.retrievalUlx) + \
                             ', ' + str(self.retrievalUly))
                             
            self.logger.info('lrHid         = ' + str(lrHid))
            self.logger.info('lrVid         = ' + str(lrVid))
            
            if abs(lrHid - ulHid) <= 1 or abs(ulVid - lrVid) <= 1:
                
                self.logger.info \
                    ('At 250m MODIS resolution, the output file ' + \
                     'will be smaller than recommended.')
            
        return ulHid, ulVid, lrHid, lrVid
    
    #---------------------------------------------------------------------------
    # isMod9File
    #---------------------------------------------------------------------------
    @staticmethod
    def isMod9File(fileName):
        
        path, baseName = os.path.split(fileName)
        fileParts = baseName.split('.')
        prodName = fileParts[0].upper()
        return prodName == 'MOD09GQ' or prodName == 'NDVI'
        
    #---------------------------------------------------------------------------
    # maxProcesses
    #
    # Retrievers can set the maximum processors they allow.  For
    # example, MODIS can only support one at a time because its
    # access uses FTP.  When multiple processes are attempted,
    # you are asking MODIS to work out of multiple FTP directories
    # from a single connection.
    #---------------------------------------------------------------------------
    def maxProcesses(self):
        
        return ModisRetriever.MAX_PROCESSES
        
    #---------------------------------------------------------------------------
    # predFilesFromDateDirs
    #
    # This produces a list of Predictor Files and the HDF files needed to
    # create each one.
    #
    # MOD13Q1.A2015337.tif:  hdf1, hdf2, ...
    # MODIS.NDVI.A2016135.tif:  hdf1, hdf2, ...
    #---------------------------------------------------------------------------
    def predFilesFromDateDirs(self, dateDirs, tileIds):
        
        predFiles = {}
        
        for dateDir in dateDirs:
            
            dateTiles = self.readFtpDir(dateDir)
            
            #---
            # For each tile, if it is one that we need, compute the output 
            # file name.
            #---
            for hdfName in dateTiles:
                
                tileId = hdfName.split('.')[2].lower()
                
                if tileId in tileIds:
                    
                    mosaicName = self.composeMosaicName(hdfName)
                    
                    if not predFiles.has_key(mosaicName):
                        predFiles[mosaicName] = []
                        
                    predFiles[mosaicName].append(os.path.join(dateDir, hdfName))
                    
        return predFiles

    #---------------------------------------------------------------------------
    # readFtpDir
    #---------------------------------------------------------------------------
    def readFtpDir(self, dir):

        self.dirList = []

        try:

            self.ftp.cwd(dir)
            self.ftp.retrlines('NLST', self.dirCollectorCb)

        except Exception, e:
            
            if self.logger:
                
                self.logger.info(e)
                self.logger.info('dir = ' + str(dir))

            raise e
                
        return self.dirList
    
    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, predFileName, tiles):

        # Download the HDF files.
        hdfs = []

        if not ModisRetriever.TEST_MODE:        
        
            for tile in tiles:

                hdfFile = os.path.join(self.request.destination.name, 
                                       os.path.basename(tile))

                if not os.path.exists(hdfFile):
                    
                    # Get the tile's FTP directory, and CD there.
                    ftpDir = os.path.dirname(tile)
                    self.ftp.cwd(ftpDir)
                    self.runFtp(tile, hdfFile)
                    
                hdfs.append(hdfFile)
            
        # Send the HDFs to a processor.
        runMod9 = ModisRetriever.isMod9File(hdfs[0])
        
        if runMod9:
            
            self.runOneMod9(hdfs, predFileName)
            
        else:

            if not ModisRetriever.TEST_MODE:
                self.runOneMod13(hdfs, predFileName)

        # Clip and transform to the output SRS.
        path, fullName = os.path.split(predFileName)
        name, ext      = os.path.splitext(fullName)
        beforeWarpFile = path + '/' + name + '-beforeXformOutput' + ext

        shutil.move(predFileName, beforeWarpFile)
        self.xformOutput(beforeWarpFile, predFileName)

        if not ModisRetriever.KEEP_ANCILLARY_FILES:
            os.remove(beforeWarpFile)

        return predFileName

    #---------------------------------------------------------------------------
    # runFtp
    #---------------------------------------------------------------------------
    def runFtp(self, tile, outFile):
        
        fp = open(outFile, 'wb')
        self.ftp.retrbinary('RETR ' + tile, fp.write)
        fp.close()
        
    #---------------------------------------------------------------------------
    # runOneMod9
    #---------------------------------------------------------------------------
    def runOneMod9(self, hdfs, predFileName):
        
        if not ModisRetriever.TEST_MODE:
            
            band1Tifs = []
            band2Tifs = []
            qaTifs    = []
        
            for hdf in hdfs:
            
                # This produces MOD09GQ.Adate.band1.tif, ...2.tif, ...qa.tif.
                b1, b2, qa = self.extractMod9(hdf)
                
                if not ModisRetriever.KEEP_ANCILLARY_FILES:
                    os.remove(hdf)
                
                band1Tifs.append(b1)
                band2Tifs.append(b2)
                qaTifs.append(qa)
        
            # All the band1's must be mosaicked, then band2 and qa's.
            name, ext     = os.path.splitext(predFileName)
            band1MosName  = name + '.band1.tif'
            band2MosName  = name + '.band2.tif'
            qaMosName     = name + '.qa.tif'
            NO_DATA_VALUE = -28672
        
            if not os.path.exists(band1MosName):
                
                self.mosaic(band1Tifs, 
                            band1MosName, 
                            ModisRetriever.KEEP_ANCILLARY_FILES, 
                            NO_DATA_VALUE)

            if not os.path.exists(band2MosName):

                self.mosaic(band2Tifs, 
                            band2MosName, 
                            ModisRetriever.KEEP_ANCILLARY_FILES, 
                            NO_DATA_VALUE)

            if not os.path.exists(qaMosName):

                self.mosaic(qaTifs, 
                            qaMosName, 
                            ModisRetriever.KEEP_ANCILLARY_FILES, 
                            NO_DATA_VALUE)

        # Insert NDVI process here.
        baseName    = os.path.basename(predFileName)
        productName = baseName.split('.')[1]
        ndviCreator = ModisNdvi(productName, self.request.destination.name)
        ndviCreator.run()
        
        if not ModisRetriever.KEEP_ANCILLARY_FILES:

            os.remove(band1MosName)
            os.remove(band2MosName)
            os.remove(qaMosName)
        
        return predFileName
        
    #---------------------------------------------------------------------------
    # runOneMod13
    #---------------------------------------------------------------------------
    def runOneMod13(self, hdfs, predFileName):
        
        tifs = []
        
        for hdf in hdfs:

            # MOD 13 contains NDVI, extract it.
            tifs.append(self.extractReprojClip(hdf))

            if not ModisRetriever.KEEP_ANCILLARY_FILES:
                os.remove(hdf)
        
        NO_DATA_VALUE = -3000
        
        self.mosaic(tifs,
                    predFileName,
                    ModisRetriever.KEEP_ANCILLARY_FILES, 
                    NO_DATA_VALUE)

        return predFileName
        

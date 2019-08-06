import os
import shutil
import tempfile

import gdal
import numpy

from django.conf import settings

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.GdalFile import GdalFile
from EvhrEngine.management.EvhrToaRetriever import EvhrToaRetriever
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# class EvhrSrRetriever
#-------------------------------------------------------------------------------
class EvhrSrRetriever(EvhrToaRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # Initialize the base class.
        super(EvhrSrRetriever, self).__init__(request, logger, numProcesses)

        self.srInputDir = os.path.join(self.request.destination.name, '6-srIn')
        
        if not os.path.exists(self.srInputDir):
            os.mkdir(self.srInputDir)
            
        # Copy the look-up files.
        lu0 = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'SurfaceReflectance/LUT_WV2.0.bin')

        lu1 = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'SurfaceReflectance/LUT_WV2.1.bin')

        shutil.copy(lu0, self.srInputDir)
        shutil.copy(lu1, self.srInputDir)
            
        self.srOutputDir = os.path.join(self.request.destination.name, 
                                        '7-srOut')
        
        if not os.path.exists(self.srOutputDir):
            os.mkdir(self.srOutputDir)
            
        self.srInputFileName = os.path.join(self.srInputDir, 'srInput.txt')

    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):

        # This is where the mosaic data set is created from the set of ToAs.
        pass

    #---------------------------------------------------------------------------
    # createWv2
    #
    # WVimg5 /att/pubrepo/MAIAC-ancillary/results/runtime_Canada.txt file_Barrow
    # Barrow
    # File_Barrow = 6-sr/srInput.txt
    #---------------------------------------------------------------------------
    def createWv2(self, toaName):
        
        wv2File = \
            os.path.join(self.srInputDir, 
                         os.path.basename(toaName).replace('.tif', '.wv2'))

        if not os.path.exists(wv2File):
            
            if self.logger:
                self.logger.info('Creating wv2 file from ' + str(toaName))

            wvImgExe = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'SurfaceReflectance/WVimg5')
        
            #---
            # This file is used by WVImg5 to identify the MAIAC files to use.
            # This needs to be generalized, but it's all that Yujie provided.
            #---
            maiacFile ='/att/pubrepo/MAIAC-ancillary/results/runtime_Canada.txt'

            #---
            # WVimg5 wants to process all IDs in srInput.txt, while we need it
            # to only process this one.  To work around that, create a
            # temporary file containing only this ID.
            #---
            oneID = os.path.basename(toaName)
            tempInput = tempfile.mkstemp()[1]
            
            with open(tempInput, 'w') as f:
                f.write(os.path.splitext(os.path.basename(toaName))[0]+'\n')
            
            # WVimg5   MAIACruntimefile  imagelistfile   TOApath
            cmd = wvImgExe + ' ' + \
                  maiacFile + ' ' + \
                  tempInput + ' ' + \
                  self.srInputDir
              
            sCmd = SystemCommand(cmd, None, self.logger, self.request, True,
                                 self.maxProcesses != 1)
                                 
            os.remove(tempInput)
        
        return wv2File

    #---------------------------------------------------------------------------
    # getLatLon 
    #
    # According to Yujie's script, WV02Cal.py, which is the example used here
    # to create the .meta files for the SR process, the UL and LR values are
    # "messed up" in the XML.  While this might have been the case at some 
    # point, it is not now.  To be safe, this method will validate the UL and
    # LR, swapping them as needed, to accommodate both correct and incorrect
    # XML files.
    #---------------------------------------------------------------------------
    def getLatLon(self, imgTag):
        
        ulLat = float(imgTag.find('BAND_B/ULLAT').text)
        ulLon = float(imgTag.find('BAND_B/ULLON').text)
        lrLat = float(imgTag.find('BAND_B/LRLAT').text)
        lrLon = float(imgTag.find('BAND_B/LRLON').text)
        lat = ulLat
        lon = ulLon
        
        if ulLat < lrLat:
            lat = lrLat
            
        if ulLon > lrLon:
            lon = lrLon
            
        return lat, lon
        
    #---------------------------------------------------------------------------
    # getScenes
    #---------------------------------------------------------------------------
    def getScenes(self, request, ulx, uly, lrx, lry, srs):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = request)
        sceneFiles = []

        if evhrScenes:
            
            sceneFiles = self._validateScenes(evhrScenes)
            
            for sceneFile in sceneFiles:
                
                dgf = DgFile(sceneFile)
                
                if dgf.isPanchromatic():
                    
                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            sceneFile.fileName + \
                                            ' is being skipped because' + \
                                            ' it is panchromatic.')
                                            
                if dgf.sensor() != 'WV02' and dgf.sensor() != 'WV03':

                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            sceneFile.fileName + \
                                            ' is being skipped because' + \
                                            ' it is not WV02 or WV03.')
                                            
        else:
            
            fpScenes = None
            fpq = FootprintsQuery(logger=self.logger)
            fpq.addAoI(ulx, uly, lrx, lry, srs)
            fpq.setMinimumOverlapInDegrees()
            fpq.addSensors(['WV02', 'WV03'])
            fpq.setPanchromaticOff()

            maxScenes = EvhrToaRetriever.MAXIMUM_SCENES
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                maxScenes = min(maxScenes, settings.MAXIMUM_SCENES)
                
            fpq.setMaximumScenes(maxScenes)
            fpScenes = fpq.getScenes()
            self._fpScenesToEvhrScenes(fpScenes)
            sceneFiles = [fps.fileName() for fps in fpScenes]
                
        sceneFiles.sort()
        
        return sceneFiles

    #---------------------------------------------------------------------------
    # listConstituents
    #
    # Constituent: SR file
    # Files:  scenes for a single ToA strip
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query for scenes.
        scenes = self.getScenes(self.request,
                                self.retrievalUlx,
                                self.retrievalUly,
                                self.retrievalLrx,
                                self.retrievalLry,
                                self.retrievalSRS)

        if not scenes and self.logger:
            self.logger.error('No multispectral scenes for WV2 or WV3.')

        # Aggregate the scenes into ToAs.
        toas = {}
        
        for scene in scenes:
            
            dgf = DgFile(scene, self.logger)
            stripID = dgf.getStripName()
            toaName = os.path.join(self.toaDir, stripID + '-toa.tif')

            if not toas.has_key(toaName):
                toas[toaName] = []
                
            toas[toaName].append(scene)
            
        # Aggregate the ToAs into SRs and create the SR input file.
        constituents = {}
        
        if os.path.exists(self.srInputFileName):
            os.remove(self.srInputFileName)
        
        with open(self.srInputFileName, 'aw+') as f:
            
            for toa in sorted(toas):
                
                srBaseName = os.path.basename(toa).replace('-toa.tif', '.bin')
                srName = os.path.join(self.srOutputDir, srBaseName)
                constituents[srName] = toas[toa]
                f.write(os.path.splitext(os.path.basename(srBaseName))[0]+'\n')

        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):
        
        stripName = DgFile(fileList[0], self.logger).getStripName()
        stripBandList = self.scenesToStrip(stripName, fileList)

        toaName = os.path.join(self.toaDir,
                               os.path.basename(constituentFileName). \
                                   replace('.bin', '.tif'))

        self.processStrip(stripBandList, toaName)
        # self.toaToBin(toaName)
        DgFile(toaName).toBandInterleavedBinary(self.srInputDir)
        self.writeMeta(toaName)
        self.createWv2(toaName)
        self.runSr(stripName)
        
    #---------------------------------------------------------------------------
    # runSr
    #---------------------------------------------------------------------------
    def runSr(self, stripName):
        
        srFile = os.path.join(self.srOutputDir, stripName + '.bin')

        if not os.path.exists(srFile):
            
            srExe = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'SurfaceReflectance/MAIAC_WV2_5')
        
            cmd = srExe + ' ' + \
                  stripName + ' ' + \
                  self.srInputDir + ' ' + \
                  self.srOutputDir
            
            sCmd = SystemCommand(cmd, None, self.logger, self.request, True,
                                 self.maxProcesses != 1)
            
        return srFile      
                  
    #---------------------------------------------------------------------------
    # toaToBin
    #
    # line 1, band 1
    # line 1, band 2
    # ...
    # line2, band 1
    # line2, band 2
    # ...
    #---------------------------------------------------------------------------
    # def toaToBin(self, toaName):
    #
    #     binFileName = \
    #         os.path.join(self.srInputDir,
    #                      os.path.basename(toaName).replace('.tif', '.bin'))
    #
    #     if not os.path.exists(binFileName):
    #
    #         if self.logger:
    #             self.logger.info('Extracting raster from ' + str(toaName))
    #
    #         toaGdalFile = GdalFile(toaName)
    #
    #         with open(binFileName, 'w') as f:
    #
    #             for lineNum in range(toaGdalFile.dataset.RasterYSize):
    #                 for bandNum in range(toaGdalFile.dataset.RasterCount):
    #
    #                     band = toaGdalFile.dataset.GetRasterBand(bandNum + 1)
    #
    #                     npa = band.ReadAsArray(0,
    #                                            lineNum,
    #                                            toaGdalFile.dataset.RasterXSize,
    #                                            1)
    #
    #                     npa.tofile(f)
    #
    #     return binFileName
        
    #---------------------------------------------------------------------------
    # writeMeta
    #---------------------------------------------------------------------------
    def writeMeta(self, toaName):
        
        metaFileName = \
            os.path.join(self.srInputDir, 
                         os.path.basename(toaName).replace('.tif', '.meta'))

        if not os.path.exists(metaFileName):
            
            if self.logger:
                self.logger.info('Extracting metadata from ' + str(toaName))

            dgFile = DgFile(toaName)

            # Time-related fields.
            date = dgFile.firstLineTime().strftime('%Y-%m-%d')
            hour = dgFile.firstLineTime().strftime('%H')
            minute = dgFile.firstLineTime().strftime('%M')
            minutes = float(hour) * 60.0 + float(minute)

            # Angles, elevations, etc.
            SZA = 90.0 - dgFile.meanSunElevation()
            VZA = 90.0 - dgFile.meanSatelliteElevation()
            SAZ = dgFile.meanSunAzimuth()
            VAZ = dgFile.meanSatelliteAzimuth()
            
            relAZ = SAZ - VAZ
         
            if (RelAZ > 360):
                
                RelAZ -= 360
                 
            elif (RelAZ<-360):
                
                RelAZ += 360

            RelAZ = math.fabs(180 - math.fabs(RelAZ)
        
            #---
            # Projection information
            #
            # According to Yujie, "The xml file has messed up UL and LR," hence
            # the seemingly misnamed tags.
            #---
            lat, lon = self.getLatLon(dgFile.imdTag)
            projWords = dgFile.srs.GetAttrValue('projcs').split()
            xScale = dgFile.dataset.GetGeoTransform()[1]
            yScale = dgFile.dataset.GetGeoTransform()[5]
            ulx = dgFile.dataset.GetGeoTransform()[0]
            uly = dgFile.dataset.GetGeoTransform()[3]
        
            # Write the file.
            with open(metaFileName, 'w') as f:
            
                f.write(date)
                f.write('   %d\n' % minutes)
                f.write('%f   %f\n' % (lat, lon))
                f.write('%f   %f   %f   %f   %f \n' % (SZA, VZA,SAZ,VAZ,relAZ))
            
                f.write('%d   %d\n' % (dgFile.dataset.RasterYSize, 
                                       dgFile.dataset.RasterXSize))
            
                f.write('%s   %s\n' % (projWords[-1][0:-1], projWords[-1][-1]))
                f.write('%f   %f   %f   %f\n' % (ulx, xScale, uly, yScale))
                f.write(dgFile.dataset.GetProjection())

        return metaFileName
        
import math
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
#
# NOTE: the LUT files must reside in the Django project directory, the directory
# containing manage.py.
#
# Yujie's code is in /att/nobackup/ywang1/ABoVE/WVImg5 and 
# /att/nobackup/ywang1/ABoVE/MAIAC5_WorldView2_Nov-9-2017/.
#-------------------------------------------------------------------------------
class EvhrSrRetriever(EvhrToaRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # NumProcesses must be 1 because SR can only run on evhr103.
        numProcesses = 1
        
        # Initialize the base class.
        super(EvhrSrRetriever, self).__init__(request, logger, numProcesses)

        self.srInputDir = os.path.join(self.request.destination.name, '6-srIn')
        
        if not os.path.exists(self.srInputDir):
            os.mkdir(self.srInputDir)
            
        self.srOutputDir = os.path.join(self.request.destination.name, 
                                        '7-srOut')
        
        if not os.path.exists(self.srOutputDir):
            os.mkdir(self.srOutputDir)
            
        # self.srInputFileName = os.path.join(self.srInputDir, 'srInput.txt')

    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):

        # Build the VRT.
        # outputVrtFileName = os.path.join(self.srOutputDir, 'toa.vrt')
        #
        # cmd = 'gdalbuildvrt -q -overwrite ' + \
        #       outputVrtFileName + ' ' + \
        #       ' '.join(outFiles)
        #
        # sCmd = SystemCommand(cmd, None, self.logger, self.request, True, True)
        #
        # # Build pyramids.
        # cmd = 'gdaladdo ' + outputVrtFileName + ' 2 4 8 16'
        # sCmd = SystemCommand(cmd, None, self.logger, self.request, True, True)
        pass
        
    #---------------------------------------------------------------------------
    # binToTif
    #---------------------------------------------------------------------------
    def binToTif(self, srBin, orthoTif, srTif):

        inNoDataVal = -99999 # Yujie's NoData value
        outNoDataVal = -20000 # output NoData value
        scaleFactor = 10000

        # Get reference information from ortho geoTIFF
        inDS = gdal.Open(orthoTif)
        geoTransform = inDS.GetGeoTransform()
        proj = inDS.GetProjection()
        (nCols, nRows) = (inDS.RasterXSize, inDS.RasterYSize)
        nBands = inDS.RasterCount

        inArr = numpy.fromfile(srBin, numpy.float32) # Read input array from .bin

        # may not need try statement here (and prob needs editing) but:
        # if the file is corrupt/not written all the way, there will be insufficient
        # number of pixels to reshape array to original size. catch it here
        try:
            inArr = numpy.reshape(inArr, (nBands, nRows, nCols))

        except ValueError:
            
            print "Could not reshape {}".format(srBin)
            return None

        # Scale up and replace input NoData val
        outArr = numpy.multiply(inArr, scaleFactor)
        outArr[inArr==inNoDataVal] = outNoDataVal

        inDS = inArr = None

        # Write outArr to output geotif with data type 3 (int16):
        drv = gdal.GetDriverByName("GTiff")
        outDS = drv.Create(srTif, nCols, nRows, nBands, 3, options=["COMPRESS=LZW","BIGTIFF=YES"])
        outDS.SetGeoTransform(geoTransform)
        outDS.SetProjection(proj)

        for b in range(0, nBands):
            outDS.GetRasterBand(b+1).SetNoDataValue(outNoDataVal)
            outDS.GetRasterBand(b+1).WriteArray(outArr[b])

        outDS = outArr = None

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
                                            dgf.fileName + \
                                            ' is being skipped because' + \
                                            ' it is panchromatic.')
                                            
                if dgf.sensor() != 'WV02' and dgf.sensor() != 'WV03':

                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            dgf.fileName + \
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

        # # Aggregate the scenes into strips.
        # toas = {}
        #
        # for scene in scenes:
        #
        #     dgf = DgFile(scene, self.logger)
        #     stripID = dgf.getStripName()
        #     orthoName = os.path.join(self.orthoDir, stripID + '-ortho.tif')
        #
        #     if not orthos.has_key(orthoName):
        #         orthos[orthoName] = []
        #
        #     orthos[orthoName].append(scene)
        #
        # # Aggregate the ToAs into SRs and create the SR input file.
        # constituents = {}
        #
        # if os.path.exists(self.srInputFileName):
        #     os.remove(self.srInputFileName)
        #
        # with open(self.srInputFileName, 'aw+') as f:
        #
        #     for ortho in sorted(orthos):
        #
        #         srBaseName = os.path.basename(ortho).replace('-ortho.tif', '.bin')
        #         srName = os.path.join(self.srOutputDir, srBaseName)
        #         constituents[srName] = orthos[ortho]
        #         f.write(os.path.splitext(os.path.basename(srBaseName))[0]+'\n')

        # Aggregate the scenes into strips, and create the SR input file.
        constituents = {}
        
        for scene in scenes:
            
            dgf = DgFile(scene, self.logger)
            stripID = dgf.getStripName()
            srBaseName = 'MAIAC.' + stripID + '.bin'
            constituentFileName = os.path.join(self.srOutputDir, srBaseName)
            
            if not constituents.has_key(constituentFileName):
                constituents[constituentFileName] = []
                
            constituents[constituentFileName].append(scene)

        return constituents

    #---------------------------------------------------------------------------
    # orthoStrip
    #
    # Input:  a mosaic of all the scenes for each band:  a mosaic containing
    # band1 from every scene, a mosaic containing band2 from every scene ...
    #
    # Output:  an orthorectified version of each of the bands in stripBands
    #---------------------------------------------------------------------------
    def orthoStrip(self, stripBands, orthoFinal):

        # If the output file exists, don't bother running it again.
        if not os.path.exists(orthoFinal):

            if self.logger:
                self.logger.info('Orthorectifing strip {}'.format(orthoFinal))

            # Catch errors, so the constituent continues despite errors.
            try:

                orthoBands = []
                
                for stripBand in stripBands:

                    dgStrip = DgFile(stripBand)
                    orthoBand = self.orthoOne(stripBand, dgStrip)
                    orthoBands.append(orthoBand)

                self.mergeBands(orthoBands, orthoFinal)
      
                shutil.copy(dgStrip.xmlFileName, 
                            orthoFinal.replace('.tif', '.xml'))    

            except:
                pass

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):
        
        stripName = DgFile(fileList[0], self.logger).getStripName()
        stripBandList = self.scenesToStrip(stripName, fileList)

        baseName ='.'.join(os.path.basename(constituentFileName).split('.')[1:])
        baseName.replace('.bin', '.tif')
        orthoName = os.path.join(self.srInputDir, baseName)
        
        self.orthoStrip(stripBandList, orthoName)

        #---
        # Run the SR code.  Yujie's code does not properly report errors, so
        # check for expected output after each step.
        #---
        metaFileName, binFileName = self.writeMetaAndBin(stripName, orthoName)

        if not os.path.exists(metaFileName) or not os.path.exists(binFileName):
            raise RuntimeError('WV02Cal failed for ' + constituentFileName)

        wv2File = self.writeWv2(stripName)

        if not os.path.exists(wv2File):
            raise RuntimeError('WVimg5 failed for ' + constituentFileName)

        srFile = self.runMaiac(stripName)
            
        if not os.path.exists(srFile):
            raise RuntimeError('MAIAC_WV2_5 failed for ' + constituentFileName)

        #---
        # Convert SR binary to geoTIFF output
        # srTif = my best guess on the output name; 'srBin' needs to be the 
        # binary output of Yujie's code, and I assume orthoName is the ortho 
        # tif, which is what we need to use as georeference for output SR tif
        #---
        srTif = os.path.join(self.srOutputDir, '{}_SR.tif'.format(stripName))
        self.binToTif(srFile, orthoName, srTif) 
                    
        return constituentFileName
        
    #---------------------------------------------------------------------------
    # runMaiac
    #
    # Yujie's code is at
    # /att/nobackup/ywang1/ABoVE/MAIAC5_WorldView2_Nov-9-2017/MAIAC_WV2_5.
    #---------------------------------------------------------------------------
    def runMaiac(self, stripName):
        
        srFile = os.path.join(self.srOutputDir, 'MAIAC.' + stripName + '.bin')

        if not os.path.exists(srFile):
            
            srExe = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'SurfaceReflectance/MAIAC_WV2_5')
        
            cmd = srExe + ' ' + \
                  stripName + ' ' + \
                  self.srInputDir + ' ' + \
                  self.srOutputDir
            
            # cmd = "pdsh -w {} '{}'".format('evhr103', cmd)

            sCmd = SystemCommand(cmd, None, self.logger, self.request, True,
                                 False)
            
            if sCmd.returnCode != 0:

                if self.logger:
                    
                    self.logger.error(cmd)
                    self.logger.error(sCmd.msg)

        return srFile      

    #---------------------------------------------------------------------------
    # scenesToStrip()
    #---------------------------------------------------------------------------
    def scenesToStrip(self, stripName, stripScenes):

        if self.logger:
            self.logger.info('Extracting bands and mosaicking to strips for' + \
                    ' {} ({} input scenes)'.format(stripName, len(stripScenes)))

        bands = ['BAND_C', 'BAND_B', 'BAND_G', 'BAND_R', 'BAND_N']

        return self.scenesToStripFromBandList(stripName, stripScenes, bands)
                  
    #---------------------------------------------------------------------------
    # writeMetaAndBin
    #---------------------------------------------------------------------------
    def writeMetaAndBin(self, stripName, orthoName):

        metaFileName = os.path.join(self.srInputDir, stripName + '.meta')
        binFileName = os.path.join(self.srInputDir, stripName + '.bin')

        if not os.path.exists(metaFileName) or not os.path.exists(binFileName):

            if self.logger:
                
                self.logger.info('Extracting metadata and bin from ' + \
                                 str(stripName))

            wv02CalExe = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      'SurfaceReflectance/WV02Cal.py')

            #---
            # WV02Cal.py wants to process all IDs in srInput.txt, while we need
            # it to only process this one.  To work around that, create a
            # temporary file containing only this ID.
            #---
            oneID = os.path.basename(stripName)
            tempInput = tempfile.mkstemp()[1]

            with open(tempInput, 'w') as f:
                f.write(os.path.splitext(os.path.basename(stripName))[0]+'\n')
              
            #---
            # Temporarily link the ortho to the SR input directory because 
            # that is where WV02Cal.py expects to find it.
            #---
            srInOrtho = os.path.join(self.srInputDir, orthoName)
            srInOrthoXml = srInOrtho.replace('tif', 'xml')
            os.symlink(orthoName, srInOrtho)
            os.symlink(orthoName, srInOrthoXml)
                
            # Build and run the command.  
            cmd = wv02CalExe + ' ' + tempInput + ' ' + self.srInputDir
                  
            sCmd = SystemCommand(cmd, None, self.logger, self.request, True,
                                 self.maxProcesses != 1)
                                 
            if sCmd.returnCode != 0:

                if self.logger:
                    
                    self.logger.error(cmd)
                    self.logger.error(sCmd.msg)
                    
            os.remove(srInOrtho)
            os.remove(srInOrthoXml)

        return metaFileName, binFileName

    #---------------------------------------------------------------------------
    # writeWv2
    #
    # WVimg5 /att/pubrepo/MAIAC-ancillary/results/runtime_Canada.txt file_Barrow
    # Barrow
    # File_Barrow = 6-sr/srInput.txt
    #
    # Yujie's code is at /att/nobackup/ywang1/ABoVE/WVImg5/WVimg5.
    #---------------------------------------------------------------------------
    def writeWv2(self, stripName):

        wv2File = os.path.join(self.srInputDir, stripName + '.wv2')

        if not os.path.exists(wv2File):

            if self.logger:
                self.logger.info('Creating wv2 file from ' + str(stripName))

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
            oneID = os.path.basename(stripName)
            tempInput = tempfile.mkstemp()[1]

            with open(tempInput, 'w') as f:
                f.write(os.path.splitext(os.path.basename(stripName))[0]+'\n')
                
            # WVimg5   MAIACruntimefile  imagelistfile   TOApath
            cmd = wvImgExe + ' ' + \
                  maiacFile + ' ' + \
                  tempInput + ' ' + \
                  self.srInputDir

            # cmd = "pdsh -w {} '{}'".format('evhr103', cmd)
            
            sCmd = SystemCommand(cmd, None, self.logger, self.request, True,
                                 False)

            if sCmd.returnCode != 0:

                if self.logger:
                    
                    self.logger.error(cmd)
                    self.logger.error(sCmd.msg)

            # os.remove(tempInput)
            
        return wv2File



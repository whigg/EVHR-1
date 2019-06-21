
import glob
import json
import math
import os
import random
import shutil
import traceback

import numpy

from osgeo import gdal
from osgeo.osr import SpatialReference

from django.conf import settings

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrHelper import EvhrHelper
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.management.FootprintsScene import FootprintsScene
from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.management.TilerHalfDegree import TilerHalfDegree
from EvhrEngine.management.UTM import UTM
from EvhrEngine.management.commands.TOA import TOA
from EvhrEngine.models import EvhrError
from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# class EvhrToaRetriever
#
# To build the SRTM index file:
# gdaltindex -t_srs "EPSG:4326" -src_srs_name SRS srtm.shp /att/pubrepo/DEM/SRTM/1-ArcSec/*.hgt
#
# To build the ASTERDEM index file:
# gdaltindex -t_srs "EPSG:4326" -src_srs_name SRS astergdem.shp /att/pubrepo/DEM/ASTERGDEM/v2/*dem.tif
#
# https://github.com/NeoGeographyToolkit/StereoPipeline
#
# ./manage.py processEvhrRequest --name testCrystal --epName "EVHR Mosaic" --ulx -113.39250146 --uly 43.35041085 --lrx -112.80953835 --lry 42.93059617 --epsg 4326 --outEpsg 102039 -n 1
#
# ./manage.py processEvhrRequest --name testFairbanks --epName "EVHR Mosaic" --ulx -148 --uly 65 --lrx -147.5 --lry 64.5 --epsg 4326 --outEpsg 4326 -n 1
#-------------------------------------------------------------------------------
class EvhrToaRetriever(GeoRetriever):

    MAXIMUM_SCENES = 100
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        self.evhrHelper = EvhrHelper(logger)

        # The output SRS must be UTM, regardless of what the user chooses.

        # Get UTM proj4 string and set outSRS        
        self.proj4 = UTM.proj4(request.ulx,
                               request.uly,
                               request.lrx,
                               request.lry,
                               request.srs)

        sr = SpatialReference()
        sr.ImportFromProj4(self.proj4)
        request.outSRS = sr.ExportToWkt()
        request.save(update_fields = ['outSRS'])

        # Initialize the base class.
        super(EvhrMosaicRetriever, self).__init__(request, logger, numProcesses)

        #---
        # GeoRetriever should always choose EPSG:4326 as the retrieval SRS
        # because that is all that FOOTPRINTS knows.  Verify that.
        #---
        if not self.retrievalSRS.IsSame(GeoRetriever.GEOG_4326):
            raise RuntimeError('Retrieval SRS must be geographic.')

        # Ensure the ortho and toa directories exist.
        self.bandDir  = os.path.join(self.request.destination.name, '1-bands')
        self.stripDir = os.path.join(self.request.destination.name, '2-strips')
        self.demDir   = os.path.join(self.request.destination.name, '3-dems')
        self.orthoDir = os.path.join(self.request.destination.name, '4-orthos')
        self.toaDir   = os.path.join(self.request.destination.name, '5-toas')

        for d in [self.bandDir, self.stripDir, self.demDir, self.orthoDir, 
                  self.toaDir]:
            if not os.path.exists(d): os.mkdir(d)
            
    #---------------------------------------------------------------------------
    # createDemForOrthos
    #
    # retrieveOne -> processScene -> orthoOne -> createDemForOrthos
    #---------------------------------------------------------------------------
    def createDemForOrthos(self, ulx, uly, lrx, lry, srs):

        if self.logger:
            self.logger.info('Creating DEM for orthorectification.')

        # If there is already a clipped DEM for this bounding box, use it.
        demName = 'dem-'                          + \
                  str(ulx) + '-'                  + \
                  str(uly) + '-'                  + \
                  str(lrx) + '-'                  + \
                  str(lry) + '-'                  + \
                  str(srs.GetAuthorityCode(None)) + \
                  '-adj.tif'

        demName = os.path.join(self.demDir, demName)

        if os.path.exists(demName):
            return demName

        # Expand the bounding box before clipping the DEM.
        xUlx, xUly, xLrx, xLry = self.expandByPercentage(ulx, uly, lrx, lry,srs)

        # Mosaic SRTM tiles to cover this AoI.
        self.mosaicAndClipDemTiles(demName, xUlx, xUly, xLrx, xLry, srs)

        return demName

    #---------------------------------------------------------------------------
    # deleteFiles
    #---------------------------------------------------------------------------
    def deleteFiles(self, deleteDir):
        
        # Remove *.tif and their .xmls
        files = glob.glob(os.path.join(deleteDir, '*.tif'))
        files.extend(glob.glob(os.path.join(deleteDir, '*.xml')))

        for f in files:
            os.remove(f)
            
    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # getScenes
    #---------------------------------------------------------------------------
    def getScenes(self, request, ulx, uly, lrx, lry, srs):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = request)
        sceneFiles = []

        if evhrScenes:
            for evhrScene in evhrScenes:
                scenePath = evhrScene.sceneFile.name
                if not os.path.isfile(scenePath):
                    evhrScene.delete()
                    if self.logger:
                        msg = '{} does not exist in the filesystem'.format(scenePath)
                        self.logger.warning(msg)
                else:
                    sceneFiles.append(scenePath)            
        
        else:
            
            fpScenes = None
            fpq = FootprintsQuery(logger=self.logger)
            fpq.addAoI(ulx, uly, lrx, lry, srs)
            fpq.setMinimumOverlapInDegrees()

            maxScenes = EvhrMosaicRetriever.MAXIMUM_SCENES
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                maxScenes = min(maxScenes, settings.MAXIMUM_SCENES)
                
            fpq.setMaximumScenes(maxScenes)
            fpScenes = fpq.getScenes()
            
            for scene in fpScenes:

                evhrScene = EvhrScene()
                evhrScene.request = request
                evhrScene.sceneFile = scene.fileName()
                evhrScene.save()

            sceneFiles = [fps.fileName() for fps in fpScenes]
                
        sceneFiles.sort()
        
        return sceneFiles
        
    #---------------------------------------------------------------------------
    # listConstituents
    #
    # Constituent:  ToA strip
    # Files:  scenes
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
            self.logger.error('There were no level 1B scenes.')

        # Aggregate the scenes into strips.
        constituents = {}
        
        for scene in scenes:
            
            dgf = DgFile(scene, self.logger)
            stripID = dgf.getStripName()
            constituentFileName = os.path.join(self.toaDir, stripID + '-toa.tif')
            
            if not constituents.has_key(constituentFileName):
                constituents[constituentFileName] = []
                
            constituents[constituentFileName].append(scene)
            
        return constituents
    
    #---------------------------------------------------------------------------
    # mergeBands
    #---------------------------------------------------------------------------
    def mergeBands(self, bandFiles, outFileName):

        if self.logger:
            self.logger.info('Merging bands into ' + str(outFileName))

        cmd = 'gdal_merge.py -co COMPRESS=LZW -co BIGTIFF=YES -ot Int16 \
                -separate -n {} -a_nodata {} -o {} {}'. \
                format(settings.NO_DATA_VALUE, \
                       settings.NO_DATA_VALUE, 
                       outFileName, \
                       ' '.join(bandFiles))

        sCmd = SystemCommand(cmd, outFileName, self.logger, self.request, 
                             True, self.maxProcesses != 1)
                             
        for bandFile in bandFiles: os.remove(bandFile)

    #---------------------------------------------------------------------------
    # mosaicAndClipDemTiles
    #
    # retrieveOne -> processScene -> orthoOne -> createDemForOrthos
    # -> mosaicAndClipDemTiles
    #
    # To build the SRTM index file:
    # gdaltindex -t_srs "EPSG:4326" -src_srs_name SRS srtm.shp /att/pubrepo/DEM/SRTM/1-ArcSec/*.hgt
    #
    # To build the ASTERGDEM index file:
    # gdaltindex -t_srs "EPSG:4326" -src_srs_name SRS astergdem.shp /att/pubrepo/DEM/ASTERGDEM/v2/*dem.tif
    #---------------------------------------------------------------------------
    def mosaicAndClipDemTiles(self, outDemName, ulx, uly, lrx, lry, srs):

        if self.logger:
            self.logger.info('Creating DEM ' + str(outDemName))

        outDemNameTemp = outDemName.replace('.tif', '-temp.tif')

        #---
        # SRTM was collected between -54 and 60 degrees of latitude.  Use
        # ASTERGDEM where SRTM is unavailable.
        #---
        SHP_INDEX = None
        
        if uly >= -54.0 and uly <= 60.0 and lry >= -54.0 and lry <= 60.0:

            SHP_INDEX = \
                os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'SRTM/srtm.shp')
                             
        else:

            SHP_INDEX = \
                os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'ASTERGDEM/astergdem.shp')
                             
        # Get the SRTM tile Shapefile and intersect it with the AoI.
        features = self.evhrHelper.clipShp(SHP_INDEX, 
                                           ulx, 
                                           uly, 
                                           lrx, 
                                           lry, 
                                           srs, 
                                           self.request)
        
        if not features or len(features) == 0:
            
            msg = 'Clipping rectangle to SRTM did not return any features. ' + \
                  'Corners: (' + str(ulx) + ', ' + str(uly) + '), ('         + \
                  str(lrx) + ', ' + str(lry) + ')'
                
            raise RuntimeError(msg)

        # Get the list of tiles.
        tiles = []

        for feature in features:

            tileFile = str(feature. \
                           getElementsByTagName('ogr:location')[0]. \
                           firstChild. \
                           data)

            tiles.append(tileFile)

        # Mosaic the tiles.
        cmd = 'gdal_merge.py'         + \
              ' -o ' + outDemNameTemp + \
              ' -ul_lr'               + \
              ' ' + str(ulx)          + \
              ' ' + str(uly)          + \
              ' ' + str(lrx)          + \
              ' ' + str(lry)          + \
              ' ' + ' '.join(tiles)

        sCmd = SystemCommand(cmd, outDemNameTemp, self.logger, self.request, 
                             True, True)

        # Run mosaicked DEM through geoid correction
        cmd = '/opt/StereoPipeline/bin/dem_geoid '  + \
              outDemNameTemp + ' --geoid EGM96 -o ' + \
              outDemName.strip('-adj.tif')          + \
              ' --reverse-adjustment'

        sCmd = SystemCommand(cmd, outDemName, self.logger, self.request, True,
                             self.maxProcesses != 1)
        
        for log in glob.glob(os.path.join(self.demDir, '*log*.txt')):
            os.remove(log) # remove dem_geoid log file
    
    #---------------------------------------------------------------------------
    # orthoOne
    #
    # retrieveOne -> processScene -> orthoOne
    #---------------------------------------------------------------------------
    def orthoOne(self, bandFile, origDgFile):

        if self.logger:
            self.logger.info('Orthorectifying ' + str(bandFile))

        baseName  = os.path.splitext(os.path.basename(bandFile))[0]
        orthoFile = os.path.join(self.orthoDir, baseName + '-ortho.tif')

        if not os.path.exists(orthoFile):

            try:
                clippedDEM = self.createDemForOrthos(origDgFile.ulx,
                                                     origDgFile.uly,
                                                     origDgFile.lrx,
                                                     origDgFile.lry,
                                                     origDgFile.srs)

            except RuntimeError, e:

                msg = str(e) + ' Band file: ' + str(bandFile) + \
                      ' DgFile: ' + str(origDgFile.fileName)
                      
                raise RuntimeError(msg)

            # Orthorectify.
            orthoFileTemp = orthoFile.replace('.tif', '-temp.tif')
            bandName = DgFile(bandFile).getBandName()
            outRes = 2
            if origDgFile.isPanchromatic(): outRes = 1            

            cmd = '/opt/StereoPipeline/bin/mapproject --nodata-value 0' + \
                  ' --threads=2 -t rpc'                                 + \
                  ' --mpp={}'.format(outRes)                            + \
                  ' --t_srs "{}"'.format(self.proj4)                    + \
                  ' ' + clippedDEM                                      + \
                  ' ' + bandFile                                        + \
                  ' ' + origDgFile.xmlFileName                          + \
                  ' ' + orthoFileTemp

            sCmd = SystemCommand(cmd, 
                                 orthoFileTemp, 
                                 self.logger, 
                                 self.request, 
                                 True,
                                 self.maxProcesses != 1)

            # Convert NoData to settings value, set output type to Int16
            cmd = '/opt/StereoPipeline/bin/image_calc -c "var_0" {} -d int16   \
                        --output-nodata-value {} -o {}'.format(orthoFileTemp, 
                                            settings.NO_DATA_VALUE, orthoFile)

            sCmd = SystemCommand(cmd, orthoFile, self.logger, self.request,
                                 True, True)

            # Copy xml to accompany ortho file (needed for TOA)
            shutil.copy(origDgFile.xmlFileName,
                        orthoFile.replace('.tif', '.xml'))

            DgFile(orthoFile).setBandName(bandName)

        return orthoFile

    #---------------------------------------------------------------------------
    # processStrip()
    #
    # Takes a strip and a list of band mosaics (from dg_mosaic) and processes
    # The original NITF, extracted band strips and orthorectified strips remain
    # unclipped.  Only the final orthorectified image is clipped in mergeBands
    # or compress. 
    #---------------------------------------------------------------------------
    def processStrip(self, stripBands, toaFinal):

        if self.logger:
            self.logger.info('Processing strip {}'.format(toaFinal))

        # If the output file exists, don't bother running it again.
        if not os.path.exists(toaFinal):

            # Catch errors, so the constituent continues despite errors.
            try:

                toaBands = []
                
                for stripBand in stripBands:

                    dgStrip = DgFile(stripBand)
                    orthoBand = self.orthoOne(stripBand, dgStrip)
                    #orthoBands.append(orthoBand) # yujie

                    toaBands.append(TOA.run(orthoBand,
                                            self.toaDir,
                                            stripBand, # instead of inputNitf
                                            self.logger))

                self.mergeBands(toaBands, toaFinal)
      
                shutil.copy(DgFile(orthoBand).xmlFileName, 
                            toaFinal.replace('.tif', '.xml'))    

            except:
                pass

    #---------------------------------------------------------------------------
    # scenesToStrips()
    #
    # Takes a list of scenes belonging to a strip and mosaics the scenes
    # together with dg_mosaic
    #---------------------------------------------------------------------------
    def scenesToStrip(self, stripName, stripScenes):

        if self.logger:
            self.logger.info('Extracting bands and mosaicking to strips for' + \
                    ' {} ({} input scenes)'.format(stripName, len(stripScenes)))

        stripBandList = [] # Length of list = number of bands
            
        bands = ['BAND_P'] if 'P1BS' in stripName else \
                ['BAND_B', 'BAND_G', 'BAND_R', 'BAND_N']
	
        #bands =	DgFile(stripScenes[0]).bandNameList # yujie. might use later

        for bandName in bands:
           
            bandScenes = [DgFile(scene).getBand(self.bandDir, bandName) \
                         for scene in stripScenes]
 
            bandScenesStr = ' '.join(bandScenes)

            stripBandFile = os.path.join(self.stripDir, 
                                         '{}_{}.r100.tif'.format(stripName, 
                                                                 bandName))

            cmd = '/opt/StereoPipeline/bin/dg_mosaic --output-nodata-value 0' +\
                  ' --ignore-inconsistencies --output-prefix {} {}'. \
                  format(stripBandFile.replace('.r100.tif', ''), bandScenesStr)

            sCmd = SystemCommand(cmd, stripBandFile, self.logger, self.request,
                                 True, self.maxProcesses != 1)
            
            DgFile(stripBandFile).setBandName(bandName)                          
            stripBandList.append(stripBandFile) 

        # Return the list of band strips.
        return stripBandList

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        stripName = DgFile(fileList[0], self.logger).getStripName()
        stripBandList = self.scenesToStrip(stripName, fileList)
        self.processStrip(stripBandList, constituentFileName)
        # self.deleteFiles(self.stripDir)
        # self.deleteFiles(self.demDir)
        # self.deleteFiles(self.orthoDir)
        
        return constituentFileName


import glob
import json
import math
import os
import shutil
import traceback

import numpy

from osgeo import gdal
from osgeo.osr import CoordinateTransformation
from osgeo.osr import SpatialReference

from django.conf import settings

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrHelper import EvhrHelper
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.management.FootprintsScene import FootprintsScene
from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.management.TilerHalfDegree import TilerHalfDegree
from EvhrEngine.management.commands.TOA import TOA
from EvhrEngine.models import EvhrError
from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# class EvhrMosaicRetriever
# maggieRoger
# SRSs
# - requestSRS: as usual, whatever the user chooses
# - outSRS: this must be UTM, regardless of what the user chooses
# - supportedSRSs: the native SRS of FOOTPRINTS: EPSG:4326
# - retrievalSRS: GeoRetriever.getRetrievalSRS() determines this, must be 4326
# - 1/2-degree Tiles: EPSG:4326
# - DEM: EPSG:4326, transformed to UTM for use with orthorectification
#
# Directory Structure
# - outDir directory
#     - tileTemplates
#     - bandFiles directory
#     - orthos directory
#     - clippedDEM.tif
#     - final-output-ortho.tif
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
class EvhrMosaicRetriever(GeoRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        self.evhrHelper = EvhrHelper(logger)

        # The output SRS must be UTM, regardless of what the user chooses.
        request.outSRS = self.evhrHelper.getUtmSrs(request)
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
        self.tileDir  = os.path.join(self.request.destination.name, '1-tiles')
        self.bandDir  = os.path.join(self.request.destination.name, '2-bands')
        self.stripDir = os.path.join(self.request.destination.name, '3-strips')
        self.demDir   = os.path.join(self.request.destination.name, '4-dems')
        self.orthoDir = os.path.join(self.request.destination.name, '5-orthos')
        self.toaDir   = os.path.join(self.request.destination.name, '6-toas')

        for d in [self.tileDir, self.bandDir, self.stripDir, self.demDir, \
                                                   self.orthoDir, self.toaDir]:

            if not os.path.exists(d): os.mkdir(d)
            
    #---------------------------------------------------------------------------
    # compress
    #
    # retrieveOne -> processScene -> compress
    #---------------------------------------------------------------------------
    # def compress(self, orthoBand):
    #
    #     if self.logger:
    #         self.logger.info('Compressing ' + orthoBand)
    #
    #     # To compress in place, copy the input file to a temporary file.
    #     tempBandFile = tempfile.mkstemp()[1]
    #     shutil.move(orthoBand, tempBandFile)
    #
    #     cmd = 'gdal_translate -q -ot Int16 -co COMPRESS=LZW' + \
    #           ' -co BIGTIFF=YES'                             + \
    #           ' ' + tempBandFile                             + \
    #           ' ' + orthoBand
    #
    #     sCmd = SystemCommand(cmd, orthoBand, self.logger, self.request, True)

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
    # createEmptyTile
    #---------------------------------------------------------------------------
    def createEmptyTile(self, tileGeometry, srs, tileNum):

        ulx = tileGeometry.GetGeometryRef(0).GetPoint(0)[0]
        uly = tileGeometry.GetGeometryRef(0).GetPoint(0)[1]
        lrx = tileGeometry.GetGeometryRef(0).GetPoint(2)[0]
        lry = tileGeometry.GetGeometryRef(0).GetPoint(2)[1]

        tileName = os.path.join(self.tileDir, 'tile' + str(tileNum) + '.tif')

        height = 1  # Choose a nominal height and width.  All we really
        width  = 1  # need is the extent and file name of this tile tif.
        driver = gdal.GetDriverByName('GTiff')
        ds     = driver.Create(tileName, width, height)

        if not ds:
            raise RuntimeError('Unable to open ' + str(tileName))

        ds.SetProjection(srs.ExportToWkt())

        rotation = 0
        xRes = lrx - ulx
        yRes = (uly - lry) * -1.0

        ds.SetGeoTransform([ulx, xRes, rotation, uly, rotation, yRes])
        raster = numpy.zeros((height, width), dtype = numpy.uint8)

        ds.GetRasterBand(1).WriteArray(raster)
        ds = None

        return tileName

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
    # extractBands
    #
    # retrieveOne -> processScene -> extractBands (multispectral only)
    #---------------------------------------------------------------------------
    def extractBands(self, nitfFile):

        if self.logger:
            self.logger.info('Extracting bands from ' + str(nitfFile.fileName))

        # Get the bands to use.
        bands = ['BAND_P'] if nitfFile.isPanchromatic() else \
                ['BAND_B', 'BAND_G', 'BAND_R', 'BAND_N']

        # Extract the bands.
        bandFiles = []

        for band in bands:

            bandFileName = nitfFile.getBand(self.bandDir, band)

            if bandFileName:
                
                bandFiles.append(bandFileName)

            else:
                
                self.logger.error('Unable to extract band '  + \
                                  str(band)                  + \
                                  ' from '                   + \
                                  nitfFile.fileName)
                
        return bandFiles

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
        features = None
        fpScenes = None
        fpq = FootprintsQuery(logger=self.logger)
        fpq.addAoI(ulx, uly, lrx, lry, srs)
        
        if evhrScenes:
            
            fpq.addEvhrScenes(evhrScenes)
            fpScenes = fpq.getScenes()
            self.evhrHelper.checkForMissingScenes(fpScenes, evhrScenes)
        
        else:
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                fpq.setMaximumScenes(settings.MAXIMUM_SCENES)

            fpq.setPairsOnly()
            fpScenes = fpq.getScenes()
            
            for scene in fpScenes:

                evhrScene = EvhrScene()
                evhrScene.request = request
                evhrScene.sceneFile = scene.fileName()
                evhrScene.save()
                
        return [fps.fileName() for fps in fpScenes]

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query for scenes.
        scenes = self.getScenes(self.request,
                                self.retrievalUlx,
                                self.retrievalUly,
                                self.retrievalLrx,
                                self.retrievalLry,
                                self.retrievalSRS)
            
        #---
        # Create a polygon for each scene.  They are used to test for
        # intersection below.
        #---
        sceneGeoms = {}
        
        for scene in scenes:
        
            try:
                dg = DgFile(scene, self.logger)
                
            except Exception, e:
                
                err             = EvhrError()
                err.request     = self.request
                err.inputFile   = scene
                err.errorOutput = traceback.format_exc()
                err.save()
                
                continue
                
            geom = self.bBoxToPolygon(dg.ulx, dg.uly, dg.lrx, dg.lry,dg.srs)
            sceneGeoms[scene] = geom
                
        # Define the tiles.
        tiler = TilerHalfDegree(self.retrievalUlx,
                                self.retrievalUly,
                                self.retrievalLrx,
                                self.retrievalLry,
                                self.retrievalSRS, 
                                self.logger)

        grid  = tiler.defineGrid()
        tiles = tiler.gridToPolygons(grid)
        
        # Tiles + scenes = constituents.
        constituents = {}
        tileNum = 0
        
        for tile in tiles:
            
            tileNum += 1
            tileFile = self.createEmptyTile(tile, self.retrievalSRS, tileNum)
            constituents[tileFile] = []
            
            for scene in scenes:
                
                # Scenes could be rejected due to missing information.
                if not scene in sceneGeoms:
                    continue
                    
                if not tile.GetSpatialReference(). \
                       IsSame(sceneGeoms[scene].GetSpatialReference()):
                       
                    raise RuntimeError('Tile and scene must be in the '
                                       'same SRS.')
                                       
                if tile.Intersects(sceneGeoms[scene]):
                    
                    constituents[tileFile].append(scene)
                    
                    if hasattr(settings, 'MAX_SCENES_PER_TILE') and \
                       len(constituents[tileFile]) >= \
                           settings.MAX_SCENES_PER_TILE:
                        
                           break
                    
            # Ensure the tile has scenes covering it.
            if not constituents[tileFile]:
                
                raise RuntimeError('There were no scenes covering tile ' + \
                                   str(tile))
             
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

        sCmd = SystemCommand(cmd, outFileName, self.logger, self.request, True)
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
                             True)
        
        for log in glob.glob(os.path.join(self.demDir, '*log*.txt')): \
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

            # to project, add: --t_srs "+proj=utm +zone=? +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
            cmd = '/opt/StereoPipeline/bin/mapproject --nodata-value 0' + \
                  ' --threads=2 -t rpc --mpp=2'                         + \
                  ' ' + clippedDEM                                      + \
                  ' ' + bandFile                                        + \
                  ' ' + origDgFile.xmlFileName                          + \
                  ' ' + orthoFileTemp

            sCmd = SystemCommand(cmd, 
                                 orthoFileTemp, 
                                 self.logger, 
                                 self.request, 
                                 True,
                                 True)

            # Convert NoData to settings value, set output type to Int16
            cmd = '/opt/StereoPipeline/bin/image_calc -c "var_0" {} -d int16   \
                        --output-nodata-value {} -o {}'.format(orthoFileTemp,  \
                                            settings.NO_DATA_VALUE, orthoFile)

            sCmd = SystemCommand(cmd, orthoFile, self.logger, self.request,
                                 True, True)

            # Copy xml to accompany ortho file (needed for TOA)
            shutil.copy(origDgFile.xmlFileName, \
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
    def processStrip(self, stripName, stripBands):

        if self.logger:
            self.logger.info('Processing strip {}'.format(stripName))

        # Get the output name to see if it exists.
        bname = '{}-ortho.tif'.format(stripName)
        
        toaFinal = os.path.join(self.toaDir, 
                                'EVHR_{}'.format(bname.replace \
                                                    ('-ortho.tif', '-TOA.tif')))

        # If the output file exists, don't bother running it again.
        if not os.path.exists(toaFinal):

            # Catch errors, so the constituent continues despite errors.
            try:

                toaBands = []
                #orthoBands = [] # temp-yujie
                
                for stripBand in stripBands:

                    dgStrip = DgFile(stripBand)
                    orthoBand = self.orthoOne(stripBand, dgStrip)
                    #orthoBands.append(orthoBand) # yujie

                    toaBands.append(TOA.run(orthoBand,
                                            self.toaDir,
                                            stripBand, # instead of inputNitf
                                            self.logger))

                self.mergeBands(toaBands, toaFinal)
      
                shutil.copy(DgFile(orthoBand).xmlFileName, \
                                              toaFinal.replace('.tif', '.xml'))    
                #self.mergeBands(orthoBands, os.path.join(self.toaDir, bname)) # yujie


            except:
                pass

        return toaFinal


    #---------------------------------------------------------------------------
    # scenesToStrips()

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
	
        bands =	DgFile(stripScenes[0]).bandNameList # yujie. might use later

        for bandName in bands:
           
            bandScenes = [DgFile(scene).getBand(self.bandDir, bandName) \
                                                       for scene in stripScenes]
 
            bandScenesStr = ' '.join(bandScenes)

            stripBandFile = os.path.join(self.stripDir, '{}_{}.r100.tif'\
                                                  .format(stripName, bandName))

            cmd = '/opt/StereoPipeline/bin/dg_mosaic --output-nodata-value 0' +\
                             ' --ignore-inconsistencies --output-prefix {} {}' \
                               .format(stripBandFile.replace('.r100.tif', ''), \
                                                                  bandScenesStr)

            sCmd = SystemCommand(cmd, stripBandFile, self.logger, self.request,
                                 True, True)
                
            DgFile(stripBandFile).setBandName(bandName)
                          
            stripBandList.append(stripBandFile) 

        # Return the list of band strips
        return stripBandList

    #---------------------------------------------------------------------------
    # retrieveOne
    #
    # This receives a 1/2 degree tile file and the list of NITF files that
    # intersect it.  The NITF files have not been clipped.
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        #---
        # Mosaic scenes into strips, orthorectify the full strip, clip to the 
        # half-degree-square tile, and covert to Geotiff.
        #---

        completedStrips = []
        
        # Get list of unique strip names for scenes in AOI
        stripNameList = list(set([DgFile(scene).getStripName() \
                                                        for scene in fileList]))

        # For each strip, extract bands --> mosaic, ortho, toa each band
        for stripName in stripNameList:

            stripScenes = [scene for scene in fileList \
                            if DgFile(scene).getStripName() == stripName]

            stripBandList = self.scenesToStrip(stripName, stripScenes)
            completedStrips.append(self.processStrip(stripName, stripBandList))
        
        self.deleteFiles(self.bandDir)
        self.deleteFiles(self.stripDir)
        self.deleteFiles(self.demDir)
        self.deleteFiles(self.orthoDir)
 
        # Mosaic the scenes into a single file.
        
        # Transform the mosaic into the output SRS.
        
        return completedStrips[0]



import glob
import json
import math
import os
import shutil
import tempfile
import traceback
from xml.dom import minidom

import numpy

from osgeo import gdal
from osgeo.osr import CoordinateTransformation
from osgeo.osr import SpatialReference

from django.conf import settings

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.management.TilerHalfDegree import TilerHalfDegree
from EvhrEngine.management.commands.TOA import TOA
from EvhrEngine.models import EvhrError
from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# class EvhrMosaicRetriever
#
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

    FOOTPRINTS_FILE = '/att/pubrepo/NGA/INDEX/Footprints/current/10_05_2017/geodatabase/nga_inventory_10_05_2017.gdb'
    # FOOTPRINTS_FILE = '/att/nobackup/dslaybac/PublicMD/DG_28Nov2017.gdb'

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # EVHR gets its own subdirectory because it can have multiple files.
        # if os.path.basename(request.destination.name) != 'EVHR':
        #
        #     request.destination.name = \
        #         os.path.join(request.destination.name,'EVHR')
        #
        #     request.save(update_fields = ['destination'])
        #
        # if not os.path.exists(request.destination.name):
        #     os.mkdir(request.destination.name)

        # The output SRS must be UTM, regardless of what the user chooses.
        request.outSRS = self.getUtmSrs(request)
        request.save(update_fields = ['outSRS'])

        # Initialize the base class.
        super(EvhrMosaicRetriever, self).__init__(request, logger, numProcesses)

        #---
        # GeoRetriever should always choose EPSG:4326 as the retrieval SRS
        # because that is all that FOOTPRINTS knows.  Verify that.
        #---
        if not self.retrievalSRS.IsSame(GeoRetriever.GEOG_4326):
            raise RuntimeError('Retrieval SRS must be geographic.')

        self.runSensors = ['WV01', 'WV02', 'WV03']

        # Ensure the orthos and toa directories exists.
        self.tileDir  = os.path.join(self.request.destination.name, '1-tiles')
        self.bandDir  = os.path.join(self.request.destination.name, '2-bands')
        self.demDir   = os.path.join(self.request.destination.name, '3-dems')
        self.orthoDir = os.path.join(self.request.destination.name, '4-orthos')
        self.toaDir   = os.path.join(self.request.destination.name, '5-toas')

        if not os.path.exists(self.tileDir):
            os.mkdir(self.tileDir)

        if not os.path.exists(self.bandDir):
            os.mkdir(self.bandDir)

        if not os.path.exists(self.demDir):
            os.mkdir(self.demDir)

        if not os.path.exists(self.orthoDir):
            os.mkdir(self.orthoDir)

        if not os.path.exists(self.toaDir):
            os.mkdir(self.toaDir)

    #---------------------------------------------------------------------------
    # clipShp
    #
    # listConstituents -> queryFootprints -> clipShp
    #
    # retrieveOne -> processScene -> orthoOne -> createDemForOrthos
    # -> mosaicAndClipDemTiles -> clipShp
    #---------------------------------------------------------------------------
    def clipShp(self, shpFile, ulx, uly, lrx, lry, srs, extraQueryParams = ''):

        if self.logger:
            self.logger.info('Clipping Shapefile.')

        # Create a temporary file for the clip output.
        tempClipFile = tempfile.mkstemp()[1]
        
        #---
        # To filter scenes that only overlap the AoI slightly, decrease both
        # corners of the query AoI.
        #---
        MIN_OVERLAP_IN_DEGREES = 0.2
        ulx = float(ulx) + MIN_OVERLAP_IN_DEGREES
        uly = float(uly) - MIN_OVERLAP_IN_DEGREES
        lrx = float(lrx) - MIN_OVERLAP_IN_DEGREES
        lry = float(lry) + MIN_OVERLAP_IN_DEGREES

        # Clip.  The debug option somehow prevents an occasional seg. fault!
        cmd = 'ogr2ogr'                        + \
              ' -f "GML"'                      + \
              ' -spat'                         + \
              ' ' + str(ulx)                   + \
              ' ' + str(lry)                   + \
              ' ' + str(lrx)                   + \
              ' ' + str(uly)                   + \
              ' -spat_srs'                     + \
              ' "' + srs.ExportToProj4() + '"' + \
              ' --debug on'                    + \
              ' ' + str(extraQueryParams)      + \
              ' "' + tempClipFile + '"'        + \
              ' "' + shpFile + '"'

        sCmd = SystemCommand(cmd, shpFile, self.logger, self.request, True)

        xml      = minidom.parse(tempClipFile)
        features = xml.getElementsByTagName('gml:featureMember')

        return features

    #---------------------------------------------------------------------------
    # compress
    #
    # retrieveOne -> processScene -> compress
    #---------------------------------------------------------------------------
    def compress(self, orthoBand):

        if self.logger:
            self.logger.info('Compressing ' + orthoBand)

        # To compress in place, copy the input file to a temporary file.
        tempBandFile = tempfile.mkstemp()[1]
        shutil.move(orthoBand, tempBandFile)

        cmd = 'gdal_translate -q -ot Int16 -co COMPRESS=LZW' + \
              ' -co BIGTIFF=YES'                             + \
              ' ' + tempBandFile                             + \
              ' ' + orthoBand

        sCmd = SystemCommand(cmd, orthoBand, self.logger, self.request, True)

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
                  '.tif'

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
        
        files = glob.glob(os.path.join(deleteDir, '*.tif'))
        
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
    def getScenes(self):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = self.request)
        scenes = []

        if evhrScenes:
            
            for es in evhrScenes:
                scenes.append(es.sceneFile.name)

        else:
            
            MAX_FEATS = 100

            # AoI + FOOTPRINTS = scenes
            scenes = self.queryFootprints(self.retrievalUlx,
                                          self.retrievalUly,
                                          self.retrievalLrx,
                                          self.retrievalLry,
                                          self.retrievalSRS,
                                          MAX_FEATS)
                                          
            for scene in scenes:
                
                evhrScene = EvhrScene()
                evhrScene.request = self.request
                evhrScene.sceneFile = scene
                evhrScene.save()
                
        return scenes
                
    #---------------------------------------------------------------------------
    # getUtmSrs
    #
    # This method finds the UTM zone covering the most of the request's AoI.
    # It does this by finding the centroid of the AoI and choosing that zone.
    #---------------------------------------------------------------------------
    def getUtmSrs(self, request):

        # Centroid, called below, doesn't preserve the SRS.
        srs = self.constructSrs(request.srs)
        
        center = self.bBoxToPolygon(request.ulx,
                                    request.uly,
                                    request.lrx,
                                    request.lry,
                                    srs).Centroid()
        
        # If request is already in WGS84 UTM...
        if srs.IsProjected() and 'UTM' in srs.GetAttrValue('PROJCS'):
            return request.srs

        # If the center is not in geographic projection, convert it.
        xValue = None

        if not GeoRetriever.GEOG_4326.IsSame(srs):

            xform = CoordinateTransformation(srs, GeoRetriever.GEOG_4326)
            xPt = xform.TransformPoint(center.GetX(), center.GetY())
            xValue = float(xPt.GetX())

        else:
            xValue = float(center.GetX())

        # Initally, use the UTM zone of the upper-left corner of the AoI.
        zone = (math.floor((xValue + 180.0) / 6) % 60) + 1
        BASE_UTM_EPSG = '326'
        epsg = int(BASE_UTM_EPSG + str(int(zone)))
        srs = GeoRetriever.constructSrsFromIntCode(epsg)
        return srs.ExportToWkt()
                
    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    # def listConstituents(self):
    #
    #     # If a saved scene list exists. use it.
    #     scenes = None
    #     sceneFile = os.path.join(self.request.destination.name, 'scenes.txt')
    #
    #     if os.path.exists(sceneFile):
    #
    #         with open(sceneFile) as f: sceneString = f.read()
    #         scenes = json.loads(sceneString)
    #
    #         if self.logger:
    #             self.logger.info('Using saved scene list.')
    #
    #     else:
    #
    #         # AoI + FOOTPRINTS = scenes
    #         MAX_FEATS = 100
    #
    #         scenes = self.queryFootprints(self.retrievalUlx,
    #                                       self.retrievalUly,
    #                                       self.retrievalLrx,
    #                                       self.retrievalLry,
    #                                       self.retrievalSRS,
    #                                       MAX_FEATS)
    #
    #         # Save the scenes because the query takes a long time to process.
    #         jsonScenes = json.dumps(scenes)
    #         with open(sceneFile, 'w+') as f: f.write(jsonScenes)
    #
    #     sceneGeoms = {}
    #
    #     for scene in scenes:
    #
    #         try:
    #             dg = DgFile(scene, self.logger)
    #
    #         except Exception, e:
    #
    #             err             = EvhrError()
    #             err.request     = self.request
    #             err.inputFile   = scene
    #             err.errorOutput = traceback.format_exc()
    #             err.save()
    #
    #             continue
    #
    #         geom = self.bBoxToPolygon(dg.ulx, dg.uly, dg.lrx, dg.lry,dg.srs)
    #         sceneGeoms[scene] = geom
    #
    #     # Define the tiles.
    #     tiler = TilerHalfDegree(self.retrievalUlx,
    #                             self.retrievalUly,
    #                             self.retrievalLrx,
    #                             self.retrievalLry,
    #                             self.retrievalSRS,
    #                             self.logger)
    #
    #     grid  = tiler.defineGrid()
    #     tiles = tiler.gridToPolygons(grid)
    #
    #     # Tiles + scenes = constituents.
    #     constituents = {}
    #     tileNum = 0
    #
    #     for tile in tiles:
    #
    #         tileNum += 1
    #         tileFile = self.createEmptyTile(tile, self.retrievalSRS, tileNum)
    #         constituents[tileFile] = []
    #
    #         for scene in scenes:
    #
    #             # Scenes could be rejected due to missing information.
    #             if not scene in sceneGeoms:
    #                 continue
    #
    #             if not tile.GetSpatialReference(). \
    #                    IsSame(sceneGeoms[scene].GetSpatialReference()):
    #
    #                 raise RuntimeError('Tile and scene must be in the '
    #                                    'same SRS.')
    #
    #             if tile.Intersects(sceneGeoms[scene]):
    #                 constituents[tileFile].append(scene)
    #
    #     return constituents
        
    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        scenes     = self.getScenes()
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
        features = self.clipShp(SHP_INDEX, ulx, uly, lrx, lry, srs)
        
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
        cmd = 'gdal_merge.py'     + \
              ' -o ' + outDemName + \
              ' -ul_lr'           + \
              ' ' + str(ulx)      + \
              ' ' + str(uly)      + \
              ' ' + str(lrx)      + \
              ' ' + str(lry)      + \
              ' ' + ' '.join(tiles)

        sCmd = SystemCommand(cmd, outDemName, self.logger, self.request, True)

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

            # get band name from bandFile
            ds = gdal.Open(bandFile, gdal.GA_ReadOnly)
            bandName =  ds.GetMetadataItem('bandName')
            ds = None

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
                                 True)

            # Convert NoData to settings value, set output type to Int16
            cmd = '/opt/StereoPipeline/bin/image_calc -c "var_0" {} -d int16   \
                        --output-nodata-value {} -o {}'.format(orthoFileTemp,  \
                                            settings.NO_DATA_VALUE, orthoFile)

            sCmd = SystemCommand(cmd, orthoFile, self.logger, self.request,True)

            os.remove(orthoFileTemp)

            # Add bandName metadata tag back
            ds = gdal.Open(orthoFile, gdal.GA_ReadOnly)
            ds.SetMetadataItem("bandName", bandName)
            ds = None

        return orthoFile

    #---------------------------------------------------------------------------
    # processScene
    #
    # The original NITF, extracted bands and orthorectified scenes remain
    # unclipped.  Only the final orthorectified image is clipped in mergeBands
    # or compress.
    #---------------------------------------------------------------------------
    def processScene(self, inputNitf):

        if self.logger:
            self.logger.info('Processing scene ' + str(inputNitf))

        # Get the output name to see if it exists.
        bname = os.path.basename(inputNitf).replace('.ntf', '-ortho.tif')
        toaFinal = os.path.join(self.toaDir, bname.replace('.tif', '-toa.tif'))

        # If the output file exists, don't bother running it again.
        if not os.path.exists(toaFinal):

            dgFile = DgFile(inputNitf, self.logger)
            bandFiles = self.extractBands(dgFile)
            toaBands = []

            for bandFile in bandFiles:
            
                orthoBand = self.orthoOne(bandFile, dgFile)
            
                toaBands.append(TOA.run(orthoBand, 
                                        self.toaDir, 
                                        inputNitf, 
                                        self.logger))
            
            self.mergeBands(toaBands, toaFinal)
            
        return toaFinal

    #---------------------------------------------------------------------------
    # queryFootprints
    #
    # listConstituents -> queryFootprints
    #---------------------------------------------------------------------------
    def queryFootprints(self, ulx, uly, lrx, lry, srs, maxFeatures = None):

        whereClause = '-where "'
        first = True

        for sensor in self.runSensors:

            if first:
                first = False
            else:
                whereClause += ' OR '

            whereClause += 'SENSOR=' + "'" + sensor + "'"

        whereClause += '"'

        features = self.clipShp(EvhrMosaicRetriever.FOOTPRINTS_FILE, \
                                ulx, uly, lrx, lry, srs,             \
                                whereClause)

        # Put them into a list of (row, path) tuples.
        nitfs = []
        featureCount = 0

        for feature in features:

            featureCount += 1

            if maxFeatures and featureCount > maxFeatures:
                break

            nitf = str(feature. \
                       getElementsByTagName('ogr:S_FILEPATH')[0]. \
                       firstChild. \
                       data)

            nitfs.append(nitf)

        return nitfs

    #---------------------------------------------------------------------------
    # retrieveOne
    #
    # This receives a 1/2 degree tile file and the list of NITF files that
    # intersect it.  The NITF files have not been clipped.
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        #---
        # Orthorectify the full scene, clip to the half-degree-square tile,
        # and covert to Geotiff.
        #---
        completedScenes = [self.processScene(nitf) for nitf in fileList]
        
        self.deleteFiles(self.bandDir)
        self.deleteFiles(self.demDir)
        self.deleteFiles(self.orthoDir)

        # Mosaic the scenes into a single file.
        return completedScenes[0]


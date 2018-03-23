
import json
import math
import os
import shutil
import tempfile
from xml.dom import minidom

import numpy

from osgeo import gdal
from osgeo.osr import CoordinateTransformation
from osgeo.osr import SpatialReference

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever
from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.commands.TOA import TOA
from django.conf import settings

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
# https://github.com/NeoGeographyToolkit/StereoPipeline
#
# --- Crystal Fire ---
# ./manage.py processGeoRequest --name testCrystal --epName "EVHR Mosaic" --ulx -113.39250146 --uly 43.35041085 --lrx -112.80953835 --lry 42.93059617 --epsg 4326 --outEpsg 102039 -n 1
#-------------------------------------------------------------------------------
class EvhrMosaicRetriever(GeoRetriever):

    DEM_FILE        = '/att/pubrepo/DEM/SRTM/1-ArcSec'
    FOOTPRINTS_FILE = '/att/pubrepo/NGA/INDEX/Footprints/current/10_05_2017/geodatabase/nga_inventory_10_05_2017.gdb'
    # FOOTPRINTS_FILE = '/att/nobackup/dslaybac/PublicMD/DG_28Nov2017.gdb'
    QUERY_LAYER     = 'nga_inventory_10_05_2017'

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger):

        # EVHR gets its own subdirectory because it can have multiple files.
        if os.path.basename(request.destination.name) != 'EVHR':

            request.destination.name = \
                os.path.join(request.destination.name,'EVHR')

            request.save(update_fields = ['destination'])

        if not os.path.exists(request.destination.name):
            os.mkdir(request.destination.name)

        # The output SRS must be UTM, regardless of what the user chooses.
        request.outSRS = self.getUtmSrs(request)
        request.save(update_fields = ['outSRS'])

        # Initialize the base class.
        super(EvhrMosaicRetriever, self).__init__(request, logger)

        #---
        # GeoRetriever should always choose EPSG:4326 as the retrieval SRS
        # because that is all that FOOTPRINTS knows.  Verify that.
        #---
        if not self.retrievalSRS.IsSame(GeoRetriever.GEOG_4326):
            raise RuntimeError('Retrieval SRS must be geographic.')

        self.runSensors = ['WV01', 'WV02', 'WV03']

        # Ensure the orthos and toa directories exists.
        self.orthoDir = os.path.join(self.request.destination.name, 'orthos')
        self.toaDir   = os.path.join(self.request.destination.name, 'toa')

        if not os.path.exists(self.orthoDir):
            os.mkdir(self.orthoDir)

        if not os.path.exists(self.toaDir):
            os.mkdir(self.toaDir)

    #---------------------------------------------------------------------------
    # clipShp
    #---------------------------------------------------------------------------
    def clipShp(self, shpFile, ulx, uly, lrx, lry, srs, extraQueryParams = ''):

        if self.logger:
            self.logger.info('Clipping Shapefile.')

        # Create a temporary file for the clip output.
        tempClipFile = tempfile.mkstemp()[1]

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

        self.runSystemCmd(cmd)

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

        self.runSystemCmd(cmd)

    #---------------------------------------------------------------------------
    # createDemForOrthos
    #
    # retrieveOne -> processScene -> orthoOne -> createDemForOrthos
    #---------------------------------------------------------------------------
    def createDemForOrthos(self, ulx, uly, lrx, lry, srs):

        if self.logger:
            self.logger.info('Creating DEM for orthorectification.')

        # Ensure the clippedDEMs subdirectory exists.
        clipDir = os.path.join(self.request.destination.name, 'clippedDEMs')

        if not os.path.exists(clipDir):
            os.mkdir(clipDir)

        # If there is already a clipped DEM for this bounding box, use it.
        demName = 'dem-'                          + \
                  str(ulx) + '-'                  + \
                  str(uly) + '-'                  + \
                  str(lrx) + '-'                  + \
                  str(lry) + '-'                  + \
                  str(srs.GetAuthorityCode(None)) + \
                  '.tif'

        demName = os.path.join(clipDir, demName)

        if os.path.exists(demName):
            return demName

        # Expand the bounding box before clipping the DEM.
        xUlx, xUly, xLrx, xLry = self.expandByPercentage(ulx, uly, lrx, lry,srs)

        # Mosaic SRTM tiles to cover this AoI.
        self.mosaicAndClipDemTiles(demName, xUlx, xUly, xLrx, xLry, srs)

        return demName

    #---------------------------------------------------------------------------
    # createEmptyTiles
    #---------------------------------------------------------------------------
    def createEmptyTiles(self):

        # Ensure the clippedDEMs subdirectory exists.
        templDir = os.path.join(self.request.destination.name, 'tileTemplates')

        if not os.path.exists(templDir):
            os.mkdir(templDir)

        #---
        # Here is where we define position the start of the tile grid.
        # Initially, we start it at the upper-left of the request AoI.  If ever
        # we want a more efficient tiling scheme to align the AoI, the UTM grid,
        # and the half-degree tile grid, do that here by adjusting this starting
        # point.
        #---
        startingX = self.request.ulx
        startingY = self.request.uly

        #---
        # Create the upper-left and lower-right tile corners, based on the
        # starting point and lower-left of the request AoI.
        #---
        corners = self.imposeGridOnAoI(startingX,
                                       startingY,
                                       self.request.lrx,
                                       self.request.lry)

        # Use the corners to create GeoTiffs representing each constituent.
        tiles = []
        count = 0

        for corner in corners:

            ulx = corner[0]
            uly = corner[1]
            lrx = corner[2]
            lry = corner[3]

            count += 1
            constituentName = os.path.join(self.request.destination.name,
                                           templDir,
                                           'tileTemplate' + str(count) + '.tif')

            height = 1  # Choose a nominal height and width.  All we really
            width  = 1  # need is the extent and file name of this tile tif.
            driver = gdal.GetDriverByName('GTiff')
            ds     = driver.Create(constituentName, width, height)

            if not ds:
                raise RuntimeError('Unable to open ' + str(constituentName))

            ds.SetProjection(str(self.retrievalSRS))

            rotation = 0
            xRes = lrx - ulx
            yRes = (uly - lry) * -1.0

            ds.SetGeoTransform([ulx, xRes, rotation, uly, rotation, yRes])
            raster = numpy.zeros((height, width), dtype = numpy.uint8)

            ds.GetRasterBand(1).WriteArray(raster)
            ds = None

            tiles.append(constituentName)

        return tiles

    #---------------------------------------------------------------------------
    # extractBands
    #
    # retrieveOne -> processScene -> extractBands (multispectral only)
    #---------------------------------------------------------------------------
    def extractBands(self, nitfFile):

        if self.logger:
            self.logger.info('Extracting bands from ' + str(nitfFile.fileName))

        # Make a directory for temporary band files.
        tempDir = os.path.join(self.request.destination.name, 'bandFiles')

        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        # Get the bands to use.
        bands = ['BAND_P'] if nitfFile.isPanchromatic() else \
                ['BAND_B', 'BAND_G', 'BAND_R', 'BAND_N']

        # Extract the bands.
        bandFiles = []

        for band in bands:

            bandFileName = nitfFile.getBand(tempDir, band)
            bandFiles.append(bandFileName)

        return bandFiles

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # getUtmSrs
    #---------------------------------------------------------------------------
    def getUtmSrs(self, request):

        requestSRS = self.constructSrs(request.srs)

        # If request is already in WGS84 UTM...
        if requestSRS.IsProjected() and \
           'UTM' in requestSRS.GetAttrValue('PROJCS'):

            return request.srs

        # If the request is not in geographic projection, convert it.
        xValue = None

        if not GeoRetriever.GEOG_4326.IsSame(requestSRS):

            xform = CoordinateTransformation(requestSRS,GeoRetriever.GEOG_4326)
            xPt = xform.TransformPoint(request.ulx, request.uly)
            xValue = float(xPt.GetX())

        else:
            xValue = float(request.ulx)

        # Initally, use the UTM zone of the upper-left corner of the AoI.
        zone = (math.floor((xValue + 180.0) / 6) % 60) + 1
        BASE_UTM_EPSG = '326'
        epsg = int(BASE_UTM_EPSG + str(int(zone)))
        srs = GeoRetriever.constructSrsFromIntCode(epsg)
        return srs.ExportToWkt()

    #---------------------------------------------------------------------------
    # imposeGridOnAoI
    #
    # This method, given an AoI, returns a list of 1/2-degree square grid
    # corners.  CreateEmptyTiles() uses this to lay a grid based on the starting
    # point it chooses to best align the AoI, the UTM grid and the half-degree
    # grid.
    #---------------------------------------------------------------------------
    def imposeGridOnAoI(self, ulx, uly, lrx, lry):

        #---
        # Start at the upper-left corner of the AoI, and create 1/2-degree
        # square tiles.  Adjust initial lon and lat by 0.5, so the loop's test
        # lets the tiles encompass the far edges of the AoI.
        #---
        lons   = []
        curLon = float(self.request.ulx) - 0.5
        maxLon = float(self.request.lrx)

        while curLon <= maxLon:

            curLon += 0.5
            lons.append(curLon)

        lats   = []
        curLat = float(self.request.uly) + 0.5
        minLat = float(self.request.lry)

        while curLat >= minLat:

            curLat -= 0.5
            lats.append(curLat)

        # We have the lats and longs comprising the grid.  Form them into tiles.
        corners = []

        for x in range(len(lons) - 1):
            for y in range(len(lats) - 1):
                corners.append((lons[x], lats[y], lons[x+1], lats[y+1]))

        return corners

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        #---
        # constituents = {'/path/to/scene1.tif' : [/path/to/scene1.ntf],
        #                 '/path/to/scene2.tif' : [/path/to/scene2.ntf],
        #                 ...
        #                }
        #
        # If a saved constituent list exists. use it.
        #---
        constituents = None
        
        constituentFile = os.path.join(self.request.destination.name,
                                       'constituents.txt')

        if os.path.exists(constituentFile):

            with open(constituentFile) as f:
                constituentsString = f.read()

            constituents = json.loads(constituentsString)

            if self.logger:
                self.logger.info('Using saved constituent list.')

        else:

            # Query FOOTPRINTS using the AoI.
            MAX_FEATS = 10

            scenes = self.queryFootprints(self.retrievalUlx,
                                          self.retrievalUly,
                                          self.retrievalLrx,
                                          self.retrievalLry,
                                          MAX_FEATS)
                                          
            constituents = {}
            
            for scene in scenes:
                
                consName = scene.replace('.ntf', '.tif')
                constituents[consName] = scene

            # The FOOTPRINTS query is lengthy, so save the results.
            jsonConstituents = json.dumps(constituents)

            with open(constituentFile, 'w+') as f:
                f.write(jsonConstituents)

        return constituents
            
    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    # def listConstituents(self):
    #
    #     #---
    #     # Impose 1/2 degree by 1/2 degree tiling on AoI.  Create an empty output
    #     # file for each tile.  These empty files will have the extent of their
    #     # 1/2 degree tiles.  RetrieveOne() will clip the files in its fileList
    #     # to this.
    #     #
    #     # constituents = {'/path/to/outputTile1.tif' : [],
    #     #                 '/path/to/outputTile2.tif' : [], ...}
    #     #
    #     # The list of constituents associated with each tile contains the full
    #     # path to each NITF scene overlapping the tile.  The NITF could cover a
    #     # much larger area than the tile.  Clipping happens later.
    #     #
    #     # If a saved constituent list exists. use it.
    #     #---
    #     constituentFile = os.path.join(self.request.destination.name,
    #                                   'constituents.txt')
    #
    #     if os.path.exists(constituentFile):
    #
    #         with open(constituentFile) as f:
    #             constituentsString = f.read()
    #
    #         constituents = json.loads(constituentsString)
    #
    #         if self.logger:
    #             self.logger.info('Using saved constituent list.')
    #
    #     else:
    #
    #         #---
    #         # Create a list of empty tile files which define the overall tiling
    #         # scheme.
    #         #---
    #         tiles = self.createEmptyTiles()
    #
    #         #---
    #         # Make a dictionary where the key is a tile file and the values
    #         # are blank.  The values will become a list of scenes from
    #         # FOOTPRINTS.
    #         #---
    #         constituents = {key : [] for key in tiles}
    #
    #         # Query FOOTPRINTS for each tile.
    #         MAX_FEATS = 10
    #
    #         for key in constituents.iterkeys():
    #
    #             outFile = key
    #             constituents[outFile] = self.queryFootprintsFromFile(outFile, MAX_FEATS)
    #
    #         # The FOOTPRINTS query is lengthy, so save the results.
    #         jsonConstituents = json.dumps(constituents)
    #
    #         with open(constituentFile, 'w+') as f:
    #             f.write(jsonConstituents)
    #
    #     return constituents

    #---------------------------------------------------------------------------
    # mergeBands
    #---------------------------------------------------------------------------
    def mergeBands(self, bandFiles, outFileName, deleteBands = True):

        if self.logger:
            self.logger.info('Merging bands into ' + str(outFileName))

        cmd = 'gdal_merge.py -co COMPRESS=LZW -co BIGTIFF=YES -ot Int16 \
                -separate -n {} -a_nodata {} -o {} {}'. \
                format(settings.NO_DATA_VALUE, \
                       settings.NO_DATA_VALUE, 
                       outFileName, \
                       ' '.join(bandFiles))

        self.runSystemCmd(cmd)

        # Remove the band files.
        if deleteBands:
            for bandFile in bandFiles:
                os.remove(bandFile)

    #---------------------------------------------------------------------------
    # mosaicAndClipDemTiles
    #
    # retrieveOne -> processScene -> orthoOne -> createDemForOrthos
    # -> mosaicAndClipDemTiles
    #
    # To build the SRTM index file:
    # gdaltindex -t_srs "EPSG:4326" -src_srs_name SRS srtm.shp /att/pubrepo/DEM/SRTM/1-ArcSec/*.hgt
    #---------------------------------------------------------------------------
    def mosaicAndClipDemTiles(self, outDemName, ulx, uly, lrx, lry, srs):

        if self.logger:
            self.logger.info('Creating DEM ' + str(outDemName))

        # Get the SRTM tile Shapefile and intersect it with the AoI.
        SHP_INDEX = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'SRTM/srtm.shp')

        features = self.clipShp(SHP_INDEX, ulx, uly, lrx, lry, srs)

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

        self.runSystemCmd(cmd)

    #---------------------------------------------------------------------------
    # orthoOne
    #
    # retrieveOne -> processScene -> orthoOne
    #---------------------------------------------------------------------------
    def orthoOne(self, bandFile, origDgFile):

        if self.logger:
            self.logger.info('Orthorectifying ' + str(bandFile))

        clippedDEM = self.createDemForOrthos(origDgFile.ulx,
                                             origDgFile.uly,
                                             origDgFile.lrx,
                                             origDgFile.lry,
                                             origDgFile.srs)
        # Orthorectify.
        baseName  = os.path.splitext(os.path.basename(bandFile))[0]
        orthoFile = os.path.join(self.orthoDir, baseName + '-ortho.tif')
        orthoFileTemp = orthoFile.replace('.tif', '-temp.tif')

        # get band name from bandFile
        ds = gdal.Open(bandFile, gdal.GA_ReadOnly)
        bandName =  ds.GetMetadataItem('bandName')
        ds = None

        if not os.path.exists(orthoFile):

            cmd = '/opt/StereoPipeline/bin/mapproject --nodata-value 0' + \
                  ' --threads=2 -t rpc --mpp=2'                         + \
                  ' ' + clippedDEM                                      + \
                  ' ' + bandFile                                        + \
                  ' ' + origDgFile.xmlFileName                          + \
                  ' ' + orthoFileTemp

            self.runSystemCmd(cmd)

            # Convert NoData to settings value, set output type to Int16
            cmd = '/opt/StereoPipeline/bin/image_calc -c "var_0" {} -d int16   \
                        --output-nodata-value {} -o {}'.format(orthoFileTemp,  \
                                            settings.NO_DATA_VALUE, orthoFile)

            self.runSystemCmd(cmd)

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

        toaFinal = os.path.join(self.request.destination.name, \
                                self.toaDir,
                                bname.replace('.tif', '-toa.tif'))

        # If the output file exists, don't bother running it again.
        if os.path.exists(toaFinal):
            return toaFinal

        dgFile    = DgFile(inputNitf)
        bandFiles = self.extractBands(dgFile)
        toaBands  = []

        for bandFile in bandFiles:
            
            orthoBand = self.orthoOne(bandFile, dgFile)
            
            toaBands.append(TOA.run(orthoBand, 
                                    self.toaDir, 
                                    inputNitf, 
                                    self.logger))
            
            os.remove(bandFile)
            os.remove(orthoBand)
            
        self.mergeBands(toaBands, toaFinal)
            
        return toaFinal

    #---------------------------------------------------------------------------
    # queryFootprints
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
    # queryFootprintsFromFile
    #---------------------------------------------------------------------------
    def queryFootprintsFromFile(self, clipFile, maxFeatures = None):

        # Get the extent of the clip file.
        dataset = gdal.Open(clipFile, gdal.GA_ReadOnly)

        if not dataset:
            raise RuntimeError('Unable to open ' + str(clipFile))

        geoTransform = dataset.GetGeoTransform()
        ulx          = geoTransform[0]
        uly          = geoTransform[3]
        lrx          = ulx + geoTransform[1] * dataset.RasterXSize
        lry          = uly + geoTransform[5] * dataset.RasterYSize
        srs          = SpatialReference(dataset.GetProjection())
        dataset      = None
        
        return self.queryFootprints(self, ulx, uly, lrx, lry, srs, maxFeatures)

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

        # Mosaic the scenes into a single file.
        return completedScenes[0]   # This is temporary, so retrieveOne returns something.

    #---------------------------------------------------------------------------
    # runSystemCmd
    #---------------------------------------------------------------------------
    def runSystemCmd(self, cmd):

        if not cmd:
            return

        if self.logger:
            self.logger.info('Command: ' + cmd)

        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('System command failed.')


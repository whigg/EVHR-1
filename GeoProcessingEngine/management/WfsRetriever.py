
import glob
import logging
import math
import mmap
import numpy
import os
import shutil

from owslib.wfs import WebFeatureService

from osgeo import gdal
from osgeo import ogr

from django.conf import settings

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class WfsRetriever
#-------------------------------------------------------------------------------
class WfsRetriever(GeoRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        owslibLog = logging.getLogger('owslib')
        owslibLog.setLevel(logging.DEBUG)

        self.service = WebFeatureService(request.endPoint.url, 
                                         request.endPoint.version)

        if not request.endPoint.serviceId in self.service.contents:

            raise RuntimeError('Unable to find ' + \
                               request.endPoint.serviceId + \
                               ' for ' + request.endPoint.name + \
                               ' at '  + request.endPoint.url  + \
                               ' service contents: '   + \
                               str(self.service.contents))

        super(WfsRetriever, self).__init__(request, logger, numProcesses)

    #---------------------------------------------------------------------------
    # axisOrderLonLat
    #
    # (89, 89), (-89, 89), (89, -89)
    #---------------------------------------------------------------------------
    # def axisOrderLonLat(self, featFile):
    #
    #     ds = gdal.OpenEx(featFile, gdal.OF_VECTOR )
    #
    #     if ds is None:
    #         raise RuntimeError('Unable to open ' + str(featFile))
    #
    #     layer    = ds.GetLayerByIndex()
    #     extent   = layer.GetExtent()
    #     minX     = extent[0]
    #     maxX     = extent[1]
    #     minY     = extent[2]
    #     maxY     = extent[3]
    #     isLonLat = None
    #
    #     if minX < 0 or maxX < 0 or minX > 90 or maxX > 90:
    #
    #         isLonLat = True
    #
    #     elif minY < 0 or maxY < 0 or minY > 90 or maxY > 90:
    #
    #         isLonLat = False
    #
    #     if not isLonLat:
    #
    #         raise RuntimeError('Cannot determine the axis order in ' + \
    #                            str(featFile))
    #
    #     return isLonLat
        
    #---------------------------------------------------------------------------
    # clipGML
    #---------------------------------------------------------------------------
    def clipGML(self, inFile, ulx, uly, lrx, lry, srs):
        
        if self.logger:
            self.logger.info('In clipGML ...')
            
        path, fullName = os.path.split(inFile)
        name, ext      = os.path.splitext(fullName)
        clipFile       = os.path.join(path, name + '-clipped' + ext)

        albersOrds = self.transformBbox(ulx, 
                                        uly, 
                                        lrx, 
                                        lry, 
                                        srs, 
                                        GeoRetriever.ALBERS_102039)

        cmd = 'ogr2ogr ' + \
              '-s_srs "' + srs.ExportToProj4() + '" ' + \
              '-t_srs "' + GeoRetriever.ALBERS_102039.ExportToProj4() + '" ' + \
              '-f GML ' + \
              '-clipdst ' + \
              str(albersOrds[0]) + ' ' + \
              str(albersOrds[3]) + ' ' + \
              str(albersOrds[2]) + ' ' + \
              str(albersOrds[1]) + ' ' + \
              '"' + clipFile + '" ' + \
              '"' + inFile   + '"'
              
        status = self.runCommand(cmd)
        
        # We don't need inFile any longer.  Delete it and its counterparts.
        self.removeAncillaryFiles(inFile)

        # Now it's clipped and in Albers.  Transform it to the output SRS.
        xformFile = os.path.join(path, name + '-transformed' + ext)
        
        cmd = 'ogr2ogr ' + \
              '-s_srs "' + GeoRetriever.ALBERS_102039.ExportToProj4() + '" ' + \
              '-t_srs "' + self.outSRS.ExportToProj4() + '" ' + \
              '-f GML '  + \
              '"' + xformFile + '" ' + \
              '"' + clipFile  + '"'
        
        status = self.runCommand(cmd)

        self.removeAncillaryFiles(clipFile)

        if status == 0:
            
            outputBaseName = os.path.splitext(inFile)[0]
            xformFiles = glob.glob(os.path.splitext(xformFile)[0] + '.*')
        
            for xformFile in xformFiles:
            
                name, ext = os.path.splitext(xformFile)
                destFile  = outputBaseName + ext
                shutil.move(xformFile, destFile)
        
    #---------------------------------------------------------------------------
    # createEmptyRaster
    #---------------------------------------------------------------------------
    def createEmptyRaster(self, outFileName, ulx, uly, lrx, lry, srs):
        
        if self.logger:
            self.logger.info('In createEmtpyRaster...')
                
        # Get the bounding box in terms of the output CRS.
        outUlx, outUly, outLrx, outLry = self.transformBbox(ulx,
                                                            uly,
                                                            lrx,
                                                            lry,
                                                            srs,
                                                            self.outSRS)
        
        # Create the output file.
        path, file = os.path.split(outFileName)
        name, ext  = os.path.splitext(file)
        tifName    = os.path.join(path, name + '.tif')

        # Compute height and width based on the given scale.
        scale = settingsDEFAULT_SCALE_IN_METERS
        
        outUl = ogr.Geometry(ogr.wkbPoint)
        outUl.AddPoint(float(outUlx), float(outUly))
        outUl.AssignSpatialReference(self.outSRS)
        
        outLr = ogr.Geometry(ogr.wkbPoint)
        outLr.AddPoint(float(outLrx), float(outLry))
        outLr.AssignSpatialReference(self.outSRS)
        
        outUr = ogr.Geometry(ogr.wkbPoint)
        outUr.AddPoint(float(outLrx), float(outUly))
        outUr.AssignSpatialReference(self.outSRS)

        xDist = outUl.Distance(outUr)
        yDist = abs(outLr.Distance(outUr))

        width  = int(math.ceil(float(xDist) / scale))
        height = int(math.ceil(float(yDist) / scale))

        # Configure the file.
        driver   = gdal.GetDriverByName('GTiff')
        ds       = driver.Create(tifName, width, height)
        rotation = 0
        
        ds.SetProjection(str(self.outSRS.ExportToWkt()))
        
        ds.SetGeoTransform([outUlx, 
                            scale, 
                            rotation, 
                            outUly, 
                            rotation, 
                            scale * -1])
        
        raster = numpy.zeros((height, width), dtype = numpy.uint8)    
        ds.GetRasterBand(1).WriteArray(raster)
        ds = None
        
        os.remove(outFileName)
        return tifName

    #---------------------------------------------------------------------------
    # flipAxis
    #---------------------------------------------------------------------------
    # def flipAxis(self, outFileName, srs):
    #
    #     path, file = os.path.split(outFileName)
    #     name, ext  = os.path.splitext(file)
    #     beforeName = os.path.join(path, name + '-beforeAxisFlipped' + '.gml')
    #     flipName   = os.path.join(path, name + '-axisFlipped'       + '.gml')
    #     gfsName    = os.path.join(path, name + '.gfs')
    #
    #     shutil.move(outFileName, beforeName)
    #     os.remove(gfsName)
    #
    #     wkt   = srs.ExportToProj4()
    #     wktNe = wkt + ' +axis=neu +wktext'
    #     wktEn = wkt + ' +axis=enu +wktext'
    #
    #     cmd = 'ogr2ogr -f "GML" -s_srs "' + wktNe + '" -t_srs "' + wktEn + \
    #           '" "' + flipName + '" "' + beforeName + '"'
    #
    #     status = os.system(cmd)
    #
    #     if status != 0:
    #         raise RuntimeError('Failed to flip axes.  Status = ' + str(status))
    #
    #     shutil.copyfile(flipName, outFileName)
    #
    #     try:
    #         beforeGfsName = beforeName.replace('.gml', '.gfs')
    #         flipXsdName   = flipName.replace('.gml', '.xsd')
    #
    #         os.remove(beforeName)
    #         os.remove(beforeGfsName)
    #         os.remove(flipName)
    #         os.remove(flipXsdName)
    #         os.remove(gfsName)
    #
    #     except:
    #         pass
        
    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):

        # Use a dict, to avoid storing duplicates.
        srsDict = {}
        
        crsOptions = self.service.contents[self.request.endPoint.serviceId]. \
                        crsOptions
        
        for crs in crsOptions:

            code = crs.getcode()

            if code not in srsDict:
                srsDict[code] = GeoRetriever.constructSrsFromCode(code)
        
        return srsDict.values()

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        outFileName = self.getOutFileName(self.request.endPoint.name, '.gml')
        return {outFileName: [outFileName]}
        
    #---------------------------------------------------------------------------
    # rasterize
    #---------------------------------------------------------------------------
    def rasterize(self, inFileName, xmlId, srid):
        
        if self.logger:
            self.logger.info('Creating rasterize...')
                
        # If the xmlId has a namespace, remove it.
        xmlId = xmlId.split(':')[-1]
        
        path, file = os.path.split(inFileName)
        name, ext  = os.path.splitext(file)
        tifName    = os.path.join(path, name + '.tif')

        cmd = 'gdal_rasterize -of GTiff -ts 250 250 -burn 100' + \
              ' -l ' + xmlId + \
              ' -a_srs EPSG:' + str(srid) + \
              ' "' + inFileName + '" "' + tifName + '"'

        status = os.system(cmd)
        
        if status != 0:
            raise RuntimeError('Failed rasterize layer.')

        try:
            gfsName = inFileName.replace('.gml', '.gfs')
            os.remove(inFileName)
            os.remove(gfsName)
            
        except:
            pass
            
        return tifName

    #---------------------------------------------------------------------------
    # removeAncillaryFiles
    #---------------------------------------------------------------------------
    def removeAncillaryFiles(self, exampleFileName):
        
        inFiles = glob.glob(os.path.splitext(exampleFileName)[0] + '.*')
        
        for inFile in inFiles:
            os.remove(inFile)
    
    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        self.bBoxToVector(self.request.ulx, 
                          self.request.uly, 
                          self.request.lrx, 
                          self.request.lry, 
                          self.requestSRS, 
                          'request')
                                    
        self.bBoxToVector(self.retrievalUlx, 
                          self.retrievalUly, 
                          self.retrievalLrx, 
                          self.retrievalLry, 
                          self.retrievalSRS, 
                          'retrieval')
                                    
        exUlx, exUly, exLrx, exLry = \
            self.expandByPercentage(self.retrievalUlx, 
                                    self.retrievalUly, 
                                    self.retrievalLrx, 
                                    self.retrievalLry, 
                                    self.retrievalSRS, 
                                    10)
                                                             
        self.bBoxToVector(exUlx, 
                          exUly, 
                          exLrx, 
                          exLry, 
                          self.retrievalSRS, 
                          'expanded')
                                    
        # contents = self.service.contents[self.request.endPoint.serviceId]
        bboxOGC  = [exUlx, exLry, exLrx, exUly]
        crs      = 'EPSG:' + str(self.retrievalSRS.GetAuthorityCode(None))
        featureFilter  = None
        featureId      = None
        featureVersion = None
        maxFeatures    = None
        propertyName   = None 
        tnList         = [self.request.endPoint.serviceId]
        
        # Hate to do this, but we must hard code a special case for Soils.
        if self.request.endPoint.name == 'Soils':
            
            featureFilter = '<filter><bbox><propertyName>Geometry'       + \
                            '</propertyName><box srsName="' + crs + '">' + \
                            '<coordinates>'                              + \
                            exUlx + ' '                                  + \
                            exLry + ' '                                  + \
                            exLrx + ' '                                  + \
                            exUly                                        + \
                            '</coordinates></box></bbox></filter>'
            
            url = self.service.getfeature(tnList, 
                                          featureFilter, 
                                          None, 
                                          featureId, 
                                          featureVersion,   
                                          propertyName, 
                                          maxFeatures, 
                                          None)
        else:

            url = self.service.getfeature(tnList, 
                                          featureFilter,        
                                          bboxOGC, 
                                          featureId,  
                                          featureVersion, 
                                          propertyName, 
                                          maxFeatures, 
                                          crs)

        fOut = open(constituentFileName, 'w+')
        fOut.write(url.read())

        #---
        # Count the features retrieved.  If there are none, create an
        # empty raster.
        #---
        fileType = 'GML'
        fOut.seek(0)
        results = mmap.mmap(fOut.fileno(), 0, prot = mmap.PROT_READ)
        
        if results.find('featureMember') == -1:
            
            fOut.close()
            results.close()

            constituentFileName = self.createEmptyRaster(constituentFileName, 
                                                         exUlx, 
                                                         exUly, 
                                                         exLrx, 
                                                         exLry,
                                                         self.retrievalSRS)
                
            fileType = None
            self.xformOutput(constituentFileName, None, fileType)
            
        else:
            fOut.close()
            results.close()

            #---
            # If necessary, flip the order of the coordinates.  If the GML
            # file has no SRS information, this will fail.
            #---
            # if not self.axisOrderLonLat(constituentFileName):
            #     self.flipAxis(constituentFileName, self.outSRS)

            #---
            # If the retrieval CRS is incompatible with the output CRS, 
            # rasterize the layer.
            #---
            # if not bbox.crs().isCompatible(self.outSRS):
            #
            #     constituentFileName = \
            #         self.rasterize(constituentFileName,
            #                        self.request.endPoint.serviceId,
            #                        self.outSRS)
            #
            #     fileType = None
            #     self.xformOutput(constituentFileName, None, fileType)
            #
            # else:
            #     #---
            #     # At this point, the features will not be rasters.  The must
            #     # be clipped, reprojected and reformatted.  Clipping must be
            #     # in the output SRS; however, unlike gdalwarp, ogr2ogr cannot
            #     # clip in anything but the source or destination SRS.
            #     # Therefore, this requires two steps.  Clip here.
            #     #---
            #     self.clipGML(constituentFileName)

            self.clipGML(constituentFileName, 
                         self.retrievalUlx, 
                         self.retrievalUly, 
                         self.retrievalLrx, 
                         self.retrievalLry, 
                         self.retrievalSRS)
                
        return constituentFileName

    #---------------------------------------------------------------------------
    # runCommand
    #---------------------------------------------------------------------------
    def runCommand(self, cmd):
        
        if self.logger:
            self.logger.info("Command:  " + cmd)

        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('Failed to clip layer.')
            
        return status
  

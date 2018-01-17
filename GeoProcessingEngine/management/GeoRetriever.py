
import os
import shutil

from osgeo import ogr
from osgeo.osr import CoordinateTransformation
from osgeo.osr import SpatialReference

from ProcessingEngine.management.Retriever import Retriever

from GeoProcessingEngine import settings
from GeoProcessingEngine.models import GeoRequest

#-------------------------------------------------------------------------------
# class GeoRetriever
#
# This extends Retriever for GIS processing.
# https://pcjericks.github.io/py-gdalogr-cookbook/geometry.html
# https://pcjericks.github.io/py-gdalogr-cookbook/projection.html
#-------------------------------------------------------------------------------
class GeoRetriever(Retriever):

    # SRSs common to the Wrangler domain.
    ALBERS_102039         = SpatialReference('PROJCS["USA_Contiguous_Albers_Equal_Area_Conic",GEOGCS["GCS_North_American_1983",DATUM["North_American_Datum_1983",SPHEROID["GRS_1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["False_Easting",0],PARAMETER["False_Northing",0],PARAMETER["longitude_of_center",-96],PARAMETER["Standard_Parallel_1",29.5],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["latitude_of_center",37.5],UNIT["Meter",1],AUTHORITY["EPSG","102003"]]')
    GEOG_4326             = SpatialReference('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
    MODIS_SINUSOIDAL_6842 = SpatialReference('PROJCS["Sinusoidal",GEOGCS["GCS_Undefined",DATUM["Undefined",SPHEROID["User_Defined_Spheroid",6371007.181,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Sinusoidal"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],UNIT["Meter",1.0]]')
    
    SPECIAL_PROJECTIONS = {
        'EPSG:6842'   : MODIS_SINUSOIDAL_6842,
        'EPSG:102003' : ALBERS_102039,
        'EPSG:102039' : ALBERS_102039,
    }
    
    #---------------------------------------------------------------------------
    # __init__ 
    #---------------------------------------------------------------------------
    def __init__(self, request, logger = None, maxProcesses = 1):

        super(GeoRetriever, self).__init__(request, logger)
        
        self.requestSRS    = self.constructSrs(self.request.srs)
        self.outSRS        = self.constructSrs(self.request.outSRS)
        self.supportedSRSs = self.getEndPointSRSs(self.request.endPoint)
        self.retrievalSRS  = self.getRetrievalSRS(self.requestSRS)

        retrievalOrds = self.transformBbox(self.request.ulx, 
                                           self.request.uly, 
                                           self.request.lrx, 
                                           self.request.lry, 
                                           self.requestSRS,  
                                           self.retrievalSRS)

        self.retrievalUlx = retrievalOrds[0]
        self.retrievalUly = retrievalOrds[1]
        self.retrievalLrx = retrievalOrds[2]
        self.retrievalLry = retrievalOrds[3]
        
    #---------------------------------------------------------------------------
    # bBoxToVector
    #
    # This is helpful for testing, to visualize bounding boxes.
    #---------------------------------------------------------------------------
    def bBoxToVector(self, ulx, uly, lrx, lry, srs, name):
        
        fUlx = float(ulx)
        fUly = float(uly)
        fLrx = float(lrx)
        fLry = float(lry)

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(fUlx, fUly)
        ring.AddPoint(fLrx, fUly)
        ring.AddPoint(fLrx, fLry)
        ring.AddPoint(fUlx, fLry)
        
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        poly.AssignSpatialReference(srs)
        
        outDriver = ogr.GetDriverByName('GML')
        
        bboxFile = os.path.join(str(self.request.destination.name), 
                                name + '_' + srs.GetAuthorityCode(None) +'.gml')
        
        outDataSource = outDriver.CreateDataSource(bboxFile)
        outLayer = outDataSource.CreateLayer(bboxFile, geom_type=ogr.wkbPolygon)
        featureDefn = outLayer.GetLayerDefn()
        outFeature = ogr.Feature(featureDefn)
        outFeature.SetGeometry(poly)
        outLayer.CreateFeature(outFeature)
        outFeature = None
        outDataSource = None
        
    #---------------------------------------------------------------------------
    # computeScale
    #---------------------------------------------------------------------------
    def computeScale(self, ulx, uly, lrx, lry, srs, width, height):
        
        ulPoint = ogr.Geometry(ogr.wkbPoint)
        ulPoint.AddPoint(float(ulx), float(uly))
        ulPoint.AssignSpatialReference(srs)

        lrPoint = ogr.Geometry(ogr.wkbPoint)
        lrPoint.AddPoint(float(lrx), float(lry))
        lrPoint.AssignSpatialReference(srs)

        urPoint = ogr.Geometry(ogr.wkbPoint)
        urPoint.AddPoint(float(lrx), float(uly))
        urPoint.AssignSpatialReference(srs)
        
        xDist = ulPoint.Distance(urPoint)
        yDist = urPoint.Distance(lrPoint)

        xScale = xDist  / float(width)
        yScale = yDist / float(height)
        
        if self.logger:
            
            self.logger.info('Width, Height: '    + \
                             str(width)  + ', ' + str(height))

            self.logger.info('xDist, yDist: '    + \
                             str(xDist)  + ', ' + str(yDist))

            self.logger.info('X Scale, Y Scale: ' + \
                             str(xScale) + ', ' + str(yScale))
        
        return xScale, yScale        
                
    #---------------------------------------------------------------------------
    # constructSrs
    #---------------------------------------------------------------------------
    def constructSrs(self, srsString):
        
        srs = SpatialReference(str(srsString))  # str() in case it's unicode
        
        #---
        # The SRS can exist, but be invalid such that any method called on it
        # will raise an exception.  Use Fixup because it will either reveal
        # this error or potentially improve the object.
        #---
        try:
            srs.Fixup()
        
        except TypeError, e:
            
            raise RuntimeError('Invalid SRS object created for ' + srsString)

        if srs.Validate() != ogr.OGRERR_NONE:
            raise RuntimeError('Unable to construct valid SRS for ' + srsString)

        return srs
        
    #---------------------------------------------------------------------------
    # constructSrsFromIntCode
    #---------------------------------------------------------------------------
    @staticmethod
    def constructSrsFromIntCode(codeInt):
    
        return GeoRetriever.constructSrsFromCode('EPSG:' + str(codeInt))
        
    #---------------------------------------------------------------------------
    # constructSrsFromCode
    #---------------------------------------------------------------------------
    @staticmethod
    def constructSrsFromCode(codeStr):
    
        if GeoRetriever.SPECIAL_PROJECTIONS.has_key(codeStr):
            
            return GeoRetriever.SPECIAL_PROJECTIONS[codeStr]
            
        else:
            
            intCode = int(codeStr.split(':')[1])
            srs = SpatialReference()
            srs.ImportFromEPSG(intCode)
            return srs
    
    #---------------------------------------------------------------------------
    # expandByPercentage
    #---------------------------------------------------------------------------
    def expandByPercentage(self, ulx, uly, lrx, lry, srs, percentage = 10):
        
        ulPoint = ogr.Geometry(ogr.wkbPoint)
        ulPoint.AddPoint(float(ulx), float(uly))
        ulPoint.AssignSpatialReference(srs)

        lrPoint = ogr.Geometry(ogr.wkbPoint)
        lrPoint.AddPoint(float(lrx), float(lry))
        lrPoint.AssignSpatialReference(srs)

        urPoint = ogr.Geometry(ogr.wkbPoint)
        urPoint.AddPoint(float(lrx), float(uly))
        urPoint.AssignSpatialReference(srs)
        
        width  = abs(ulPoint.Distance(urPoint))
        height = abs(ulPoint.Distance(lrPoint))
        
        pct      = percentage / 100.0
        exWidth  = width * pct / 2.0
        exHeight = height * pct / 2.0
        
        exUlx = ulx - exWidth
        exUly = uly + exHeight
        exLrx = lrx + exWidth
        exLry = lry - exHeight
        
        return exUlx, exUly, exLrx, exLry
        
    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #
    # This method returns a list of SpatialReference supported by this 
    # request's end point.
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
         raise RuntimeError('This method must be overridden by a subclass.')
                    
    #---------------------------------------------------------------------------
    # getOutFileName
    #---------------------------------------------------------------------------
    def getOutFileName(self, baseName, ext):
        
        count   = 1
        outName = os.path.join(self.request.destination.name, baseName + ext)

        while os.path.exists(outName):
            
            outName = os.path.join(self.request.destination.name, \
                                   baseName + '-' + str(count) + ext)
            
            count += 1
        
        return outName
        
    #---------------------------------------------------------------------------
    # getRetrievalSRS
    #---------------------------------------------------------------------------
    def getRetrievalSRS(self, reqSRS):

        #---
        # Minimize data transformation.  Ultimately, the data must end up in the
        # output SRS.  If the end point supports it, use it.
        #---
        if self.isCodeSupported(self.outSRS):
            return self.outSRS

        #---
        # The output SRS is unsuppported.  Try the request SRS because that will
        # only require the output to be transformed.
        #---
        if self.isCodeSupported(self.requestSRS):
            return self.requestSRS

        #---
        # Neither the output nor the request SRS are supported.  Try the
        # ubiquitous geographic projection.
        #---
        if self.isCodeSupported(GeoRetriever.GEOG_4326):
            return GeoRetriever.GEOG_4326

        #---
        # Still, nothing is supported.  Go through the supported SRSs, and
        # use the first one that is not deemed a special projection by
        # GeoRetriever.  Special projections are those that do not easily
        # tranform to Albers.
        #---
        finalEpsg = None

        for srs in self.supportedSRSs:
            if not self.isSpecialProjection(srs):
                return srs

        # Still haven't found one, use whatever is first.
        return self.supportedSRSs[0]

    #---------------------------------------------------------------------------
    # getXformCmd
    #---------------------------------------------------------------------------
    def getXformCmd(self, inFile, outFile, fileType = None):

        bboxOrds = self.transformBbox(self.retrievalUlx, 
                                      self.retrievalUly, 
                                      self.retrievalLrx, 
                                      self.retrievalLry, 
                                      self.retrievalSRS, 
                                      self.outSRS)
        
        cmd = 'gdalwarp -multi ' + \
              '-t_srs "' + \
              self.outSRS.ExportToProj4() + '" "' + \
              inFile + '" "' + \
              outFile + '" ' + \
              '-te_srs "' + \
              self.outSRS.ExportToProj4() + '" ' + \
              '-te ' + \
              str(bboxOrds[0]) + ' ' + \
              str(bboxOrds[3]) + ' ' + \
              str(bboxOrds[2]) + ' ' + \
              str(bboxOrds[1])

        return cmd
        
    #---------------------------------------------------------------------------
    # isCodeSupported
    #---------------------------------------------------------------------------
    def isCodeSupported(self, inSrs):

        for srs in self.supportedSRSs:
            if srs.IsSame(inSrs):
                return True

        return False
        
    #---------------------------------------------------------------------------
    # isSpecialProjection
    #---------------------------------------------------------------------------
    def isSpecialProjection(self, inSrs):

        for srs in GeoRetriever.SPECIAL_PROJECTIONS.values():
            if srs.IsSame(inSrs):
                return True

        return False
        
    #---------------------------------------------------------------------------
    # mosaic
    #---------------------------------------------------------------------------
    def mosaic(self, tifs, outFile, keepConstituents = False, \
               noDataValue = None):
        
        if self.logger:
            self.logger.info('ModisRetriever.mosaic()...')
            
        if len(tifs) == 1:
            
            shutil.move(tifs[0], outFile)
            
        else:
            
            inTifs = ''
        
            for tif in tifs:
                inTifs += ' "' + tif + '" '
            
            cmd = settings.GDAL_MERGE

            if noDataValue:
                cmd += ' -n ' + str(noDataValue)

            cmd += ' -o "' + outFile + '" ' + inTifs
        
            if self.logger:
                self.logger.info('cmd = ' + cmd)
            
            result = os.system(cmd)

            if result != 0: 
                raise RuntimeError('gdal_merge failed with result: ' + \
                                   str(result) + \
                                   '.  The command was: ' + cmd)
    
            # Remove the consituent tifs.
            if not keepConstituents:
                for tif in tifs:
                    os.remove(tif)
        
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

    #---------------------------------------------------------------------------
    # transformBbox
    #---------------------------------------------------------------------------
    def transformBbox(self, ulx, uly, lrx, lry, srs, outSRS):

        if srs.IsSame(outSRS):
            return ulx, uly, lrx, lry
            
        #---
        # When multiple images are collected from various end points, as 
        # Wrangler does, ensure their extents and scales match when finally
        # transformed to the output SRS.  To achieve this, transform all four
        # corners of bounding boxes, and use the extremes of the ordinates to
        # construct the upper-left and lower-right output corners.
        #---
        xform = CoordinateTransformation(srs, outSRS)

        fUlx = float(ulx)
        fUly = float(uly)
        fLrx = float(lrx)
        fLry = float(lry)

        xUl = xform.TransformPoint(fUlx, fUly)
        xLr = xform.TransformPoint(fLrx, fLry)
        xLl = xform.TransformPoint(fUlx, fLry)
        xUr = xform.TransformPoint(fLrx, fUly)

        xValues = [xLl[0], xLr[0], xUl[0], xUr[0]]
        yValues = [xLl[1], xLr[1], xUl[1], xUr[1]]
        
        minX = min(xValues)
        maxX = max(xValues)
        minY = min(yValues)
        maxY = max(yValues)
        
        return minX, maxY, maxX, minY

    #---------------------------------------------------------------------------
    # xformOutput
    #---------------------------------------------------------------------------
    def xformOutput(self, inFile, outFile = None, fileType = None, \
                    keepOriginal = False):

        hasOutFile = True if outFile != None else False
        
        if not outFile:

            path, fullName = os.path.split(inFile)
            name, ext      = os.path.splitext(fullName)
            outFile        = os.path.join(path, name + '-warpedToOutCrs' + ext)

        cmd = self.getXformCmd(inFile, outFile, fileType)
        
        if self.logger:
            self.logger.info('Command:  ' + cmd)

        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('Failed to transform layer to output SRS.')
          
        if status == 0 and not hasOutFile:

            if keepOriginal:
                
                saveFile = os.path.join(path, name + '-untransformed' + ext)
                shutil.copy(inFile, saveFile)

            shutil.move(outFile, inFile)
            

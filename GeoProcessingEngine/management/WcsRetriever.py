
import logging
import math
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from osgeo import ogr

from owslib.wcs import WebCoverageService

from django.conf import settings

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class WcsRetriever
#
# https://pcjericks.github.io/py-gdalogr-cookbook/geometry.html
# https://landfire.cr.usgs.gov/arcgis/services/Landfire/US_130/MapServer/WCSServer?request=GetCapabilities&service=WCS
#-------------------------------------------------------------------------------
class WcsRetriever(GeoRetriever):

    #---------------------------------------------------------------------------
    # __init__ 
    #---------------------------------------------------------------------------
    def __init__(self, request, logger = None):

        owslibLog = logging.getLogger('owslib')
        owslibLog.setLevel(logging.DEBUG)

        self.service = WebCoverageService(request.endPoint.url, 
                                          request.endPoint.version)
        
        if not request.endPoint.serviceId in self.service.contents:

            raise RuntimeError('Unable to find ' + \
                               request.endPoint.serviceId + \
                               ' for ' + request.endPoint.name + \
                               ' at '  + request.endPoint.url  + \
                               ' service contents: '   + \
                               str(self.service.contents))
        
        super(WcsRetriever, self).__init__(request, logger)

    #---------------------------------------------------------------------------
    # computeHeightWidth
    #---------------------------------------------------------------------------
    def computeHeightWidth(self, ulx, uly, lrx, lry, srs, contents):

        # Get the native scale.  Assume pixels are square.
        xScale, yScale, nativeSRS = self.computeNativeScale(contents)

        if xScale == 0 or yScale == 0:
            raise RuntimeError('Pixel scale is 0.')

        if math.fabs(xScale - yScale) > 0.0002:
            raise RuntimeError('Pixels are not square.  (' + str(xScale) + \
                               ', ' + str(yScale) + ')')
                               
        natScale = xScale # One var. because pixels are square.
        
        #---
        # Get the retrieval bbox in the native CRS, so the native scale is in
        # the same units.
        #---
        natUlx, natUly, natLrx, natLry = \
            self.transformBbox(ulx, uly, lrx, lry, srs, nativeSRS)
                                                            
        # Compute the native bbox's x and y distance.
        natUl = ogr.Geometry(ogr.wkbPoint)
        natUl.AddPoint(float(natUlx), float(natUly))
        natUl.AssignSpatialReference(nativeSRS)
        
        natLr = ogr.Geometry(ogr.wkbPoint)
        natLr.AddPoint(float(natLrx), float(natLry))
        natLr.AssignSpatialReference(nativeSRS)
        
        natUr = ogr.Geometry(ogr.wkbPoint)
        natUr.AddPoint(float(natLrx), float(natUly))
        natUr.AssignSpatialReference(srs)

        natX_Dist = natUl.Distance(natUr)
        natY_Dist = abs(natLr.Distance(natUr))

        if natX_Dist < 0 or natY_Dist < 0:
            raise RuntimeError('Distance should be > 0.')
            
        if self.logger:
            
            self.logger.info('Native X Distance: ' + str(natX_Dist))
            self.logger.info('Native Y Distance: ' + str(natY_Dist))
            
        return natY_Dist / natScale, natX_Dist / natScale
        
        #---
        # We must limit the data requested.  If the native scale exceeds them,
        # compute new samples and lines, while maintaining square pixels, until
        # both are below the maximums.
        #---        
        # maxSamples = settings.WRANGLE_SETTINGS['maxSamples']
        # maxLines   = settings.WRANGLE_SETTINGS['maxLines']
        # samples    = 0
        # lines      = 0
        # maxX_Scale = math.ceil(natX_Dist / maxSamples) # Largest scale that
        # maxY_Scale = math.ceil(natY_Dist / maxLines)   # covers the distance.
        # maxScale   = max(maxX_Scale, maxY_Scale)       # Use largest pixel size.
        # maxScale   = max(natScale, maxScale)           # Max <= native scale.
        # scale      = natScale
        #
        # while scale <= maxScale:
        #
        #     samples = math.ceil(float(natX_Dist) / scale)
        #     lines   = math.ceil(float(natY_Dist) / scale)
        #
        #     if samples <= maxSamples and lines <= maxLines:
        #         break
        #
        #     scale = math.ceil(scale + 0.5)
        #
        # if self.logger:
        #     self.logger.info('WcsRetriever.computeHeightWidth: lines = ' +
        #                      str(lines) + ', samples = ' + str(samples))
        #
        # return lines, samples

    #---------------------------------------------------------------------------
    # computeNativeScale
    #---------------------------------------------------------------------------
    def computeNativeScale(self, contents):

        # Find the bounding box in the native SRS.
        bbox      = None
        nativeSRS = None

        for bboxDict in contents.boundingboxes:
            
            if 'nativeSrs' in bboxDict and 'bbox' in bboxDict:

                nativeSRS = \
                    GeoRetriever.constructSrsFromCode(bboxDict['nativeSrs'])
                
                bbox = bboxDict['bbox']
                break
        
        if not bbox:
            raise RuntimeError('Unable to find native bounding box.')

        if not nativeSRS:
            raise RuntimeError('Unable to find native SRS.')
            
        # Get the image dimensions.
        lows  = contents.grid.lowlimits
        highs = contents.grid.highlimits

        dim1ImageDist = math.fabs(float(highs[0]) - float(lows[0]))
        dim2ImageDist = math.fabs(float(highs[1]) - float(lows[1]))

        #---
        # Points will ignore strings given to the srid parameter.
        # Bbox is minX, minY, maxX, maxY
        #---
        xScale, yScale = self.computeScale(bbox[0],       \
                                           bbox[3],       \
                                           bbox[2],       \
                                           bbox[1],       \
                                           nativeSRS,     \
                                           dim1ImageDist, \
                                           dim2ImageDist)
                                           
        return xScale, yScale, nativeSRS
        
    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):

        # Use a dict, to avoid storing duplicates.
        srsDict = {}

        for k, v in self.service.contents.iteritems():

            for crs in v.supportedCRS:

                code = crs.getcode()

                if code not in srsDict:
                    srsDict[code] = GeoRetriever.constructSrsFromCode(code)

        return srsDict.values()
                    
    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        contents    = self.service.contents[self.request.endPoint.serviceId]
        outFileName = self.getOutFileName(contents.title, '.tif')
        return {outFileName: [outFileName]}
        
    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        exUlx, exUly, exLrx, exLry =                   \
            self.expandByPercentage(self.retrievalUlx, \
                                    self.retrievalUly, \
                                    self.retrievalLrx, \
                                    self.retrievalLry, \
                                    self.retrievalSRS, \
                                    10)
                                                             
        self.bBoxToVector(exUlx, 
                          exUly, 
                          exLrx, 
                          exLry, 
                          self.retrievalSRS, 
                          'expanded')

        contents = self.service.contents[self.request.endPoint.serviceId]
        
        # height, width = self.computeHeightWidth(exUlx,             \
        #                                         exUly,             \
        #                                         exLrx,             \
        #                                         exLry,             \
        #                                         self.retrievalSRS, \
        #                                         contents)
        
        bboxOGC = [exUlx, exLry, exLrx, exUly]
        crs     = 'EPSG:' + str(self.retrievalSRS.GetAuthorityCode(None))

        # url = self.service.getCoverage(self.request.endPoint.serviceId, \
        #                                bboxOGC,                         \
        #                                None,                            \
        #                                'GeoTIFF',                       \
        #                                crs,                             \
        #                                width,                           \
        #                                height)

        print '**** CAN I DO THIS WITH RESX RESY INSTEAD OF HEIGHT WIDTH? ****'
        url = self.service.getCoverage(self.request.endPoint.serviceId, \
                                       bboxOGC,                         \
                                       None,                            \
                                       'GeoTIFF',                       \
                                       crs,                             \
                                       None,                            \
                                       None,                            \
                                       30.0, 30.0)
    
        # Write the layer
        if self.logger:
            
            self.logger.info(url.geturl())
            self.logger.info('Writing layer ...')
    
        fOut = open(constituentFileName, 'w')
        fOut.write(url.read())
        fOut.close()

        #---
        # Search for an error.  The output file will not parse, if
        # it is a GeoTiff.
        #---
        try:
            xml      = minidom.parse(constituentFileName)
            itemList = xml.getElementsByTagName('ServiceException') 

            if len(itemList):
                raise RuntimeError(itemList[0].childNodes[0].data)
            
        except ExpatError:
            
            # No ServiceException; therefore, no WCS errors.
            pass
                  
        self.xformOutput(constituentFileName, None, None, False)

        return constituentFileName

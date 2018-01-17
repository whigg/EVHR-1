
import logging
import os
import shutil
import tempfile
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from owslib.crs import Crs
from owslib.wms import WebMapService
from owslib.wms import WMSCapabilitiesReader

from django.conf import settings

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class WmRetriever
#-------------------------------------------------------------------------------
class WmsRetriever(GeoRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger = None):

        owslibLog = logging.getLogger('owslib')
        owslibLog.setLevel(logging.DEBUG)

        self.service = WebMapService(request.endPoint.url, \
                                     version = request.endPoint.version)

        if not request.endPoint.serviceId in self.service.contents:

            raise RuntimeError('Unable to find ' + \
                               request.endPoint.serviceId + \
                               ' for ' + request.endPoint.name + \
                               ' at '  + request.endPoint.url  + \
                               ' service contents: '   + \
                               str(self.service.contents))

        super(WmsRetriever, self).__init__(request, logger)

    #---------------------------------------------------------------------------
    # chooseAvailableFormat
    #---------------------------------------------------------------------------
    def chooseAvailableFormat(self):
        
        PREFERRED_FORMAT = 'image/tiff'
        chosenFormat     = None
        
        for op in self.service.operations:

            if op.name.lower() == 'getmap':
                
                formats = op.formatOptions
                
                for f in formats:
                    if f == PREFERRED_FORMAT:
                        chosenFormat = PREFERRED_FORMAT
                        
                if chosenFormat == None:
                    chosenFormat = formats[0]
                    
        if chosenFormat == None:
            raise RuntimeError('Unable to identify any image formats.')
            
        return chosenFormat

    #---------------------------------------------------------------------------
    # computeHeightWidth
    #---------------------------------------------------------------------------
    def computeHeightWidth(self, bbox):

        # Try to find the maximum allowable scale.  This might not be given.
        if self.scaleHint == None:

            scale = settings.WRANGLE_SETTINGS['defaultScaleInMeters']
            
        else:
            scale = float(self.scaleHint['max'])
                    
        height, width = GeoUtils.computeHeightWidth(scale, scale, bbox, 
                                                    self.logger)
        
        if height > self.maxHeight or width > self.maxWidth:

            maxScale = GeoUtils.computeMaxScale(bbox, 
                                                self.maxWidth, 
                                                self.maxHeight, 
                                                self.logger)

            height, width = GeoUtils.computeHeightWidth(maxScale, 
                                                        maxScale, 
                                                        bbox, 
                                                        self.logger)

        return height, width

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
    # findTag
    #---------------------------------------------------------------------------
    def findTag(self, tag, tree):
        
        children = tree.getchildren()
        
        for child in children:
            if child.tag.endswith(tag):
                return child
        
    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        contents    = self.service.contents[self.request.endPoint.serviceId]
        outFileName = self.getOutFileName(contents.title, '.tif')
        return {outFileName: [outFileName]}
        
    #---------------------------------------------------------------------------
    # parseMax
    #---------------------------------------------------------------------------
    # def parseMax(self, url, version):
    #
    #     #---
    #     # Version 1.3.0, the version that has the maximums, might include
    #     # namespaces with the tags, making it difficult to find specific ones.
    #     #---
    #     reader       = WMSCapabilitiesReader(version, url)
    #     capabilities = reader.read(url)
    #     serviceElem  = self.findTag('Service', capabilities)
    #     maxHeight    = self.findTag('MaxHeight', serviceElem).text
    #     maxWidth     = self.findTag('MaxWidth', serviceElem).text
    #
    #     return int(maxHeight), int(maxWidth)
        
    #---------------------------------------------------------------------------
    # runOnePredFile
    #---------------------------------------------------------------------------
    def runOnePredFile(self, constituentFileName, fileList):
        
        exUlx, exUly, exLrx, exLry =                   \
            self.expandByPercentage(self.retrievalUlx, \
                                    self.retrievalUly, \
                                    self.retrievalLrx, \
                                    self.retrievalLry, \
                                    self.retrievalSRS, \
                                    150)

        contents = self.service.contents[self.request.endPoint.serviceId]
        
        height, width = self.computeHeightWidth(exUlx,             \
                                                exUly,             \
                                                exLrx,             \
                                                exLry,             \
                                                self.retrievalSRS, \
                                                contents)

        bboxOGC = [exUlx, exLry, exLrx, exUly]
        crs     = 'EPSG:' + str(self.retrievalSRS.GetAuthorityCode(None))

        url = self.service.getmap([self.endPoint.serviceId],     \
                                   None,                         \
                                   crs,                          \
                                   bboxOGC,                      \
                                   self.chooseAvailableFormat(), \
                                   (width, height))

        fOut = open(constituentFileName, 'w') 
        fOut.write(url.read())
        fOut.close()

        # Search for an error.
        try:
            xml      = minidom.parse(constituentFileName)
            itemList = xml.getElementsByTagName('ServiceException') 

            if len(itemList):
                raise RuntimeError(itemList[0].childNodes[0].data)
            
        except ExpatError:
            
            # No ServiceException; therefore, no WMS errors.
            pass
            
        #---
        # WMS returns images without geographic information.  Convert the
        # WMS image to GeoTiff.
        #---
        self.wmsToGeoTiff(constituentFileName, \
                          exUlx,               \
                          exUly,               \
                          exLrx,               \
                          exLry,               \
                          self.retrievalSRS)

        self.xformOutput(constituentFileName, None, None, True)

        return constituentFileName

    #---------------------------------------------------------------------------
    # wmsToGeoTiff
    #---------------------------------------------------------------------------
    def wmsToGeoTiff(self, outFileName, ulx, uly, lrx, lry, srs):
        
        path, name  = os.path.split(outFileName)
        wmsFileName = os.path.join(tempfile.gettempdir(), name)
        shutil.move(outFileName, wmsFileName)
        
        cmd = 'gdal_translate '                           + \
              '-a_srs EPSG:' + srs.GetAuthorityCode(None) + \
              ' -a_ullr '                                 + \
              str(ulx) + ' '                              + \
              str(uly) + ' '                              + \
              str(lrx) + ' '                              + \
              str(lry) + ' '                              + \
              '"' + wmsFileName + '" "'                   + \
              outFileName + '"'
              
        status = os.system(cmd)
        
        if status != 0:
            raise RuntimeError('Failed to translate WMS image into GeoTiff.')



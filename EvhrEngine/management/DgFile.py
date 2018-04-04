import os
from osgeo import gdal
from osgeo.osr import SpatialReference
import xml.etree.ElementTree as ET
from datetime import datetime

#-------------------------------------------------------------------------------
# class DgFile
#-------------------------------------------------------------------------------
class DgFile:

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, fileName):

        # Check that the file is NITF or TIFF
        extension = os.path.splitext(fileName)[1]
        self.fileName = fileName
        self.xmlFileName = self.fileName.replace(extension, '.xml')

        if extension != '.ntf' and extension != '.tif':
            
            raise RuntimeError('{} is not a NITF or TIFF file'. \
                               format(self.fileName))

        if not os.path.isfile(self.fileName):
            raise RuntimeError('{} does not exist'.format(self.fileName))

        dataset = gdal.Open(self.fileName, gdal.GA_ReadOnly)

        if not dataset:
            raise RuntimeError("Could not open {}".format(self.fileName))

        # firstLineTime
        t = dataset.GetMetadataItem('NITF_CSDIDA_TIME')
        self.firstLineTime = datetime.strptime(t, "%Y%m%d%H%M%S")

        # meanSunElevation
        self.meanSunElevation = \
            float(dataset.GetMetadataItem('NITF_CSEXRA_SUN_ELEVATION'))

        # specType
        self.specTypeCode = dataset.GetMetadataItem('NITF_CSEXRA_SENSOR')

        # sensor
        self.sensor = dataset.GetMetadataItem('NITF_PIAIMC_SENSNAME')

        # year
        self.year = dataset.GetMetadataItem('NITF_CSDIDA_YEAR')

        # extent / SRS
        if dataset.GetProjection():

            geoTransform = dataset.GetGeoTransform()
            self.ulx = geoTransform[0]
            self.uly = geoTransform[3]
            self.lrx = self.ulx + geoTransform[1] * dataset.RasterXSize
            self.lry = self.uly + geoTransform[5] * dataset.RasterYSize
            self.srs = SpatialReference(dataset.GetProjection())

        elif dataset.GetGCPProjection():

            self.ulx = dataset.GetGCPs()[0].GCPX
            self.uly = dataset.GetGCPs()[0].GCPY
            self.lrx = dataset.GetGCPs()[2].GCPX
            self.lry = dataset.GetGCPs()[2].GCPY
            self.srs = SpatialReference(dataset.GetGCPProjection())

        else:
            raise RuntimeError("Could not get projection or corner coordinates")

        # numBands
        self.numBands = dataset.RasterCount

        # These data member require the XML file counterpart to the TIF.
        self.imdTag = None
        
        if os.path.isfile(self.xmlFileName):

            # bandNameList #* added this for getBand --> [BAND_B, BAND_R, etc...]
            tree = ET.parse(self.xmlFileName)
            self.imdTag = tree.getroot().find('IMD')
        
            self.bandNameList = \
                [n.tag for n in self.imdTag if n.tag.startswith('BAND_')]

        else:
            # raise RuntimeError('{} does not exist'.format(self.xmlFileName))
            print 'Warning: ' + self.xmlFileName + ' does not exist.'

    #---------------------------------------------------------------------------
    # isMultispectral()
    #---------------------------------------------------------------------------
    def isMultispectral(self):

        return self.specTypeCode == 'MS'

    #---------------------------------------------------------------------------
    # isPanchromatic()
    #---------------------------------------------------------------------------
    def isPanchromatic(self):

        return self.specTypeCode == 'PAN'

    #---------------------------------------------------------------------------
    # getBand()
    #---------------------------------------------------------------------------
    def getBand(self, outputDir, bandName):

        gdalBandIndex = int(self.bandNameList.index(bandName)) + 1

        extension = os.path.splitext(self.fileName)[1]
        
        baseName = os.path.basename(self.fileName.replace(extension, \
                                            '_b{}.tif'.format(gdalBandIndex)))

        tempBandFile = os.path.join(outputDir, baseName)

        if not os.path.exists(tempBandFile):

            cmd = 'gdal_translate'                      + \
                  ' -b {}'.format(gdalBandIndex)        + \
                  ' -a_nodata 0'                        + \
                  ' -mo "bandName={}"'.format(bandName) + \
                  ' ' + self.fileName                   + \
                  ' ' + tempBandFile

            os.system(cmd)

        return tempBandFile

    #---------------------------------------------------------------------------
    # abscalFactor()
    #---------------------------------------------------------------------------
    def abscalFactor(self, bandName):

        if self.imdTag and \
           isinstance(bandName, str) and \
           bandName.startswith('BAND_'):

            return float(self.imdTag.find(bandName).find('ABSCALFACTOR').text)

        else:
            raise RuntimeError('Could not retrieve abscal factor.')

    #---------------------------------------------------------------------------
    # effectiveBandwidth()
    #---------------------------------------------------------------------------
    def effectiveBandwidth(self, bandName):

        if self.imdTag and \
           isinstance(bandName, str) and \
           bandName.startswith('BAND_'):

            return float(self.imdTag.      \
                           find(bandName). \
                           find('EFFECTIVEBANDWIDTH').text)

        else:
            raise RuntimeError('Could not retrieve effective bandwidth.')
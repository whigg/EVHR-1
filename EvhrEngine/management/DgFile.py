import os
from osgeo import gdal
from osgeo.osr import SpatialReference
import xml.etree.ElementTree as ET
from datetime import datetime

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
            raise RuntimeError('{} is not a NITF or TIFF file'.format\
                                                                (self.fileName))

        if not os.path.isfile(self.fileName):
            raise RuntimeError('{} does not exist'.format(self.fileName))

        if not os.path.isfile(self.xmlFileName):
            raise RuntimeError('{} does not exist'.format(self.xmlFileName))


        dataset = gdal.Open(self.fileName, gdal.GA_ReadOnly)

        if not dataset:
            raise RuntimeError("Could not open {}".format(self.fileName))

        tree = ET.parse(self.xmlFileName)

##        # abscalFactors
##        elem = tree.findall('.//ABSCALFACTOR')
##        self.abscalFactors = [i.text for i in elem]
##
##        # effectiveBandwidths
##        elem = tree.findall('.//EFFECTIVEBANDWIDTH')
##        self.effectiveBandwidths = [i.text for i in elem]

        # firstLineTime
        t = dataset.GetMetadataItem('NITF_CSDIDA_TIME')
        self.firstLineTime = datetime.strptime(t, "%Y%m%d%H%M%S")

        # bandNameList #* added this for getBand --> [BAND_B, BAND_R, etc...]
        elem = tree.getroot().find('IMD')
        self.bandNameList = [node.tag for node in elem if node.tag. \
                                                            startswith('BAND_')]

        # meanSunElevation
        self.meanSunElevation = float(dataset.GetMetadataItem \
                                                ('NITF_CSEXRA_SUN_ELEVATION'))

        # specType
        self.specTypeCode = dataset.GetMetadataItem('NITF_CSEXRA_SENSOR')

        # sensor
        self.sensor = dataset.GetMetadataItem('NITF_PIAIMC_SENSNAME')

        # year
        self.year = dataset.GetMetadataItem('NITF_CSDIDA_YEAR')

        # extent / SRS
        if dataset.GetProjection():
            self.srs    =   SpatialReference(dataset.GetProjection())

            geoTransform    =   dataset.GetGeoTransform()
            self.ulx    =   geoTransform[0]
            self.uly    =   geoTransform[3]
            self.lrx    =   self.ulx + geoTransform[1] * dataset.RasterXSize
            self.lry    =   self.uly + geoTransform[5] * dataset.RasterYSize

        elif dataset.GetGCPProjection():
            self.srs    =   SpatialReference(dataset.GetGCPProjection())

            self.ulx    =   dataset.GetGCPs()[0].GCPX
            self.uly    =   dataset.GetGCPs()[0].GCPY
            self.lrx    =   dataset.GetGCPs()[2].GCPX
            self.lry    =   dataset.GetGCPs()[2].GCPY

        else:
            raise RuntimeError("Could not get projection or corner coordinates")

        # numBands
        self.numBands   =   dataset.RasterCount


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
                                            'b{}.tif'.format(gdalBandIndex)))

        tempBandFile = os.path.join(outputDir, baseName)

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

        if isinstance(bandName, str) and bandName.startswith('BAND_'):

            tree = ET.parse(self.xmlFileName).getroot().find('IMD')
            abscalFactor = float(tree.find(bandName).find('ABSCALFACTOR').text)
            return abscalFactor

        else:
            raise RuntimeError('Band name {} not valid. Could not retrieve \
                                                abscal factor'.format(bandName))


    #---------------------------------------------------------------------------
    # effectiveBandwidth()
    #---------------------------------------------------------------------------
    def effectiveBandwidth(self, bandName):

        if isinstance(bandName, str) and bandName.startswith('BAND_'):

            tree = ET.parse(self.xmlFileName).getroot().find('IMD')
            effectiveBandwidth = float(tree.find(bandName).find \
                                                    ('EFFECTIVEBANDWIDTH').text)
            return effectiveBandwidth

        else:
            raise RuntimeError('Band name {} not valid. Could not retrieve \
                                        effective bandwidth'.format(bandName))
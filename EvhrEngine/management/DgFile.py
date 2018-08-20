
from datetime import datetime
import os
import subprocess
import xml.etree.ElementTree as ET

from EvhrEngine.management.GdalFile import GdalFile
from EvhrEngine.management.SystemCommand import SystemCommand

#-------------------------------------------------------------------------------
# class DgFile
#
# This class represents a Digital Globe file.  It is a single NITF file or a
# GeoTiff with an XML counterpart.  It is uniqure because of the metadata tags
# within.
#-------------------------------------------------------------------------------
class DgFile(GdalFile):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, fileName, logger = None):

        # Check that the file is NITF or TIFF
        extension = os.path.splitext(fileName)[1]

        if extension != '.ntf' and extension != '.tif':
            raise RuntimeError('{} is not a NITF or TIFF file'.format(fileName))

        # Ensure the XML file exists.
        xmlFileName = fileName.replace(extension, '.xml')

        if not os.path.isfile(xmlFileName):
            raise RuntimeError('{} does not exist'.format(xmlFileName))

        self.xmlFileName = xmlFileName
        
        # Initialize the base class.
        super(DgFile, self).__init__(fileName, logger)

        # These data member require the XML file counterpart to the TIF.
        tree = ET.parse(self.xmlFileName)
        self.imdTag = tree.getroot().find('IMD')
        
        if self.imdTag is None:
            
            raise RuntimeError('Unable to locate the "IMD" tag in ' + \
                               self.xmlFileName)
    
        # bandNameList #* added this for getBand --> [BAND_B, BAND_R, etc...]
        self.bandNameList = \
            [n.tag for n in self.imdTag if n.tag.startswith('BAND_')]

        # firstLineTime
        t = self.dataset.GetMetadataItem('NITF_CSDIDA_TIME')
        self.firstLineTime = None
        
        if t:
            self.firstLineTime = datetime.strptime(t, "%Y%m%d%H%M%S")
        
        # meanSunElevation
        self.meanSunElevation = \
            float(self.dataset.GetMetadataItem('NITF_CSEXRA_SUN_ELEVATION'))

        # specType
        self.specTypeCode = self.dataset.GetMetadataItem('NITF_CSEXRA_SENSOR')

        # sensor
        self.sensor = self.dataset.GetMetadataItem('NITF_PIAIMC_SENSNAME')

        # year
        self.year = self.dataset.GetMetadataItem('NITF_CSDIDA_YEAR')

        # numBands
        self.numBands = self.dataset.RasterCount

    #---------------------------------------------------------------------------
    # abscalFactor()
    #---------------------------------------------------------------------------
    def abscalFactor(self, bandName):

        if isinstance(bandName, str) and bandName.startswith('BAND_'):

            return float(self.imdTag.find(bandName).find('ABSCALFACTOR').text)

        else:
            raise RuntimeError('Could not retrieve abscal factor.')

    #---------------------------------------------------------------------------
    # effectiveBandwidth()
    #---------------------------------------------------------------------------
    def effectiveBandwidth(self, bandName):

        if isinstance(bandName, str) and bandName.startswith('BAND_'):

            return float(self.imdTag.      \
                           find(bandName). \
                           find('EFFECTIVEBANDWIDTH').text)

        else:
            raise RuntimeError('Could not retrieve effective bandwidth.')
            
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
                  ' -strict'                            + \
                  ' -mo "bandName={}"'.format(bandName) + \
                  ' ' + self.fileName                   + \
                  ' ' + tempBandFile

            sCmd = SystemCommand(cmd, self.fileName, self.logger)

            if sCmd.returnCode:
                tempBandFile = None
                
        return tempBandFile

    #---------------------------------------------------------------------------
    # getCatalogId
    #---------------------------------------------------------------------------
    def getCatalogId(self):
        
        return self.imdTag.findall('./IMAGE/CATID')[0].text
            
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

        
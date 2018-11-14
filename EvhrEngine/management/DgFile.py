
from datetime import datetime
import os
import subprocess
import shutil
import tempfile
from xml.dom import minidom
import xml.etree.ElementTree as ET

from osgeo.osr import SpatialReference

from django.conf import settings

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

        # If srs from GdalFile is empty, set srs, and get coords from the .xml
        if not self.srs:

            self.srs = SpatialReference()
            self.srs.ImportFromEPSG(4326)
              
            bandTag = [n for n in self.imdTag.getchildren() if \
                n.tag.startswith('BAND_')][0] # all bands will have same extent

            self.ulx = min(float(bandTag.find('LLLON').text), \
                                          float(bandTag.find('ULLON').text))

            self.uly = max(float(bandTag.find('ULLAT').text), \
                                          float(bandTag.find('URLAT').text))

            self.lrx = max(float(bandTag.find('LRLON').text), \
                                          float(bandTag.find('URLON').text))

            self.lry = min(float(bandTag.find('LRLAT').text), \
                                          float(bandTag.find('LLLAT').text))

            GdalFile.validateCoordinates(self) # Lastly, validate coordinates

        # bandNameList
        try:
            self.bandNameList = \
                 [n.tag for n in self.imdTag if n.tag.startswith('BAND_')]
        except:
            self.bandNameList = None
    
        # numBands
        try:
            self.numBands = self.dataset.RasterCount

        except:
            self.numBands = None
            
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
    # firstLineTime()
    #---------------------------------------------------------------------------
    def firstLineTime(self):

        try:
            t = self.dataset.GetMetadataItem('NITF_CSDIDA_TIME')
            if t is not None:
                return datetime.strptime(t, "%Y%m%d%H%M%S")
            else:    
                t = self.imdTag.find('IMAGE').find('FIRSTLINETIME').text
                return datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            return None

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
        
        # Copy scene .xml to accompany the extracted .tif (needed for dg_mosaic) 
        shutil.copy(self.xmlFileName, tempBandFile.replace('.tif', '.xml'))        

        return tempBandFile

    #---------------------------------------------------------------------------
    # getBandName()
    #---------------------------------------------------------------------------
    def getBandName(self):
        
        try:
            return self.dataset.GetMetadataItem('bandName')
        except:
            return None

    #---------------------------------------------------------------------------
    # getCatalogId()
    #---------------------------------------------------------------------------
    def getCatalogId(self):
        
        return self.imdTag.findall('./IMAGE/CATID')[0].text

    #---------------------------------------------------------------------------
    # getPairName
    #---------------------------------------------------------------------------
    def getPairName(self):
        
        tempClipFile = tempfile.mkstemp()[1]
        
        cmd = 'ogr2ogr '                                         + \
              '-f "GML" '                                        + \
              '--debug on '                                      + \
              '-where "S_FILEPATH=' + '"' + self.fileName + '" ' + \
              ' "' + tempClipFile + '" '                         + \
              ' "' + settings.FOOTPRINTS_FILE + '" '

        import pdb
        pdb.set_trace()

        sCmd = SystemCommand(cmd, None, self.logger)
        xml = minidom.parse(tempClipFile)
        features = xml.getElementsByTagName('gml:pairname')
        
    #---------------------------------------------------------------------------
    # getStripName()
    #---------------------------------------------------------------------------
    def getStripName(self):
        
        try:
            if self.specTypeCode() == 'MS': prodCode = 'M1BS'
            else: prodCode = 'P1BS'
            dateStr = '{}{}{}'.format(self.year(),                             \
                                     str(self.firstLineTime().month).zfill(2), \
                                         str(self.firstLineTime().day).zfill(2))

            return '{}_{}_{}_{}'.format(self.sensor(), dateStr, prodCode,      \
                                                            self.getCatalogId())

        except:
            return None   
            
    #---------------------------------------------------------------------------
    # isMultispectral()
    #---------------------------------------------------------------------------
    def isMultispectral(self):

        return self.specTypeCode() == 'MS'

    #---------------------------------------------------------------------------
    # isPanchromatic()
    #---------------------------------------------------------------------------
    def isPanchromatic(self):

        return self.specTypeCode() == 'PAN'

    #---------------------------------------------------------------------------
    # meanSunElevation()
    #---------------------------------------------------------------------------
    def meanSunElevation(self):
    
        try: 
            mse = self.dataset.GetMetadataItem('NITF_CSEXRA_SUN_ELEVATION')
            if mse is None:
                mse = self.imdTag.find('IMAGE').find('MEANSUNEL').text

            return float(mse)

        except:
            return None
      
    #---------------------------------------------------------------------------
    # sensor()
    #---------------------------------------------------------------------------
    def sensor(self):

        try:
            sens = self.dataset.GetMetadataItem('NITF_PIAIMC_SENSNAME')
            if sens is None:
                sens = self.imdTag.find('IMAGE').find('SATID').text

            return sens

        except:
	    return None

    #---------------------------------------------------------------------------
    # setBandName()
    #---------------------------------------------------------------------------
    def setBandName(self, bandName):
        
        self.dataset.SetMetadataItem("bandName", bandName)

    #---------------------------------------------------------------------------
    # specTypeCode()
    #---------------------------------------------------------------------------
    def specTypeCode(self):
        
        try:
            stc = self.dataset.GetMetadataItem('NITF_CSEXRA_SENSOR')
            if stc is None:
                if self.imdTag.find('BANDID').text == 'P':
                    stc = 'PAN'
                elif self.imdTag.find('BANDID').text == 'MS1' or \
                                    self.imdTag.find('BANDID').text == 'Multi':
                    stc = 'MS'
      
            return stc

        except:
          return None          

    #---------------------------------------------------------------------------
    # year()
    #---------------------------------------------------------------------------
    def year(self):

        try:
            yr = self.dataset.GetMetadataItem('NITF_CSDIDA_YEAR')
            if yr is None:
                yr = self.firstLineTime().year

            return yr
  
        except:
            return None

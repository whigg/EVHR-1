
import os

import numpy as np

import gdal

#-------------------------------------------------------------------------------
# class LandsatNbrNdviHelper
#-------------------------------------------------------------------------------
class LandsatNbrNdviHelper(object):

    #---
    # The output pixels are scaled by 10000, so the native no-data value, -9999,
    # would be in the range.  To prevent this, change native no-data values to
    # -15000.  The pixels indicated bad by the QA band are changed to -20000,
    # also so they will not be in the range of valid pixels.
    #---
    NATIVE_NO_DATA_VALUE       =  -9999
    NATIVE_NO_DATA_REPLACEMENT = -15000
    QA_REPLACEMENT             = -20000
    
    #---
    # USGS publishes a chart of the possible pixel values and their meaning.
    # Use this instead of dealing with bit masks.
    # https://landsat7.usgs.gov/landsat-surface-reflectance-quality-assessment
    # Values that do not have cloud, cloud shadow, fill, or snow bits set.
    #---
    C_VALUES          = [322, 386, 832]
    E_VALUES          = [66, 96, 130, 160, 224]
    ACCEPTABLE_VALUES = C_VALUES + E_VALUES

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, outFile, productName, keepBandFiles = False, 
                 logger = None):

        # Validate the output file.
        if outFile == None:
            raise RuntimeError('An output file must be provided.')
            
        self.outFile       = outFile
        self.keepBandFiles = keepBandFiles
        self.logger        = logger
        self.productName   = str(productName)

    #---------------------------------------------------------------------------
    # createNoDataMask
    #---------------------------------------------------------------------------
    def createNoDataMask(self, inArray, qaArray):
        
        rows = len(inArray)
        cols = len(inArray[0])
        mask = np.zeros((rows, cols))
        
        numRows = len(inArray)
        
        if numRows != len(qaArray):

            raise RuntimeError('Dimension 0 of the input array must be ' +
                               'the same length as QA array.')
                               
        numCols = len(inArray[0])

        if numCols != len(qaArray[0]):

            raise RuntimeError('Dimension 0 of the input array must be ' +
                               'the same length as QA array.')
                           
        for row in range(numRows):
            
            inRow = inArray[row]
            qaRow = qaArray[row]
            
            for col in range(numCols):

                inPixel = int(inRow[col])
                qaPixel = int(qaRow[col])
            
                if qaPixel not in LandsatNbrNdviHelper.ACCEPTABLE_VALUES:
                    
                    mask[row][col] = LandsatNbrNdviHelper.QA_REPLACEMENT

                elif inPixel == LandsatNbrNdviHelper.NATIVE_NO_DATA_VALUE:
                    
                    mask[row][col] = \
                        LandsatNbrNdviHelper.NATIVE_NO_DATA_REPLACEMENT

        return mask
        
    #---------------------------------------------------------------------------
    # getBandFileName
    #---------------------------------------------------------------------------
    def getBandFileName(self, band, bandFiles):

        for bandFile in bandFiles:
            if band in bandFile:
                return bandFile
                
        raise RuntimeError('Unable to find band ' + str(band) + \
                           ' in the band files.')

    #---------------------------------------------------------------------------
    # getNirBandFile
    #---------------------------------------------------------------------------
    def getNirBandFile(self, sensor):
        raise RuntimeError('This must be implemented by a subclass.')
        
    #---------------------------------------------------------------------------
    # getRedBandFile
    #---------------------------------------------------------------------------
    def getRedBandFile(self, sensor):
        raise RuntimeError('This must be implemented by a subclass.')
        
    #---------------------------------------------------------------------------
    # nativeAndQaToNan
    #
    # Replace inArray pixels that are either no data values or marked as bad by
    # QA with NaN.
    #---------------------------------------------------------------------------
    def nativeAndQaToNan(self, inArray, qaArray):

        numRows = len(inArray)
        
        if numRows != len(qaArray):

            raise RuntimeError('Dimension 0 of the input array must be ' +
                               'the same length as QA array.')
                               
        numCols = len(inArray[0])

        if numCols != len(qaArray[0]):

            raise RuntimeError('Dimension 0 of the input array must be ' +
                               'the same length as QA array.')
                           
        outArray = inArray
        
        for row in range(numRows):
            
            inRow = inArray[row]
            qaRow = qaArray[row]
            
            for col in range(numCols):

                inPixel = int(inRow[col])
                qaPixel = int(qaRow[col])
            
                if qaPixel not in LandsatNbrNdviHelper.ACCEPTABLE_VALUES or \
                   inPixel == LandsatNbrNdviHelper.NATIVE_NO_DATA_VALUE:
                    outArray[row][col] = np.nan

        return outArray

    #---------------------------------------------------------------------------
    # run
    #---------------------------------------------------------------------------
    def run(self, bandFiles):

        # If the output file already exists, don't run it again.
        if os.path.exists(self.outFile):

            if self.logger:
                self.logger.info(self.outFile + ' already exists.')

            return

        if not bandFiles:
            raise RuntimeError('A list of band files must be provided.')

        if self.logger:
            self.logger.info('Creating ' + self.productName + ' for ' + \
                             self.outFile)

        #---
        # Determine which bands to use.
        # https://landsat.usgs.gov/landsat-collections#C1%20Tiers
        #---
        testBandFile = os.path.basename(bandFiles[0])
        date, sensor, band = testBandFile.split('_', 2)
        sensor = sensor.upper()

        nirBandFile = self.getNirBandFile(sensor, bandFiles)
        redBandFile = self.getRedBandFile(sensor, bandFiles)
        qaFile      = self.getBandFileName('pixel_qa', bandFiles)

        # Open the bands.
        nirBand = gdal.Open(nirBandFile)
        redBand = gdal.Open(redBandFile)
        qaBand  = gdal.Open(qaFile)
        
        #---
        # Due to memory limitations, do not read entire bands into memory.
        # Instead, chunk through them.  Try one line at a time, to make dealing
        # with offsets easier.  First, create an empty output TIF.
        #---
        rows      = nirBand.RasterYSize
        cols      = nirBand.RasterXSize
        dataType  = nirBand.GetRasterBand(1).DataType
        tifDriver = gdal.GetDriverByName("GTiff")
        drv       = tifDriver.Create(self.outFile, cols, rows, 1, dataType)

        drv.SetGeoTransform(nirBand.GetGeoTransform())
        drv.SetProjection(nirBand.GetProjection())
        
        drv.GetRasterBand(1).SetNoDataValue(LandsatNbrNdviHelper. \
                                            NATIVE_NO_DATA_REPLACEMENT)
        
        # Chunk through, row by row.
        for yOff in range(rows):
            
            # Read a row.
            xOff     = 0
            xSize    = cols
            ySize    = 1
            nirArray = nirBand.ReadAsArray(xOff, yOff, xSize, ySize).astype(float)
            redArray = redBand.ReadAsArray(xOff, yOff, xSize, ySize).astype(float)
            qaArray  = qaBand.ReadAsArray (xOff, yOff, xSize, ySize).astype(float)
        
            #---
            # Create the no-data mask based on the NIR band before we replace
            # no-data values with NaNs.
            #---
            mask = self.createNoDataMask(nirArray, qaArray)

            #---
            # Replace native no-data values with np.nan, so they will be
            # ignored Must to incorporate QA in here too, or else the nodata
            # mask values (-15000) will be added to pixels with values other
            # than np.nan. 
            #---
            nirArray = self.nativeAndQaToNan(nirArray, qaArray)
            redArray = self.nativeAndQaToNan(redArray, qaArray)

            numerator   = np.subtract(nirArray, redArray).astype(float)
            denominator = np.add     (nirArray, redArray).astype(float)

            #---
            # Divide using np.errstate in case denominator is 0.  If so, we want 
            # the result to be 0.
            #---
            ndviArray = None
        
            with np.errstate(divide = 'ignore', invalid = 'ignore'):
            
                # After this step, 0/0 will be --> np.nan.
                ndviArray = np.true_divide(numerator, denominator).astype(float)

                # Set everything that is np.nan to 0, including no-data values.
                ndviArray[np.isnan(ndviArray)] = 0 

            #---
            # We also want the NDVI output to be 0 if either band was <= 0.  This
            # is to avoid extraneous NDVI vals, such as in areas of water.
            #---
            with np.errstate(invalid = 'ignore'):
                ndviArray[((nirArray <= 0) | (redArray <= 0))] = 0

            # Scale NDVI up by 10000.
            ndviArray = np.multiply(ndviArray, 10000)

            #---
            # Add the no-data mask to the output so we can distinguish between 0 
            # and no data.
            #---
            ndviArray = ndviArray + mask
        
            # Write the row.
            drv.GetRasterBand(1).WriteArray(ndviArray, xOff, yOff)
            
        # Remove the band files.
        if not self.keepBandFiles:
            
            os.remove(nirBandFile)
            os.remove(redBandFile)
            os.remove(qaFile)

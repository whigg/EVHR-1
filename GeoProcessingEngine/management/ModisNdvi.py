
import os

import gdal
import numpy as np

#-------------------------------------------------------------------------------
# class ModisNdvi
#-------------------------------------------------------------------------------
class ModisNdvi():
    
    NATIVE_NO_DATA_VALUE = -28672
    NO_DATA_VALUE        = -15000
    
    #---------------------------------------------------------------------------
    # __init__
    #
    # This expects workingDir to contain files named:
    #
    #   NDVI.<product date 1>.band1.tif
    #   NDVI.<product date 1>.band2.tif
    #   NDVI.<product date 1>.qa.tif
    #   NDVI.<product date 2>.band1.tif
    #   NDVI.<product date 2>.band2.tif
    #   NDVI.<product date 2>.qa.tif
    #   ...
    #
    # Provide the product date, this will create the NDVI for for it using its
    # three constituent files: band1, band2 and qa.
    #---------------------------------------------------------------------------
    def __init__(self, productDate, workingDir):

        if productDate == None:
            raise RuntimeError('A product date must be provided.')
        
        if workingDir == None             or \
           not os.path.exists(workingDir) or \
           not os.path.isdir(workingDir):
           
            raise RuntimeError('A valid working directory must be provided.')
        
        self.productDate = productDate
        self.outDir      = workingDir        
        self.tifDriver   = gdal.GetDriverByName("GTiff")
    
    #---------------------------------------------------------------------------
    # arrayToTif
    #---------------------------------------------------------------------------
    def arrayToTif(self, array, baseName, exampleTif):
                   
        outFile  = os.path.join(self.outDir, baseName + '.tif')
        dataType = exampleTif.GetRasterBand(1).DataType
        cols     = exampleTif.RasterXSize
        rows     = exampleTif.RasterYSize
        
        drv = self.tifDriver.Create(outFile, cols, rows, 1, dataType)

        drv.SetGeoTransform(exampleTif.GetGeoTransform())
        drv.SetProjection(exampleTif.GetProjection())
        drv.GetRasterBand(1).SetNoDataValue(ModisNdvi.NO_DATA_VALUE)
        drv.GetRasterBand(1).WriteArray(array)

    #---------------------------------------------------------------------------
    # createNoDataMask
    #---------------------------------------------------------------------------
    def createNoDataMask(self, array, cols, rows):
        
        noDataValues = np.ones ((rows, cols)) * ModisNdvi.NO_DATA_VALUE
        passValues   = np.zeros((rows, cols))
        
        mask = np.where(array == ModisNdvi.NATIVE_NO_DATA_VALUE, 
                        noDataValues, 
                        passValues)
        
        return mask
        
    #---------------------------------------------------------------------------
    # getBandFileName
    #---------------------------------------------------------------------------
    def getBandFileName(self, band):
        
        baseName = 'NDVI.' + self.productDate + '.'
        bandFile = os.path.join(self.outDir, baseName + band + '.tif')
        
        if not os.path.exists(bandFile):

            raise RuntimeError('Band file, ' + 
                               str(bandFile) + 
                               ', does not exist.')     

        return bandFile

    #---------------------------------------------------------------------------
    # run
    #---------------------------------------------------------------------------
    def run(self):
        
        nirBandFile = self.getBandFileName('band2')
        redBandFile = self.getBandFileName('band1')
        qaFile      = self.getBandFileName('qa')
        
        nirBand = gdal.Open(nirBandFile)
        redBand = gdal.Open(redBandFile)
        qaBand  = gdal.Open(qaFile)
        
        nirArray = nirBand.ReadAsArray().astype(float)
        redArray = redBand.ReadAsArray().astype(float)

        # Replace native no-data values with np.nan, so they will be ignored. 
        nirArray[nirArray == ModisNdvi.NATIVE_NO_DATA_VALUE] = np.nan 
        redArray[redArray == ModisNdvi.NATIVE_NO_DATA_VALUE] = np.nan

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
        cols      = nirBand.RasterXSize
        rows      = nirBand.RasterYSize
        mask      = self.createNoDataMask(nirArray, cols, rows)
        ndviArray = ndviArray + mask
        
        # Write the output.
        self.arrayToTif(ndviArray, 'NDVI.' + self.productDate, nirBand)





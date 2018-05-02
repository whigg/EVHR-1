
import os

from osgeo import gdal
from osgeo.osr import SpatialReference

#-------------------------------------------------------------------------------
# class GdalFile
#
# This class represents a GDAL image file.  It makes certain functions easier to
# manage than it would be using GDAL directly for these things.
#-------------------------------------------------------------------------------
class GdalFile(object):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, fileName, logger = None):

        if not os.path.isfile(fileName):
            raise RuntimeError('{} does not exist'.format(fileName))

        self.logger = logger

        self.fileName = fileName
        self.dataset  = gdal.Open(self.fileName, gdal.GA_ReadOnly)

        if not self.dataset:
            raise RuntimeError("Could not open {}".format(self.fileName))

        # Extent / SRS
        self.srs = None
        
        if self.dataset.GetGCPCount():
            
            self.ulx = self.dataset.GetGCPs()[0].GCPX
            self.uly = self.dataset.GetGCPs()[0].GCPY
            self.lrx = self.dataset.GetGCPs()[2].GCPX
            self.lry = self.dataset.GetGCPs()[2].GCPY
            self.srs = SpatialReference(self.dataset.GetGCPProjection())
            
            #---
            # Sometimes the input file will have ulx and lrx swapped.  Detect
            # and fix this.
            #---
            if self.ulx > self.lrx:
                
                temp = self.ulx
                self.ulx = self.lrx
                self.lrx = temp

        else:

            geoTransform = self.dataset.GetGeoTransform()
            self.ulx = geoTransform[0]
            self.uly = geoTransform[3]
            self.lrx = self.ulx + geoTransform[1] * self.dataset.RasterXSize
            self.lry = self.uly + geoTransform[5] * self.dataset.RasterYSize
            self.srs = SpatialReference(self.dataset.GetProjection())

        if not self.srs:
            raise RuntimeError("Could not get projection or corner coordinates")

        
    
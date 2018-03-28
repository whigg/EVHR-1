
import abc

from osgeo import ogr
from osgeo.osr import SpatialReference

#-------------------------------------------------------------------------------
# class Tiler
#
# https://pymotw.com/2/abc/
#-------------------------------------------------------------------------------
class Tiler(object):
    
    __metaclass__ = abc.ABCMeta
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, ulx, uly, lrx, lry, srs, logger):
        
        if not isinstance(srs, SpatialReference):
            raise TypeError('SRS must be an instance of SpatialReference.')
        
        self.ulx = ulx
        self.uly = uly
        self.lrx = lrx
        self.lry = lry
        self.srs = srs

        self.corners = self.defineGrid()

    #---------------------------------------------------------------------------
    # defineGrid
    #---------------------------------------------------------------------------
    @abc.abstractmethod
    def defineGrid(self):
        
        """This method returns an array where each element is an array of
        [ulx, uly, lrx, lry] defining the corners of a grid cell."""

    #---------------------------------------------------------------------------
    # gridsToPolygons
    #---------------------------------------------------------------------------
    def gridToPolygons(self, grid):
        
        polygons = []
        
        for cell in grid:
            
            fUlx = float(cell[0])
            fUly = float(cell[1])
            fLrx = float(cell[2])
            fLry = float(cell[3])

            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(fUlx, fUly)
            ring.AddPoint(fLrx, fUly)
            ring.AddPoint(fLrx, fLry)
            ring.AddPoint(fUlx, fLry)
            ring.AddPoint(fUlx, fUly)  # Repeating the first closes the polygon.
        
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            poly.AssignSpatialReference(self.srs)
            polygons.append(poly)
            
        return polygons
        
    #---------------------------------------------------------------------------
    # gridUpperLeft
    #---------------------------------------------------------------------------
    def gridUpperLeft(self):
        
        """This method returns the upper-left starting point for gridding.  This
        may be overridden to shift the grid around the AoI."""
        
        return [self.ulx, self.uly]
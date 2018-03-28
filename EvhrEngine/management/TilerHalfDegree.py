
from osgeo.osr import CoordinateTransformation
from osgeo.osr import SpatialReference

from EvhrEngine.management.Tiler import Tiler

#-------------------------------------------------------------------------------
# class TilerHalfDegree
#-------------------------------------------------------------------------------
def TilerHalfDegree(Tiler):
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, ulx, uly, lrx, lry, srs, logger):
        
        # This tiler requires the corners to be in geographic projection.
        GEOG_4326 = SpatialReference('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
        
        if not GEOG_4326.IsSame(srs):

            xform = CoordinateTransformation(srs, GeoRetriever.GEOG_4326)
            ulPt = xform.TransformPoint(ulx, uly)
            lrPt = xform.TransformPoint(lrx, lry)
            
            ulx = ulPt.GetX()
            uly = ulPt.GetY()
            lrx = lrPt.GetX()
            lry = lrPt.GetY()
            srs = GEOG_4326
        
        # Initialize the base class.
        super(TilerHalfDegree, self).__init__(ulx, uly, lrx, lry, srs, logger)

    #---------------------------------------------------------------------------
    # defineGrid
    #---------------------------------------------------------------------------
    def defineGrid(self):

        #---
        # Start at the upper-left corner of the AoI, and create 1/2-degree
        # square tiles.  Adjust initial lon and lat by 0.5, so the loop's test
        # lets the tiles encompass the far edges of the AoI.
        #---
        lons   = []
        curLon = float(self.gridUpperLeft()[0]) - 0.5
        maxLon = float(self.lrx)

        while curLon <= maxLon:

            curLon += 0.5
            lons.append(curLon)

        lats   = []
        curLat = float(self.gridUpperLeft()[1]) + 0.5
        minLat = float(self.lry)

        while curLat >= minLat:

            curLat -= 0.5
            lats.append(curLat)

        # We have the lats and longs comprising the grid.  Form them into tiles.
        corners = []

        for x in range(len(lons) - 1):
            for y in range(len(lats) - 1):
                corners.append((lons[x], lats[y], lons[x+1], lats[y+1]))

        return corners
        
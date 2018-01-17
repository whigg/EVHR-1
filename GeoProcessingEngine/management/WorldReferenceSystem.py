
import os
import tempfile
from xml.dom import minidom

#-------------------------------------------------------------------------------
# WorldReferenceSystem
#-------------------------------------------------------------------------------
class WorldReferenceSystem():
    
    WRS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'wrs2/wrs2_descending.shp')
    
    #---------------------------------------------------------------------------
    # pathRows
    #---------------------------------------------------------------------------
    @staticmethod
    def pathRows(ulx, uly, lrx, lry, srs, logger = None):
        
        # Clip the WRS Shapefile for this bounding box.
        clipFile = tempfile.mkstemp()[1]

        cmd = 'ogr2ogr'                        + \
              ' -spat'                         + \
              ' ' + str(ulx)                   + \
              ' ' + str(lry)                   + \
              ' ' + str(lrx)                   + \
              ' ' + str(uly)                   + \
              ' -spat_srs'                     + \
              ' "' + srs.ExportToProj4() + '"' + \
              ' -f "GML"'                      + \
              ' -select "PATH, ROW"'           + \
              ' "' + clipFile   + '"'          + \
              ' "' + WorldReferenceSystem.WRS_FILE + '"' 

        if logger:
            logger.info(cmd)
            
        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('Failed to clip ' + WorldReferenceSystem.WRS_FILE)

        # Read the path and row from the GML.
        xml      = minidom.parse(clipFile)
        features = xml.getElementsByTagName('gml:featureMember')

        # Put them into a list of (row, path) tuples.
        pathRows = []

        for feature in features:
    
            path = str(feature.getElementsByTagName('ogr:PATH')[0].firstChild.data)
            row  = str(feature.getElementsByTagName('ogr:ROW')[0].firstChild.data)
            pathRows.append((path, row))
        
        return pathRows

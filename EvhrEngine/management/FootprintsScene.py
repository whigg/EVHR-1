
#-------------------------------------------------------------------------------
# class FootprintsScene
#-------------------------------------------------------------------------------
class FootprintsScene(object):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, sceneGML, logger = None):
        
        self.gml = sceneGML
        self.logger = logger

    #---------------------------------------------------------------------------
    # pairName
    #---------------------------------------------------------------------------
    def pairName(self):
        
        return self._getValue('ogr:pairname')
        
    #---------------------------------------------------------------------------
    # getValue
    #---------------------------------------------------------------------------
    def _getValue(self, tagName):
        
        return self.gml.getElementsByTagName(tagName)[0].childNodes[0].nodeValue
        
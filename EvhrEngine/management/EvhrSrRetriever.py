import os

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrToaRetriever import EvhrToaRetriever

#-------------------------------------------------------------------------------
# class EvhrSrRetriever
#-------------------------------------------------------------------------------
class EvhrSrRetriever(EvhrToaRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # Initialize the base class.
        super(EvhrSrRetriever, self).__init__(request, logger, numProcesses)

        self.srDir = os.path.join(self.request.destination.name, '6-sr')

    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):

        # This is where the mosaic data set is created from the set of ToAs.
        pass

    #---------------------------------------------------------------------------
    # listConstituents
    #
    # Constituent: SR file
    # Files:  scenes for a single ToA strip
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query for scenes.
        scenes = self.getScenes(self.request,
                                self.retrievalUlx,
                                self.retrievalUly,
                                self.retrievalLrx,
                                self.retrievalLry,
                                self.retrievalSRS,
                                True,
                                False,
                                ['WV02', 'WV03'])

        if not scenes and self.logger:
            self.logger.error('No multispectral scenes for WV2 or WV3.')

        # Aggregate the scenes into ToAs.
        toas = {}
        
        for scene in scenes:
            
            dgf = DgFile(scene, self.logger)
            stripID = dgf.getStripName()
            toaName = os.path.join(self.toaDir, stripID + '-toa.tif')

            if not toas.has_key(toaName):
                toas[toaName] = []
                
            toas[toaName].append(scene)
            
        # Aggregate the ToAs into SRs.
        constituents = {}
        
        for toa in toas:
            
            toaBaseName = os.path.basename(toa).replace('-toa', '')
            srName = os.path.join(self.srDir, toaBaseName)
            constituents[srName] = toas[toa]
            
        print constituents
        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        stripName = DgFile(fileList[0], self.logger).getStripName()
        stripBandList = self.scenesToStrip(stripName, fileList)
        self.processStrip(stripBandList, toaName)
        
import os

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrToaRetriever import EvhrToaRetriever
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.models import EvhrScene

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
    # getScenes
    #---------------------------------------------------------------------------
    def getScenes(self, request, ulx, uly, lrx, lry, srs):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = request)
        sceneFiles = []

        if evhrScenes:
            
            sceneFiles = self._validateScenes(evhrScenes)
            
            for sceneFile in sceneFiles:
                
                dgf = DgFile(sceneFile)
                
                if dgf.isPanchromatic():
                    
                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            sceneFile.fileName + \
                                            ' is being skipped because' + \
                                            ' it is panchromatic.')
                                            
                if dgf.sensor() != 'WV02' and dgf.sensor() != 'WV03':

                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            sceneFile.fileName + \
                                            ' is being skipped because' + \
                                            ' it is not WV02 or WV03.')
                                            
        else:
            
            fpScenes = None
            fpq = FootprintsQuery(logger=self.logger)
            fpq.addAoI(ulx, uly, lrx, lry, srs)
            fpq.setMinimumOverlapInDegrees()
            fpq.addSensors(['WV02', 'WV03'])
            fpq.setPanchromaticOff()

            maxScenes = EvhrToaRetriever.MAXIMUM_SCENES
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                maxScenes = min(maxScenes, settings.MAXIMUM_SCENES)
                
            fpq.setMaximumScenes(maxScenes)
            fpScenes = fpq.getScenes()
            self._fpScenesToEvhrScenes(fpScenes)
            sceneFiles = [fps.fileName() for fps in fpScenes]
                
        sceneFiles.sort()
        
        return sceneFiles

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
                                self.retrievalSRS)

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
            
        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        stripName = DgFile(fileList[0], self.logger).getStripName()
        stripBandList = self.scenesToStrip(stripName, fileList)
        
        toaName = os.path.join(self.toaPath, 
                               os.path.basename(constituentFileName))
        
        self.processStrip(stripBandList, toaName)
        

import os
import re
from sets import Set
import shutil

from django.conf import settings

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrHelper import EvhrHelper
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.management.FootprintsScene import FootprintsScene
from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.models import EvhrScene
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class EvhrDemRetriever
#-------------------------------------------------------------------------------
class EvhrDemRetriever(GeoRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        self.evhrHelper = EvhrHelper(logger)

        # The output SRS must be UTM, regardless of what the user chooses.
        request.outSRS = self.evhrHelper.getUtmSrs(request)
        request.save(update_fields = ['outSRS'])

        # Initialize the base class.
        super(EvhrDemRetriever, self).__init__(request, logger, numProcesses)

        #---
        # GeoRetriever should always choose EPSG:4326 as the retrieval SRS
        # because that is all that FOOTPRINTS knows.  Verify that.
        #---
        if not self.retrievalSRS.IsSame(GeoRetriever.GEOG_4326):
            raise RuntimeError('Retrieval SRS must be geographic.')
            
        self.demDir = os.path.join(self.request.destination.name, 'dems')

        if not os.path.exists(self.demDir):
            os.mkdir(self.demDir)
            
        #---
        # Print system information.  This can be a helpful reference when there
        # are system errors.
        #---
        scmd = SystemCommand('parallel_stereo -v', None, self.logger)
        self.logger.info('Using ' + str(scmd.stdOut))
        self.logger.info('PYTHONPATH = ' + os.environ['PYTHONPATH'])

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # _ingestScene
    #---------------------------------------------------------------------------
    def _ingestScene(self, fpScene, pairsDict, request):
        
        # Verify the scene exists on disk.
        sceneOnDisk = os.path.exists(fpScene.fileName)
        
        # Add an EvhrScene, if it does not exist.
        try:
            evhrScene = EvhrScene.objects.get(sceneFile=fpScene.fileName)
            
            if not sceneOnDisk:
                evhrScene.delete()
            
        except EvhrScene.DoesNotExist:
            
            evhrScene = EvhrScene()
            evhrScene.request = request
            evhrScene.sceneFile = fpScene.fileName()
            evhrScene.save()

        if not sceneOnDisk:
            
            import pdb
            pdb.set_trace()
            
            if self.logger:
                
                self.logger.warning('Scene, ' + \
                                    str(fpScene) + \
                                    ' is not on disk.')
            return
            
        # Aggregate the scene into the pairs.
        pairName = fpScene.pairName()
        
        if not pairsDict.has_key(pairName):
            pairsDict[pairName] = set()
            
        pairsDict[pairName].add(str(fpScene.fileName()))
        
    #---------------------------------------------------------------------------
    # getPairs
    #---------------------------------------------------------------------------
    def getPairs(self, ulx, uly, lrx, lry, srs, request):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = request)
        pairs = {}
        
        if evhrScenes:
            
            fpq = FootprintsQuery(logger=self.logger)
            fpq.addEvhrScenes(evhrScenes)
            fpScenes = fpq.getScenes()
            self.evhrHelper.checkForMissingScenes(fpScenes, evhrScenes)
        
        else:
            
            fpq = FootprintsQuery(logger=self.logger)
            fpq.addAoI(ulx, uly, lrx, lry, srs)
            fpq.setPairsOnly()
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                fpq.setMaximumScenes(settings.MAXIMUM_SCENES)
            
            fpScenes = fpq.getScenes()
            
        # ---
        # Collect all the catalog IDs, then perform one big query, with the
        # expectation that one big query is faster than many small ones.
        # ---
        catIDs = []
        
        for fpScene in fpScenes:
            
            self._ingestScene(fpScene, pairs, request)
            catID1, catID2 = fpScene.getCatalogIDs()
            catIDs.append(catID1)
            catIDs.append(catID2)
            
        catQuery = FootprintsQuery(logger=self.logger)
        for catID in catIDs: catQuery.addCatalogID(catID)
        catScenes = catQuery.getScenes()
        for scene in catScenes: self._ingestScene(scene, pairs, request)

        return pairs
        
    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        #---
        # Query Footprints seeking pairs.  Scenes is a list of NITF files.
        #
        # Set(['WV01_20110226_10200100123C2600_1020010011416200', 
        # 'WV01_20110709_10200100140E8300_1020010012026500', 
        # 'WV01_20110227_1020010011055300_1020010012A0BE00', 
        # 'WV01_20110303_102001001157E300_1020010012BE9500', 
        # 'WV01_20110618_10200100149D3C00_1020010015B3E800', 
        # 'WV01_20110708_10200100144BD800_1020010013E74D00', 
        # 'WV01_20110804_1020010015973400_10200100152A5F00', 
        # 'WV01_20110402_102001001163AB00_102001001268E300', 
        # 'WV01_20110303_1020010011628B00_1020010011756100', 
        # 'WV01_20110401_10200100113F5C00_1020010011937800'])
        #---
        pairs = self.getPairs(self.retrievalUlx,
                              self.retrievalUly,
                              self.retrievalLrx,
                              self.retrievalLry,
                              self.retrievalSRS,
                              self.request)
                              
        # Create the constituents, which now look like:
        # {pairName.tif: {pair name: [scene1, scene2, ...]}, ...}
        constituents = {}

        for pair in pairs:

            consName = os.path.join(self.demDir, pair + '.tif')
            constituents[consName] = {pair : pairs[pair]}
            
        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        # Create the working directory.
        pairName = fileList.items()[0][0]
        workDir = os.path.join(self.demDir, pairName)
        os.mkdir(workDir)
        
        # Copy the scenes to the working directory.
        for scene in fileList.items()[0][1]:
            
            shutil.copy(scene, workDir)
            xmlName = scene.replace('.ntf', '.xml')
            shutil.copy(xmlName, workDir)
        
        # PAIR_NAME     = fileList[0]
        PAIR_NAME     = pairName
        TEST          = 'true'
        ADAPT         = 'true'
        MAP           = 'false'
        RUN_PSTEREO   = 'true' 
        BATCH_NAME    = '"' + self.request.name + '"'
        SGM           = 'false'
        SUB_PIX_KNL   = '15'
        ERODE_MAX     = '24'
        COR_KNL_SIZE  = '21'
        MYSTERY1      = '300'
        OUT_DIR       = self.demDir
        QUERY         = 'false'
        CROP_WINDOW   = '"0 15000 5000 5000"'
        USE_NODE_LIST = 'true'
        NODES         = '/att/nobackup/rlgill/DgStereo/nodeList.txt'
        
        cmd = settings.DEM_APPLICATION    + \
              ' ' + PAIR_NAME             + \
              ' ' + TEST                  + \
              ' ' + ADAPT                 + \
              ' ' + MAP                   + \
              ' ' + RUN_PSTEREO           + \
              ' ' + BATCH_NAME            + \
              ' _placeholder_for_rpcdem_' + \
              ' ' + USE_NODE_LIST         + \
              ' ' + NODES                 + \
              ' ' + SGM                   + \
              ' ' + SUB_PIX_KNL           + \
              ' ' + ERODE_MAX             + \
              ' ' + COR_KNL_SIZE          + \
              ' ' + MYSTERY1              + \
              ' ' + OUT_DIR               + \
              ' ' + QUERY                 + \
              ' ' + CROP_WINDOW
            
        try:
            SystemCommand(cmd, None, self.logger, self.request, True)
            
        except RuntimeError as error:
            
            if SystemCommand.RANSAC_MSG in error.message.lower():
                
                self.logger.warning('ASP was unable to match the left and ' + \
                                    'right images of a pair.  This pair ' + \
                                    'will not be processed.')

            else:
                raise 
                
        # Move the primary output file to the constituent name.
        pairDir = os.path.join(self.demDir, PAIR_NAME)
        outDemName = os.path.join(pairDir, 'out-DEM_4m.tif')

        if os.path.exists(outDemName):

            cmd = 'mv ' + outDemName + ' ' + constituentFileName
            sCmd = SystemCommand(cmd, None, self.logger, self.request, True)
        
        return constituentFileName    
              
              
        
        

import grp
import os
import pwd
import re
from sets import Set
import shutil

from django.conf import settings

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrHelper import EvhrHelper
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.management.FootprintsScene import FootprintsScene
from EvhrEngine.management.SystemCommand import SystemCommand
from EvhrEngine.models import EvhrError
from EvhrEngine.models import EvhrScene
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class EvhrDemRetriever
#-------------------------------------------------------------------------------
class EvhrDemRetriever(GeoRetriever):

    DEBUG_ONLY_PREPARE_DATA = False
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        self.evhrHelper = EvhrHelper(logger)

        # The output SRS must be UTM, regardless of what the user chooses.
        request.outSRS = self.evhrHelper.getUtmSrs(request)
        request.save(update_fields = ['outSRS'])

        # The DEM processor fails when it attempts to run more than 5 processes.
        numProcesses = max(5, numProcesses)
        
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

        os.environ['PYTHONPATH'] = \
            os.environ['PYTHONPATH'] + ':' + settings.PYTHON_PATH

        self.logger.info('PYTHONPATH = ' + os.environ['PYTHONPATH'])

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # getPairs
    #---------------------------------------------------------------------------
    def getPairs(self, ulx, uly, lrx, lry, srs):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request=self.request)
        features = None
        fpq = FootprintsQuery(logger=self.logger)
        fpq.addAoI(ulx, uly, lrx, lry, srs)
        
        if evhrScenes:
            
            fpq.addEvhrScenes(evhrScenes)
            fpScenes = fpq.getScenes()
            self.evhrHelper.checkForMissingScenes(fpScenes, evhrScenes)
        
        else:
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                fpq.setMaximumScenes(settings.MAXIMUM_SCENES)
            
            fpq.setMultispectralOff()
            fpq.setPairsOnly()
            fpScenes = fpq.getScenes()

            for scene in fpScenes:

                evhrScene = EvhrScene()
                evhrScene.request = self.request
                evhrScene.sceneFile = scene.fileName()
                evhrScene.save()
            
        # ---
        # Now that dg_stereo.sh does not query redundantly, EDR must copy each
        # pair's files to the request directory for dg_stereo.sh to find them.
        # The first step is to associate the pair name with its files.
        # ---
        pairs = {}

        for fps in fpScenes:
            
            pairName = fps.pairName()
            
            if not pairs.has_key(pairName):
                pairs[pairName] = []
                
            pairs[pairName].append(fps.fileName())
            
        # Ensure that each pair has its mates.
        pairsWithMissingScenes = []
        
        for pairName in pairs.iterkeys():
            
            mates = pairName.split('_')[2:]
            
            for mate in mates:
                
                r = re.compile('.*' + mate + '.*')
                
                if not (filter(r.match, pairs[pairName])):

                    fpq = FootprintsQuery(logger=self.logger)
                    fpq.addCatalogID([mate])
                    mates = fpq.getScenes()
                    
                    if mates:
                        
                        existingScenes = pairs[pairName]
                        
                        for fps in mates:
                            
                            if fps not in existingScenes:

                                pairs[pairName].append(fps.fileName())
                                fpScenes.append(fps)

                    else:
                        
                        if self.logger:

                            self.logger.warning('Pair ' +
                                                pairName +
                                                ' does not contain any scenes' +
                                                ' for ' +
                                                mate)

                        pairsWithMissingScenes.append(pairName)
                    
        #---
        # Remove pairs without scenes for both mates.  Count the scenes deleted
        # to reconcile with the number of scenes returned by the query.
        #---
        numUnpairedScenes = 0
        
        for pair in pairsWithMissingScenes:
            
            numUnpairedScenes += len(pairs[pair])
            
            for scene in pairs[pair]:
                
                EvhrScene.objects.get(request=self.request,
                                      sceneFile=scene).delete()
                
            del pairs[pair]
            
        #---
        # Count the scenes left to reconcile with the number of scenes returned
        # by the query.
        #---
        numPairedScenes = 0
        
        for pair in pairs:
            numPairedScenes += len(pairs[pair])
            
        if self.logger:
            
            numQueriedScenes = len(fpScenes)
            
            unaccountedScenes = \
                numQueriedScenes - numPairedScenes - numUnpairedScenes
            
            self.logger.info('Queried scenes: ' + \
                             str(numQueriedScenes) + '\n' + \
                             'Unpaired scenes: ' + \
                             str(numUnpairedScenes) + '\n' + \
                             'Paired scenes: ' + \
                             str(numPairedScenes) + '\n' + \
                             'Unaccounted scenes: ' + \
                             str(unaccountedScenes) + '\n' + \
                             'Pairs: ' + str(len(pairs)))
                             
            for pair in sorted(pairs.keys()):
                self.logger.info(pair)

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
                              self.retrievalSRS)
                              
        # ONLY RUN ONE SCENE FOR TESTING
        # pairs = list(pairs)[:1]
        # pairs = ['WV02_20160630_1030010058056300_1030010057266900'] # works
        # print '*** ONLY RUNNING SCENE ' + str(pairs[0])

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

        if os.path.exists(constituentFileName):
            return
            
        # Create the working directory.
        pairName = fileList.items()[0][0]
        workDir = os.path.join(self.demDir, pairName)
        
        if not os.path.exists(workDir):
            os.mkdir(workDir)
        
        # Copy the scenes to the working directory using sym links
        for scene in fileList.items()[0][1]:

            ext = os.path.splitext(scene)[1] # could be .tif or .ntf            
            dst = os.path.join(workDir, os.path.basename(scene))
            
            if not os.path.exists(dst):
                os.symlink(scene, dst)
                
            dstXml = dst.replace(ext, '.xml')
            
            if not os.path.exists(dstXml):
                os.symlink(scene.replace(ext, '.xml'), dstXml)

        if EvhrDemRetriever.DEBUG_ONLY_PREPARE_DATA:
            return constituentFileName
            
        # PAIR_NAME     = fileList[0]
        PAIR_NAME     = pairName
        TEST          = 'false' #'true'
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
            
        # try:
        #     SystemCommand(cmd, None, self.logger, self.request, True)
        #
        # except RuntimeError as error:
        #
        #     if SystemCommand.RANSAC_MSG in error.message.lower():
        #
        #         self.logger.warning('ASP was unable to match the left and ' + \
        #                             'right images of a pair.  This pair ' + \
        #                             'will not be processed.')
        #
        #     else:
        #         raise

        exitCode = \
            os.system(cmd + \
                      '> ' + \
                      os.path.join(self.request.destination.name, 'edr.out') +\
                      ' 2>&1')

        # if exitCode:
        #
        #     msg = 'DEM ' + pairName + ' failed.  Command: ' + cmd
        #     err = EvhrError()
        #     err.request = self.request
        #     err.errorOutput = msg
        #     err.command = cmd
        #     err.save()
        #
        #     if self.logger:
        #         self.logger.error(msg)
        
        # Move the primary output file to the constituent name.
        pairDir = os.path.join(self.demDir, PAIR_NAME)
        outDemName = os.path.join(pairDir, 'out-DEM_4m.tif')

        if os.path.exists(outDemName):

            cmd = 'mv ' + outDemName + ' ' + constituentFileName
            
            sCmd = SystemCommand(cmd, 
                                 None, 
                                 self.logger, 
                                 self.request, 
                                 True,
                                 False,
                                 ['no such file or directory'])
            
        else:

            msg = 'DEM ' + pairName + ' failed.\n' + \
                  'Command: ' + cmd + '\n' + \
                  'User: ' + pwd.getpwuid(os.getuid()).pw_name + '\n' + \
                  'Group: ' + grp.getgrgid(pwd.getpwuid(os.getuid()).pw_gid)[0]
                  
            err = EvhrError()
            err.request = self.request
            err.errorOutput = msg
            err.command = cmd
            err.save()
            
            if self.logger:
                self.logger.error(msg)

            # raise RuntimeError('DEM ' + outDemName + ' failed.  Command: ' + cmd)
        
        return constituentFileName    
              
              
        
        


import os

from django.conf import settings

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrHelper import EvhrHelper
from EvhrEngine.management.SystemCommand import SystemCommand
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

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query Footprints seeking pairs.  Scenes is a list of NITF files.
        scenes = self.evhrHelper.getScenes(self.request,
                                           self.retrievalUlx,
                                           self.retrievalUly,
                                           self.retrievalLrx,
                                           self.retrievalLry,
                                           self.retrievalSRS,
                                           pairsOnly = True)

        # Matching catalog IDs indicate pairs.  Aggregate by catalog ID.
        catIdConstituents = {}
            
        for scene in scenes:
            
            dgFile = DgFile(scene)
            catId = dgFile.getCatalogId()
            
            if not catIdConstituents.has_key(catId):
                catIdConstituents[catId] = []
                
            catIdConstituents[catId].append(scene)

        #---
        # Footprints queries can be limited to a certain number of records.
        # This can cause a pair to be missing a mate.  Discard any catIdConstituents
        # with only one file.
        #---
        incompletePairKeys = [key for key in catIdConstituents.iterkeys() \
                                if len(catIdConstituents[key]) < 2]

        for ipk in incompletePairKeys:
            del catIdConstituents[ipk]

        # Create the constituents.
        constituents = {}
        
        for cic in catIdConstituents.iterkeys():
            
            # oneMate = os.path.basename(catIdConstituents[cic][0])
            # pairName = '_'.join(oneMate.split('_')[:4])

            pair = catIdConstituents[cic]
            mate1 = DgFile(pair[0])
            mate2 = DgFile(pair[1])
            
            flTime = mate1.firstLineTime()

            import pdb
            pdb.set_trace()
            # Pair name is <sensor>_<yyyymmdd>_<catID1>_<catID2>.
            pairName = mate1.sensor + '_' + \
                       mate1.firstLineTime()
            
            consName = os.path.join(self.demDir, pairName + '.tif')
            constituents[consName] = catIdConstituents[cic]
            
        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        TEST          = 'true'
        ADAPT         = 'true'
        MAP           = 'false'
        RUN_PSTEREO   = 'true' 
        USE_NODE_LIST = 'false'
        NODES         = ''
        SGM           = 'false'
        SUB_PIX_KNL   = '15'
        ERODE_MAX     = '24'
        COR_KNL_SIZE  = '21'
        
        cmd = settings.DEM_APPLICATION    + \
              ' ' + fileList              + \
              ' ' + TEST                  + \
              ' ' + ADAPT                 + \
              ' ' + MAP                   + \
              ' ' + RUN_PSTEREO           + \
              ' ' + fileList[0]           + \
              ' _placeholder_for_rpcdem_' + \
              ' ' + USE_NODE_LIST         + \
              ' ' + NODES                 + \
              ' ' + SGM                   + \
              ' ' + SUB_PIX_KNL           + \
              ' ' + ERODE_MAX             + \
              ' ' + COR_KNL_SIZE
              
        sCmd = SystemCommand(cmd, None, self.logger, self.request, True)
        
              
              
              
        
        
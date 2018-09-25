
import os
from sets import Set

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

        if not os.path.exists(self.demDir):
            os.mkdir(self.demDir)

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # getPairs
    #---------------------------------------------------------------------------
    def getPairs(self, request, ulx, uly, lrx, lry, srs):

        fpRecs = self.evhrHelper.queryFootprints(ulx, 
                                                 uly, 
                                                 lrx, 
                                                 lry, 
                                                 srs, 
                                                 request,
                                                 True)

        pairs = Set([])

        for fpRec in fpRecs:

            pair = str(fpRec. \
                       getElementsByTagName('ogr:stereopair')[0]. \
                       firstChild. \
                       data)

            pairs.add(pair)
            
        import pdb
        pdb.set_trace()
        
        return pairs

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query Footprints seeking pairs.  Scenes is a list of NITF files.
        pairs = self.getPairs(self.request,
                              self.retrievalUlx,
                              self.retrievalUly,
                              self.retrievalLrx,
                              self.retrievalLry,
                              self.retrievalSRS)

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
        # This can cause a pair to be missing a mate.  Discard any
        # catIdConstituents with only one file.
        #---
        incompletePairKeys = [key for key in catIdConstituents.iterkeys() \
                                if len(catIdConstituents[key]) < 2]

        for ipk in incompletePairKeys:
            del catIdConstituents[ipk]

        # Create the constituents.
        constituents = {}
        
        for cic in catIdConstituents.iterkeys():
            
            pair = catIdConstituents[cic]
            mate1 = DgFile(pair[0])
            
            pairDate = str(mate1.firstLineTime().year)           + \
                       str(mate1.firstLineTime().month).zfill(2) + \
                       str(mate1.firstLineTime().day).zfill(2)

            # Pair name is <sensor>_<yyyymmdd>_<catID1>_<catID2>.
            pairName = mate1.sensor()       + '_' + \
                       pairDate             + '_' + \
                       mate1.getCatalogId() + '_' +\
                       DgFile(pair[1]).getCatalogId()
                       
            consName = os.path.join(self.demDir, 'out-DEM_4m.tif')
            constituents[consName] = [pairName]
            
        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        TEST          = 'true'
        ADAPT         = 'true'
        MAP           = 'false'
        RUN_PSTEREO   = 'true' 
        BATCH_NAME    = self.request.name
        USE_NODE_LIST = 'true'
        NODES         = '/att/nobackup/rlgill/DgStereo/nodeList.txt'
        SGM           = 'false'
        SUB_PIX_KNL   = '15'
        ERODE_MAX     = '24'
        COR_KNL_SIZE  = '21'
        MYSTERY1      = '300'
        OUT_DIR       = self.demDir
        
        cmd = settings.DEM_APPLICATION    + \
              ' ' + fileList[0]           + \
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
              ' ' + OUT_DIR
              
        sCmd = SystemCommand(cmd, None, self.logger, self.request, True)
        
        return constituentFileName    
              
              
        
        
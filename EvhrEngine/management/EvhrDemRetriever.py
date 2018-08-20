
from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrHelper import EvhrHelper
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

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query Footprints seeking pairs.
        scenes = self.evhrHelper.getScenes(self.request,
                                           self.retrievalUlx,
                                           self.retrievalUly,
                                           self.retrievalLrx,
                                           self.retrievalLry,
                                           self.retrievalSRS,
                                           pairsOnly = True)

        # Matching catalog IDs indicate pairs.  Aggregate by catalog ID.
        constituents = {}
            
        for scene in scenes:
            
            dgFile = DgFile(scene)
            catId = dgFile.getCatalogId()
            
            if not constituents.has_key(catId):
                constituents[catId] = []
                
            constituents[catId].append(scene)

        #---
        # Footprints queries can be limited to a certain number of records.
        # This can cause a pair to be missing a mate.  Discard any constituents
        # with only one file.
        #---
        incompletePairKeys = [key for key in constituents.iterkeys() \
                                if len(constituents[key]) < 2]

        for ipk in incompletePairKeys:
            del constituents[ipk]
            
        import pdb
        pdb.set_trace()
        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        pass
        
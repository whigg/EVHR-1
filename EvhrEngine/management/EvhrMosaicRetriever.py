
from EvhrEngine.management.EvhrToaRetriever import EvhrToaRetrieter

#-------------------------------------------------------------------------------
# class EvhrMosaicRetriever
#-------------------------------------------------------------------------------
class EvhrMosaicRetriever(EvhrToaRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # Initialize the base class.
        super(EvhrMosaicRetriever, self).__init__(request, logger, numProcesses)

    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):

        # This is where the mosaic data set is created from the set of ToAs.
        pass

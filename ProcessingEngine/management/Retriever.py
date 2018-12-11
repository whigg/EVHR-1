
from ProcessingEngine.models import Request

#-------------------------------------------------------------------------------
# class Retriever
#
# Request Hierarchy
#
#    Request
#        Constituent
#            File
#            File
#            ...
#        Constituent
#            File
#            File
#            ...
#        ...
#
# These are the methods to override in the order in which they are called.
#
#    - knowsProtocol():  mandatory
#      This returns True, when the concrete retriever can process the given
#      protocol.
#
#    - listConstituents():  mandatory 
#
#      This returns a list of Constituent names associated with the files used
#      to build each constituent.  Each of these Constituents will be processed
#      by retrieveOne().  This is actually another level in the data
#      hierarchy.  As an example, Landsat's constituents are a mosaic of scenes
#      for each date in the request's date range.  Each constituent is built
#      from all the scenes within the bounding box for one collection date.
#      Note, these are only file names; the files do not exist until
#      retrieveOne() runs.
#
#           {constituent1: [fileName1, fileName2, ...],
#            constituent2: [fileName1, fileName2, ...], ...}
#
#    - retrieveOne():  mandatory
#
#      Given one Constituent and its file names, this fully processes it to
#      create a final output file.  End Points can produce multiple
#      Constituents, which means there could be multiple final output files.
#
#    - aggregate():  optional
#      Use this method when constituents must be combined to form the final
#      product of a retriever.
#
#-------------------------------------------------------------------------------
class Retriever(object):

    #---------------------------------------------------------------------------
    # __init__ 
    #---------------------------------------------------------------------------
    def __init__(self, request, logger = None, maxProcesses = -1):

        if not request:
            raise RuntimeError('A request must be provided.')
            
        self.logger       = logger
        self.maxProcesses = maxProcesses
        self.request      = request
        
    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):
        pass
                   
    #---------------------------------------------------------------------------
    # listConstituents
    #
    # This returns an dict of constituent names mapped to the files comprising
    # the constituent
    #
    # /path/to/constituent1.tif
    #    /path/to/file1.hdf
    #    /path/to/file2.hdf
    #    /path/to/file3.hdf
    # /path/to/constituent2.tif
    #    /path/to/file4.hdf
    #    /path/to/file5.hdf
    #    /path/to/file6.hdf
    #
    # In straightforward cases where there is one file, like WCS, the
    # file is the same as the constituent.
    #
    # /path/to/constituent3.tif
    #    /path/to/file7.hdf
    #
    # In dict form, this looks like:
    #
    # {'/path/to/constituent1.tif': [/path/to/file1.hdf, /path/to/file2.hdf,
    #                                /path/to/file3.hdf],
    #  '/path/to/constituent2.tif': [/path/to/file4.hdf, /path/to/file5.hdf,
    #                                /path/to/file6.hdf],
    #  '/path/to/constituent3.tif': [/path/to/file7.hdf]}
    #---------------------------------------------------------------------------
    def listConstituents(self):
         raise RuntimeError('This method must be overridden by a subclass.')

    #---------------------------------------------------------------------------
    # retrieveOne
    #
    # constituentFileName is one of the keys to the dict produced by
    # listConstituents(), like /path/to/constituent1.tif.
    #
    # fileList is the value associated with that key, a list of files, like
    # [/path/to/file1.hdf, /path/to/file2.hdf, /path/to/file3.hdf].
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):
         raise RuntimeError('This method must be overridden by a subclass.')
        



import os
import urllib2

from MerraBase import MerraBase

#-------------------------------------------------------------------------------
# class MerraAllRetriever
#-------------------------------------------------------------------------------
class MerraAllRetriever (MerraBase):

	#---------------------------------------------------------------------------
	# __init__
	#---------------------------------------------------------------------------
    def __init__(self, request, logger):

        super(MerraAllRetriever, self).__init__(request, logger)
        self.timeIntervals = self.getTimeIntervals()

    #---------------------------------------------------------------------------
    # finishMerraFile
    #---------------------------------------------------------------------------
    def finishMerraFile(self, collectionFile, sessionID):
        
        downloadFile = urllib2.urlopen(self.request.endPoint.url + \
                                       'download.php?session_id=' + \
                                       sessionID)

        # Create an output file, and download thereto.
        baseName, ext = os.path.splitext(collectionFile)
        ncName = baseName + '.nc'
        oFile = open(ncName, 'w')
        oFile.write(downloadFile.read())
        oFile.close()
        downloadFile.close()

        tifName = baseName + '.tif'
        # self.xformOutput(ncName, tifName)
        self.nmToGt(ncName, tifName)
        
        if not MerraBase.KEEP_NC_FILES:
            os.remove(ncName)

    #---------------------------------------------------------------------------
    # getVars
    #---------------------------------------------------------------------------
    def getVars(self):

        return [(MerraBase.BASEFLOW,    'avg'),
                (MerraBase.ECHANGE,     'avg'),
                (MerraBase.EVLAND,      'avg'),
                (MerraBase.EVPINTR,     'avg'),
                (MerraBase.EVPSBLN,     'avg'),
                (MerraBase.EVPSOIL,     'avg'),
                (MerraBase.EVPTRNS,     'avg'),
                (MerraBase.FRSAT,       'avg'),
                (MerraBase.FRSNO,       'avg'),
                (MerraBase.FRUNST,      'avg'),
                (MerraBase.FRWLT,       'avg'),
                (MerraBase.GHLAND,      'avg'),
                (MerraBase.GRN,         'avg'),
                (MerraBase.GWETPROF,    'avg'),
                (MerraBase.GWETROOT,    'avg'),
                (MerraBase.GWETTOP,     'avg'),
                (MerraBase.LAI,         'avg'),
                (MerraBase.LHLAND,      'avg'),
                (MerraBase.LWLAND,      'avg'),
                (MerraBase.PARDFLAND,   'avg'),
                (MerraBase.PARDRLAND,   'avg'),
                (MerraBase.PRECSNOLAND, 'avg'),
                (MerraBase.PRECTOTLAND, 'avg'),
                (MerraBase.PRMC,        'avg'),
                (MerraBase.QINFIL,      'avg'),
                (MerraBase.RUNOFF,      'avg'),
                (MerraBase.RZMC,        'avg'),
                (MerraBase.SFMC,        'avg'),
                (MerraBase.SHLAND,      'avg'),
                (MerraBase.SMLAND,      'avg'),
                (MerraBase.SNODP,       'avg'),
                (MerraBase.SNOMAS,      'avg'),
                (MerraBase.SPLAND,      'avg'),
                (MerraBase.SPSNOW,      'avg'),
                (MerraBase.SPWATR,      'avg'),
                (MerraBase.SWLAND,      'avg'),
                (MerraBase.TELAND,      'avg'),
                (MerraBase.TPSNOW,      'avg'),
                (MerraBase.TSAT,        'avg'),
                (MerraBase.TSOIL1,      'avg'),
                (MerraBase.TSOIL2,      'avg'),
                (MerraBase.TSOIL3,      'avg'),
                (MerraBase.TSOIL4,      'avg'),
                (MerraBase.TSOIL5,      'avg'),
                (MerraBase.TSOIL6,      'avg'),
                (MerraBase.TSURF,       'avg'),
                (MerraBase.TUNST,       'avg'),
                (MerraBase.TWLAND,      'avg'),
                (MerraBase.TWLT,        'avg'),
                (MerraBase.WCHANGE,     'avg')
               ]

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):

        constituentDict = {}

        for var in iter(self.getVars()):

            # .../MERRA_ALL/BASEFLOW_avg
            baseName = os.path.join(self.request.destination.name, 
                                    var[0] + '_' + var[1])

            for sMonth, eMonth in self.timeIntervals:

                #---
                # There is no aggregation, so each predictor file is a one-
                # month .nc file.  There is a single consitituent, itself.
                # .../BASEFLOW_avg_20160101-20160131.tif
                #---
                month1  = self.formatDate(sMonth)
                month2  = self.formatDate(eMonth)
                onePred = baseName + '_' + month1 + '-' + month2 + '.tif'
                constituentDict[onePred] = [onePred]

        return constituentDict

    #---------------------------------------------------------------------------
    # nmToGt
    #---------------------------------------------------------------------------
    def nmToGt(self, ncFile, gtFile):

        cmd = 'gdal_translate "' + \
              ncFile + '" "'     + \
              gtFile             + \
              '" -a_srs EPSG:4326'
              
        status = os.system(cmd)
        
        if self.logger:
            self.logger.info(cmd)
                    
        if status != 0:
            raise RuntimeError('Unable to convert NC file to GT.')
        
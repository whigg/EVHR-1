
import calendar
from datetime import date
from datetime import datetime
from datetime import timedelta
import os
import urllib

from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class GpcpRetriever
#-------------------------------------------------------------------------------
class GpcpRetriever (GeoRetriever):

    KEEP_NC_FILES = False
    
    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # GPCP gets its own subdirectory because it can have multiple files.
        # request.destination.name = os.path.join(request.destination.name,'GPCP')
        # request.save(update_fields = ['destination'])
        #
        # if not os.path.exists(request.destination.name):
        #     os.mkdir(request.destination.name)

        # Initialize the base class.
        super(GpcpRetriever, self).__init__(request, logger, numProcesses)

        # Adjust the dates.
        earliestCollDate = datetime.strptime('1979-01-01','%Y-%m-%d').date()

        if self.request.startDate < earliestCollDate:
            self.request.startDate = earliestCollDate
        
        self.adjustEndDateNoEarlierThanXDays(180)
        
        if self.request.endDate < self.request.startDate:
            self.request.startDate = self.request.endDate
        
    #---------------------------------------------------------------------------
    # adjustEndDateNoEarlierThanXDays
    #---------------------------------------------------------------------------
    def adjustEndDateNoEarlierThanXDays(self, days):
        
        today = date.today()
        daysAgo = today - timedelta(days = days)
        
        if self.request.endDate > daysAgo:
            self.request.endDate = daysAgo
        
    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # listConstituents
    #---------------------------------------------------------------------------
    def listConstituents(self):
        
        # There will be a constituent for every month in the site's date range.
        constituents = {}
        curDate   = self.request.startDate
        
        while curDate <= self.request.endDate:
            
            year = curDate.year
            month = curDate.month
            twoDigitMonth = str(month).zfill(2)
            baseFile = 'GPCP-' + str(year) + '-' + twoDigitMonth + '.tif'
            fileName = os.path.join(self.request.destination.name, baseFile)
        
            url = self.request.endPoint.url + 'gpcp_cdr_v23rB1_y'+ str(year) + \
                  '_m' + twoDigitMonth + '.nc'
        
            constituents[fileName] = [url]
            
            # Get the first day of the next month.
            lastDay = calendar.monthrange(year, month)[1]
            curDate = date(year, month, lastDay) + timedelta(1)
            
        return constituents
        
    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        pfName, ext = os.path.splitext(constituentFileName)
        ncFile = pfName + '.nc'

        if not os.path.exists(ncFile):
            urllib.urlretrieve(fileList[0], ncFile)
            
        cmd = 'gdal_translate ' + \
              '-a_srs "' + self.retrievalSRS.ExportToProj4()  + '" ' + \
              '-a_ullr -178.75 88.75 178.75 -88.75 ' + \
              '"HDF5:"\'' + ncFile + '\'"://precip" ' + \
              '"' + constituentFileName + '"'

        if self.logger:
            self.logger.info("Command:  " + cmd)

        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('Failed to convert NC to Geotiff.')
        
        if not GpcpRetriever.KEEP_NC_FILES:
            os.remove(ncFile)

        self.xformOutput(constituentFileName)

        return constituentFileName


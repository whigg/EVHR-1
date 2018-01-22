
from datetime import datetime
from datetime import timedelta
import logging
import os
import sys
import time
import urllib2
from xml.dom import minidom

from owslib.crs import Crs

from WranglerProcess import settings
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# class MerraBase
#-------------------------------------------------------------------------------
class MerraBase (GeoRetriever):

    KEEP_NC_FILES  = True
    KEEP_XYZ_FILES = True
    #---
    # You have to consider that:
    # - 1 kg of rain water spread over 1 square meter of surface is 1 mm in
    #   thickness;
    # - there are 60x60x24=86400 seconds in one day.
    #
    # kg m-2 s-1 = (kg m-3) x (m/s) 
    # So, to go from m/s to mm/day you multiply by 86400x1000 
    # But to take out density (measured in kg m-3) you divide by 1000. 
    # Therefore, 1 kg/m2/s = 86400 mm/day.
    #---
    MM_PER_WEEK_CONVERSION = 604800.0

    #---
    # I'm guessing what you try to get from there, it seems you need a total
    # amount of rainfall over Pocatello during one week? If so, then we back to
    # the old topic: the unit of PRECTOTLAND and the meaning of the unit. The
    # long name of PRECTOTLAND is "precipitation rate over land" with unit
    # kg/m^2/s, if you consider the density of water, the unit can be converted
    # to mm/s which is in fact a unit of speed, just like mph for a car. Since
    # PRECTOTLAND has hourly temporal resolution, the value you see in the
    # original file means, in each pixel, during certain hour, rain is falling
    # at speed of X mm/s.
    #
    # Back to your question, the value of 400mm/day doesn't make too much sense
    # to me, because you add up all the "speed" during one week which hardly
    # have any physical meaning. So based on the value you currently get,
    # several calculations can be done. Assuming a pixel value X in your NetCDF
    # file, then Y=X/(7*24) gives you averaged precipitation rate during one
    # week in unit of "mm/s" ( Y*86400 if you like unit of mm/day) . If you need
    # total amount of rainfall, then Y*86400(s/day)*7(days) will be the answer.
    #---

    # Variables
    BASEFLOW    = 'BASEFLOW'
    ECHANGE     = 'ECHANGE'
    EVLAND      = 'EVLAND'
    EVPINTR     = 'EVPINTR'
    EVPSBLN     = 'EVPSBLN'
    EVPSOIL     = 'EVPSOIL'
    EVPTRNS     = 'EVPTRNS'
    FRSAT       = 'FRSAT'
    FRSNO       = 'FRSNO'
    FRUNST      = 'FRUNST'
    FRWLT       = 'FRWLT'
    GHLAND      = 'GHLAND'
    GRN         = 'GRN'
    GWETPROF    = 'GWETPROF'
    GWETROOT    = 'GWETROOT'
    GWETTOP     = 'GWETTOP'
    LAI         = 'LAI'
    LHLAND      = 'LHLAND'
    LWLAND      = 'LWLAND'
    PARDFLAND   = 'PARDFLAND'
    PARDRLAND   = 'PARDRLAND'
    PRECSNOLAND = 'PRECSNOLAND'
    PRECTOTLAND = 'PRECTOTLAND'
    PRMC        = 'PRMC'
    QINFIL      = 'QINFIL'
    RUNOFF      = 'RUNOFF'
    RZMC        = 'RZMC'
    SFMC        = 'SFMC'
    SHLAND      = 'SHLAND'
    SMLAND      = 'SMLAND'
    SNODP       = 'SNODP'
    SNOMAS      = 'SNOMAS'
    SPLAND      = 'SPLAND'
    SPSNOW      = 'SPSNOW'
    SPWATR      = 'SPWATR'
    SWLAND      = 'SWLAND'
    TELAND      = 'TELAND'
    TPSNOW      = 'TPSNOW'
    TSAT        = 'TSAT'
    TSOIL1      = 'TSOIL1'
    TSOIL2      = 'TSOIL2'
    TSOIL3      = 'TSOIL3'
    TSOIL4      = 'TSOIL4'
    TSOIL5      = 'TSOIL5'
    TSOIL6      = 'TSOIL6'
    TSURF       = 'TSURF'
    TUNST       = 'TUNST'
    TWLAND      = 'TWLAND'
    TWLT        = 'TWLT'
    WCHANGE     = 'WCHANGE'
    
    # Variables and their collections.
    VAR_TO_COLL = {BASEFLOW    : 'tavg1_2d_lnd_Nx',
                   ECHANGE     : 'tavg1_2d_lnd_Nx',
                   EVLAND      : 'tavg1_2d_lnd_Nx',
                   EVPINTR     : 'tavg1_2d_lnd_Nx',
                   EVPSBLN     : 'tavg1_2d_lnd_Nx',
                   EVPSOIL     : 'tavg1_2d_lnd_Nx',
                   EVPTRNS     : 'tavg1_2d_lnd_Nx',
                   FRSAT       : 'tavg1_2d_lnd_Nx',
                   FRSNO       : 'tavg1_2d_lnd_Nx',
                   FRUNST      : 'tavg1_2d_lnd_Nx',
                   FRWLT       : 'tavg1_2d_lnd_Nx',
                   GHLAND      : 'tavg1_2d_lnd_Nx',
                   GRN         : 'tavg1_2d_lnd_Nx',
                   GWETPROF    : 'tavg1_2d_lnd_Nx',
                   GWETROOT    : 'tavg1_2d_lnd_Nx',
                   GWETTOP     : 'tavg1_2d_lnd_Nx',
                   LAI         : 'tavg1_2d_lnd_Nx',
                   LHLAND      : 'tavg1_2d_lnd_Nx',
                   LWLAND      : 'tavg1_2d_lnd_Nx',
                   PARDFLAND   : 'tavg1_2d_lnd_Nx',
                   PARDRLAND   : 'tavg1_2d_lnd_Nx',
                   PRECSNOLAND : 'tavg1_2d_lnd_Nx',
                   PRECTOTLAND : 'tavg1_2d_lnd_Nx',
                   PRMC        : 'tavg1_2d_lnd_Nx',
                   QINFIL      : 'tavg1_2d_lnd_Nx',
                   RUNOFF      : 'tavg1_2d_lnd_Nx',
                   RZMC        : 'tavg1_2d_lnd_Nx',
                   SFMC        : 'tavg1_2d_lnd_Nx',
                   SHLAND      : 'tavg1_2d_lnd_Nx',
                   SMLAND      : 'tavg1_2d_lnd_Nx',
                   SNODP       : 'tavg1_2d_lnd_Nx',
                   SNOMAS      : 'tavg1_2d_lnd_Nx',
                   SPLAND      : 'tavg1_2d_lnd_Nx',
                   SPSNOW      : 'tavg1_2d_lnd_Nx',
                   SPWATR      : 'tavg1_2d_lnd_Nx',
                   SWLAND      : 'tavg1_2d_lnd_Nx',
                   TELAND      : 'tavg1_2d_lnd_Nx',
                   TPSNOW      : 'tavg1_2d_lnd_Nx',
                   TSAT        : 'tavg1_2d_lnd_Nx',
                   TSOIL1      : 'tavg1_2d_lnd_Nx',
                   TSOIL2      : 'tavg1_2d_lnd_Nx',
                   TSOIL3      : 'tavg1_2d_lnd_Nx',
                   TSOIL4      : 'tavg1_2d_lnd_Nx',
                   TSOIL5      : 'tavg1_2d_lnd_Nx',
                   TSOIL6      : 'tavg1_2d_lnd_Nx',
                   TSURF       : 'tavg1_2d_lnd_Nx',
                   TUNST       : 'tavg1_2d_lnd_Nx',
                   TWLAND      : 'tavg1_2d_lnd_Nx',
                   TWLT        : 'tavg1_2d_lnd_Nx',
                   WCHANGE     : 'tavg1_2d_lnd_Nx'
                  }
                  
    # Variables and their descriptions.
    VAR_TO_DESC = {BASEFLOW    : 'Unknown',
                   ECHANGE     : 'Unknown',
                   EVLAND      : 'Unknown',
                   EVPINTR     : 'Unknown',
                   EVPSBLN     : 'Unknown',
                   EVPSOIL     : 'Unknown',
                   EVPTRNS     : 'Unknown',
                   FRSAT       : 'Unknown',
                   FRSNO       : 'Unknown',
                   FRUNST      : 'Unknown',
                   FRWLT       : 'Unknown',
                   GHLAND      : 'Unknown',
                   GRN         : 'Unknown',
                   GWETPROF    : 'Unknown',
                   GWETROOT    : 'Unknown',
                   GWETTOP     : 'Soil Wetness',
                   LAI         : 'Unknown',
                   LHLAND      : 'Latent Heat Flux',
                   LWLAND      : 'Unknown',
                   PARDFLAND   : 'Unknown',
                   PARDRLAND   : 'Unknown',
                   PRECSNOLAND : 'Unknown',
                   PRECTOTLAND : 'Total Land Precipitation',
                   PRMC        : 'Unknown',
                   QINFIL      : 'Unknown',
                   RUNOFF      : 'Unknown',
                   RZMC        : 'Unknown',
                   SFMC        : 'Unknown',
                   SHLAND      : 'Sensible Heat Flux',
                   SMLAND      : 'Unknown',
                   SNODP       : 'Unknown',
                   SNOMAS      : 'Unknown',
                   SPLAND      : 'Unknown',
                   SPSNOW      : 'Unknown',
                   SPWATR      : 'Unknown',
                   SWLAND      : 'Unknown',
                   TELAND      : 'Unknown',
                   TPSNOW      : 'Unknown',
                   TSAT        : 'Unknown',
                   TSOIL1      : 'Unknown',
                   TSOIL2      : 'Unknown',
                   TSOIL3      : 'Unknown',
                   TSOIL4      : 'Unknown',
                   TSOIL5      : 'Unknown',
                   TSOIL6      : 'Unknown',
                   TSURF       : 'Surface Temperature',
                   TUNST       : 'Unknown',
                   TWLAND      : 'Unknown',
                   TWLT        : 'Unknown',
                   WCHANGE     : 'Unknown'
                  }

    # Variables and their units.
    VAR_TO_UNITS = {BASEFLOW    : 'Unknown',
                    ECHANGE     : 'Unknown',
                    EVLAND      : 'Unknown',
                    EVPINTR     : 'Unknown',
                    EVPSBLN     : 'Unknown',
                    EVPSOIL     : 'Unknown',
                    EVPTRNS     : 'Unknown',
                    FRSAT       : 'Unknown',
                    FRSNO       : 'Unknown',
                    FRUNST      : 'Unknown',
                    FRWLT       : 'Unknown',
                    GHLAND      : 'Unknown',
                    GRN         : 'Unknown',
                    GWETPROF    : 'Unknown',
                    GWETROOT    : 'Unknown',
                    GWETTOP     : 'Liters',
                    LAI         : 'Unknown',
                    LHLAND      : 'W per Meters^2',
                    LWLAND      : 'Unknown',
                    PARDFLAND   : 'Unknown',
                    PARDRLAND   : 'Unknown',
                    PRECSNOLAND : 'Unknown',
                    PRECTOTLAND : 'Millimeters per Day',
                    PRMC        : 'Unknown',
                    QINFIL      : 'Unknown',
                    RUNOFF      : 'Unknown',
                    RZMC        : 'Unknown',
                    SFMC        : 'Unknown',
                    SHLAND      : 'W per Meters^2',
                    SMLAND      : 'Unknown',
                    SNODP       : 'Unknown',
                    SNOMAS      : 'Unknown',
                    SPLAND      : 'Unknown',
                    SPSNOW      : 'Unknown',
                    SPWATR      : 'Unknown',
                    SWLAND      : 'Unknown',
                    TELAND      : 'Unknown',
                    TPSNOW      : 'Unknown',
                    TSAT        : 'Unknown',
                    TSOIL1      : 'Unknown',
                    TSOIL2      : 'Unknown',
                    TSOIL3      : 'Unknown',
                    TSOIL4      : 'Unknown',
                    TSOIL5      : 'Unknown',
                    TSOIL6      : 'Unknown',
                    TSURF       : 'Degrees',
                    TUNST       : 'Unknown',
                    TWLAND      : 'Unknown',
                    TWLT        : 'Unknown',
                    WCHANGE     : 'Unknown'
                   }

    COLL_TO_SERVICE = {'instM_3d_ana_Np' : 'M2AS',
                       'instM_3d_asm_Np' : 'M2AS',
                       'tavg1_2d_lnd_Nx' : 'M2AS'}

    TIME_INTERVAL_MONTHS = 30
    TIME_INTERVAL_WEEKS  = 7
    
	#---------------------------------------------------------------------------
	# __init__
	#---------------------------------------------------------------------------
    def __init__(self, request, logger):

        # MERRA gets its own subdirectory because it can have multiple files.
        request.destination.name =os.path.join(request.destination.name,'MERRA')
        request.save(update_fields = ['destination'])

        if not os.path.exists(request.destination.name):
            os.mkdir(request.destination.name)

        super(MerraBase, self).__init__(request, logger)

        #--- 
        # MERRA is made available periodically at the end point. Settings has
        # the most recent collection date.  MerraBase will keep its own adjusted
        # dates.
        #--- 
        earliestCollDate = \
            datetime.strptime(settings.MERRA_START_DATE, '%Y-%m-%d').date()

        latestCollDate = \
            datetime.strptime(settings.MERRA_END_DATE, '%Y-%m-%d').date()
                              
        self.startDate = self.request.startDate
        self.endDate   = self.request.endDate
        
        if earliestCollDate > self.startDate:
            self.startDate = earliestCollDate
            
        if latestCollDate < self.endDate:
            self.endDate = latestCollDate
         
        #---   
        # Intervals are a list of dates, each time interval between the start
        # and end dates.
        #---
        self.timeIntervals = None

	#---------------------------------------------------------------------------
	# awaitCompletion
	#---------------------------------------------------------------------------
    def awaitCompletion(self, sessionID):
        
        status    = None
        startTime = time.time()
        maxWait   = 60 * 60 * len(self.getVars()) # seconds

        while status != 'Completed' and status != 'Failed':

            doc = self.sendRequest(self.request.endPoint.url + \
                                   'status.php?session_id=' + sessionID)

            status = self.getSingleElemValue(doc, 'sessionStatus')

            # Wait
            time.sleep(5)
            waited = time.time() - startTime

            if waited > maxWait and status != 'Completed':

                self.getSingleElemValue(doc, 'sessionStatusDetail')

                if self.logger:

                    self.logger.info('Job has not completed in ' + \
                                     str(maxWait)                + \
                                     ' seconds, so timing out.')

                return False

        if status == 'Failed':

            self.getSingleElemValue(doc, 'sessionStatusDetail')
            
            self.logger.info('Job failed.  Ensure the server\'s IP address' + \
                             ' is registered with the MERRA server.')
            return False

        if status == 'Completed':
            self.logger.info('Job succeeded.')
            
        return True

    #---------------------------------------------------------------------------
    # formatDate
    #---------------------------------------------------------------------------
    def formatDate(self, d):
        
        return str(d.year) + str(d.month).zfill(2) + str(d.day).zfill(2)

    #---------------------------------------------------------------------------
    # getEndPointSRSs
    #---------------------------------------------------------------------------
    def getEndPointSRSs(self, endPoint):
        return [GeoRetriever.GEOG_4326]

    #---------------------------------------------------------------------------
    # getSingleElemValue
    #---------------------------------------------------------------------------
    def getSingleElemValue(self, doc, tagName):
        
        if not doc:
            raise RuntimeError("A document object must be provided.")
        
        if not tagName:
            raise RuntimeError("A tag name must be provided.")
        
        idNodes = doc.getElementsByTagName(tagName)
            
        if len(idNodes) <= 0:
            sys.stderr.write("No " + tagName + " found.\n")
            return None
            
        if len(idNodes) > 1:
            sys.stderr.write("Multiple " + tagName + "s found.\n")
            return None
            
        value = idNodes[0].firstChild.data
        
        if self.logger:
            self.logger.info(tagName + ": " + value)

        return value

    #---------------------------------------------------------------------------
    # getTimeIntervals
    #
    # These are pairs of start and end dates that are one week long.
    # [(2016-02-07, 2016-02-14), (2016-02-14, 2016-02-21), ...]
    #---------------------------------------------------------------------------
    def getTimeIntervals(self, interval = TIME_INTERVAL_WEEKS):
        
        oneInterval = timedelta(days = interval)
        intervals   = []
        cur         = self.startDate
        end         = self.endDate
        
        while cur + oneInterval < end:

            nextInterval = cur + oneInterval
            intervals.append((cur, nextInterval))
            cur = nextInterval
            
        #---
        # If the start and end dates are less than one interval apart, grab a 
        # single interval.
        #---
        if len(intervals) == 0:
            
            nextInterval = cur + oneInterval
            intervals.append((cur, nextInterval))
            cur = nextInterval
            
        return intervals
    
    #---------------------------------------------------------------------------
    # getVars
    #---------------------------------------------------------------------------
    def getVars(self):
        raise RuntimeError('This method must be overriden by derived classes.')
        
    #---------------------------------------------------------------------------
    # knowsProtocol 
    #---------------------------------------------------------------------------
    @staticmethod
    def knowsProtocol(protocol):
        
        return protocol == 'MERRA'
        
    #---------------------------------------------------------------------------
    # orderMerraFile
    #
    # variableFileName = PRECTOTLAND_sum_20150103-20150110.xyz
    #---------------------------------------------------------------------------
    def orderMerraFile(self, variableFileName):
        
        if variableFileName == None:
            raise RuntimeError('variableFileName was null.')

        path, fileName = os.path.split(variableFileName)
        fileName, ext  = os.path.splitext(fileName)
        fileNameParts  = fileName.split('_')
        var            = fileNameParts[0]
        op             = fileNameParts[1]
        dates          = fileNameParts[2]
        coll           = MerraBase.VAR_TO_COLL[var]
        service        = MerraBase.COLL_TO_SERVICE[coll]
        
        if self.logger:
            
            self.logger.info('Service:    ' + str(service))
            self.logger.info('Collection: ' + str(coll))
            self.logger.info('Variable:   ' + str(var))
            self.logger.info('Operation:  ' + str(op))
            
        # bbox = self.retrievalBbox.expandByPercentage(35)
        # minX = bbox.ul().GetX()
        # minY = bbox.lr().GetY()
        # maxX = bbox.lr().GetX()
        # maxY = bbox.ul().GetY()
        minX, maxY, maxX, minY =                       \
            self.expandByPercentage(self.retrievalUlx, \
                                    self.retrievalUly, \
                                    self.retrievalLrx, \
                                    self.retrievalLry, \
                                    self.retrievalSRS, \
                                    35)

        #---
        # These fire sites can be so small that the MERRA file returned does
        # not have enough ground control points (GCPs) for GDAL to
        # successfully convert it to GeoTif.  Add a buffer to the requested
        # box large enough to get sufficient GCPs.  Do this in geographic
        # coordinates eliminate exceeding the UTM zone bounds.
        #---
        gMinX = float(minX - 1)
        gMaxX = float(maxX + 1)
        gMinY = float(minY - 1)
        gMaxY = float(maxY + 1)

        # Order the image.
        startDate, endDate = dates.split('-')
        
        orderURL = self.request.endPoint.url + \
                   'order.php?' + \
                   '&collection=' + coll + \
                   '&end_date=' + str(endDate) + \
                   '&end_level=13' + \
                   '&job_name=WRANGLER' + \
                   '&max_lat=' + str(gMaxY) + \
                   '&max_lon=' + str(gMaxX) + \
                   '&min_lat=' + str(gMinY) + \
                   '&min_lon=' + str(gMinX) + \
                   '&operation=' + op + \
                   '&start_level=13' + \
                   '&service=' + service + \
                   '&service_request=GetVariableByCollection_Operation_TimeRange_SpatialExtent_VerticalExtent' + \
                   '&start_date=' + str(startDate) + \
                   '&variable_list=' + var
                   
        doc       = self.sendRequest(orderURL)
        sessionID = self.getSingleElemValue(doc, 'sessionId')
        
        return sessionID

    #---------------------------------------------------------------------------
    # retrieveOne
    #
    # fullyQualifiedPredFileName = /path/to/PRECTOTLAND_sum.csv
    #
    # constituents = [PRECTOTLAND_sum_20150103-20150110.xyz,
    #                 PRECTOTLAND_sum_20150110-20150117.xyz,
    #                 PRECTOTLAND_sum_20150117-20150124.xyz]
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        if os.path.exists(constituentFileName):
            return constituentFileName
            
        # Order all the MERRA files.
        sessionIDs = {}
        xyzName = None
        
        for constituent in fileList:

            if self.logger:
                self.logger.info('Running ' + os.path.basename(constituent))

            name, ext = os.path.splitext(constituent)
            xyzName = name + '.xyz'
            
            # Only order the file, if it doesn't exist.
            if not os.path.exists(constituent):
                
                sessionID = self.orderMerraFile(constituent)
                sessionIDs[sessionID] = constituent

                if self.logger:
                    self.logger.info('Ordering ' +os.path.basename(constituent))

            try:
                # To ensure it is re-finished below, remove all xyz files.
                os.path.remove(xyzName)

            except:
                pass

        # As they complete, finish their processing.
        for key in sessionIDs.keys():
            
            if self.logger:
                self.logger.info('Finishing ' + key)

            if self.awaitCompletion(key):
                
                self.finishMerraFile(sessionIDs[key], key)
        
            else:
                raise RuntimeError('MERRA collection, ' + \
                                   sessionIDs[key]      + \
                                   ' failed.')
          
        return constituentFileName

    #---------------------------------------------------------------------------
    # sendRequest
    #---------------------------------------------------------------------------
    def sendRequest(self, sendURL):
        
        if self.logger:
            self.logger.info('send URL = ' + sendURL)
        
        # Send request, then parse the response for the session ID.
        doc = minidom.parse(urllib2.urlopen(sendURL))
                
        if self.logger:
            self.logger.info('Request response: ' + doc.toprettyxml())
            
        return doc
    


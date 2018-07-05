
import collections
import csv
from datetime import datetime
import logging
import os
import urllib2

# Handle plotting for a process with no display.
if not 'DISPLAY' in os.environ:
    import matplotlib
    matplotlib.use('Agg')

import matplotlib.pyplot as plt

from django.contrib.sites.models import Site
from django.template.response import SimpleTemplateResponse

from MerraBase import MerraBase

#-------------------------------------------------------------------------------
# class MerraRetriever
#-------------------------------------------------------------------------------
class MerraRetriever (MerraBase):

	#---------------------------------------------------------------------------
	# __init__
	#---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        super(MerraRetriever, self).__init__(request, logger, numProcesses)
        self.timeIntervals = self.getTimeIntervals()

    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):

        plotFiles = []
        
        for outFile in outFiles.keys():
            
            tableDict = {}
            aggFiles = outFiles[outFile]
            
            for aggFile in aggFiles:

                # If a PF doesn't exist, the entire predictor fails.
                if not os.path.exists(aggFile):
                    return
                
                with open(aggFile, 'r') as cFd:
            
                    for line in cFd:

                        # Read one line.
                        x, y, value = line.strip().split(' ')

                        # Establish a key for this x_y.
                        key = str(x) + '_' + str(y)

                        if not tableDict.has_key(key):
                            tableDict[key] = {'x': x, 'y': y}

                        # Get the date range.
                        cNoExt, ext = os.path.splitext(aggFile)
                        name = os.path.basename(cNoExt)
                        dateRange = str(name.split('_')[2])
                
                        # Get the value. 
                        value = float(value)
                        
                        if MerraBase.PRECTOTLAND in aggFile: # in/day
                            value = value * MerraBase.MM_PER_WEEK_CONVERSION
                                    
                        elif MerraBase.TSURF in aggFile: # to degrees
                            value = 1.8 * (value - 273.15) + 32.0
                            
                        tableDict[key][dateRange] = value
                        
                if not MerraBase.KEEP_XYZ_FILES:
                    os.remove(aggFile)

            #---
            # tableDict = 
            # {43_24: {'x':43, 'y':24, '20160101-20160108':80,
            #                          '20160108-20160115': 41}
            #  43_25: {'x':43, 'y':25, '20160101-20160108':80,
            #                          '20160108-20160115': 41}}
            #
            # Sort by location.
            #---
            tableDict = collections.OrderedDict(sorted(tableDict.items()))
            
            #---
            # Remove the top-level keys, as they are no longer needed.
            #
            # rows = 
            # [{'x':43, 'y':24, '20160101-20160108':80, '20160108-20160115':41}
            #  {'x':43, 'y':25, '20160101-20160108':80, '20160108-20160115':41}]
            #---
            rows = tableDict.values()
    
            self.writeCsv(rows, outFile)
            plotFiles.append(self.plot(rows, outFile))

        baseName = os.path.dirname(outFile)
        reportFile = os.path.join(baseName, 'MERRA_Report.html')
        self.createReport(reportFile, plotFiles)
        
        return reportFile
                
    #---------------------------------------------------------------------------
    # computeAverages
    #
    # [{'x':43, 'y':24, '20160101-20160108':80, '20160108-20160115': 41}
    #  {'x':43, 'y':25, '20160101-20160108':80, '20160108-20160115': 41}]
    #---------------------------------------------------------------------------
    def computeAverages(self, rows):
        
        #---
        # Create a structure to hold the sum and count for each date.
        # {'20160101-20160108' : (0, 0), '20160108-20160115' : (0, 0)}
        #---
        counts = {}
        
        for row in rows:
            
            for key in row.iterkeys():
                
                if key not in ['x', 'y']:

                    if not counts.has_key(key):
                        counts[key] = (0.0, 0)
                        
                    total       = counts[key][0] + row[key]
                    count       = counts[key][1] + 1
                    counts[key] = (total, count)

        #---
        # Compute the averages for each date range.
        # {'20160101-20160108' : 82, '20160108-20160115' : 44}
        #---
        averages = {}
        
        for key in counts.iterkeys():
            
            count = counts[key][1]
            
            if count > 0:
                averages[key] = counts[key][0] / count
                
        return averages

    #---------------------------------------------------------------------------
    # createReport
    #---------------------------------------------------------------------------
    def createReport(self, reportFile, plotFiles):
        
        rptDate = datetime.today().strftime('%Y-%m-%d %I:%M:%S %p')
        context = {'dateTime' : rptDate}
        site    = 'http://' + Site.objects.get_current().domain + '/sites'
        
        for plotFile in plotFiles:

            baseName      = os.path.basename(plotFile)
            name, ext     = os.path.splitext(baseName)
            context[name] = plotFile
            
        resp = SimpleTemplateResponse('MerraReport.html', context)
        resp.render()
        
        with open(reportFile, 'w') as fd:
            fd.write(resp.content)
        
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
        
        # Convert to ASCII Gridded XYZ format: x, y, value.
        cmd = 'gdal_translate -of XYZ "' + ncName + '" "' + collectionFile + '"'

        if self.logger:
            self.logger.info("Command:  " + cmd)

        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('Failed to convert NC to XYZ.')
            
        if not MerraBase.KEEP_NC_FILES:
            os.remove(ncName)

    #---------------------------------------------------------------------------
    # getVars
    #---------------------------------------------------------------------------
    def getVars(self):

        return [(MerraBase.PRECTOTLAND, 'avg'),
                (MerraBase.TSURF,       'min'), 
                (MerraBase.TSURF,       'max'), 
                (MerraBase.TSURF,       'avg'),
                (MerraBase.GWETTOP,     'avg'), 
                (MerraBase.SHLAND,      'avg'), 
                (MerraBase.LHLAND,      'avg')] 

    #---------------------------------------------------------------------------
    # listConstituents
    #
    # {'PRECTOTLAND_sum.csv' : 
    #      [PRECTOTLAND_sum_20150103-20150110.xyz,
    #       PRECTOTLAND_sum_20150110-20150117.xyz,
    #       PRECTOTLAND_sum_20150117-20150124.xyz,
    #  'TSURF_min.csv' : 
    #      [TSURF_min_20150103-20150110.xyz,
    #       TSURF_min_20150110-20150117.xyz,
    #       TSURF_min_20150117-20150124.xyz]
    # }
    #---------------------------------------------------------------------------
    def listConstituents(self):

        constituentDict = {}

        for var in iter(self.getVars()):

            constituents = []
            baseName = var[0] + '_' + var[1]
            
            csvName = os.path.join(self.request.destination.name, 
                                   baseName + '.csv')
            
            constituentDict[csvName] = constituents

            for sWeek, eWeek in self.timeIntervals:

                week1    = self.formatDate(sWeek)
                week2    = self.formatDate(eWeek)
                weekFile = baseName + '_' + week1 + '-' + week2 + '.xyz'
                
                constituents.append(os.path.join(self.request.destination.name, 
                                                 weekFile))

        return constituentDict

    #---------------------------------------------------------------------------
    # plot
    #
    # http://matplotlib.org/api/pyplot_api.html
    #
    # [{'x':43, 'y':24, '20160101-20160108':80, '20160108-20160115': 41}
    #  {'x':43, 'y':25, '20160101-20160108':80, '20160108-20160115': 41}]
    #---------------------------------------------------------------------------
    def plot(self, rows, csvFileName):

        # {'20160101-20160108' : 82, '20160108-20160115' : 44}
        unsortedAvgs = self.computeAverages(rows)
        
        avgs = collections.OrderedDict(sorted(unsortedAvgs.items(), \
                                       key=lambda t: t[0]))        

        # Plot the points.
        plt.close('all')
        plt.plot(avgs.values())

        # Add the x-axis labels and title.
        locs, labels = plt.xticks()
        dates = [key.split('-')[0] for key in avgs.keys()]
        plt.xticks(locs, dates, rotation = 'vertical')

        label = 'Date Range: ' + str(self.startDate) + ' - ' + str(self.endDate)
        plt.xlabel(label)
        
        # Put units on the y axis.
        var = self.varFromFileName(csvFileName)

        yLabel = MerraBase.VAR_TO_DESC[var] + ' in ' + \
                 MerraBase.VAR_TO_UNITS[var]
                 
        plt.ylabel(yLabel)
        
        # This adjusts the borders for the labels.
        plt.tight_layout()

        # Create the plot file.
        name, ext = os.path.splitext(csvFileName)
        plotName = name + '.png'
        plt.savefig(plotName)

        return plotName
        
    #---------------------------------------------------------------------------
    # varFromFileName
    #---------------------------------------------------------------------------
    def varFromFileName(self, fileName):
        
        var = None
        
        if MerraBase.GWETTOP in fileName:
            var = MerraBase.GWETTOP
        
        elif MerraBase.LHLAND in fileName:
            var = MerraBase.LHLAND
        
        elif MerraBase.PRECTOTLAND in fileName:
            var = MerraBase.PRECTOTLAND
        
        elif MerraBase.SHLAND in fileName:
            var = MerraBase.SHLAND

        elif MerraBase.TSURF in fileName:
            var = MerraBase.TSURF
            
        return var
        
    #---------------------------------------------------------------------------
    # writeCsv
    #
    # [{'x':43, 'y':24, '20160101-20160108':80, '20160108-20160115': 41}
    #  {'x':43, 'y':25, '20160101-20160108':80, '20160108-20160115': 41}]
    #---------------------------------------------------------------------------
    def writeCsv(self, rows, csvFileName):

        with open(csvFileName, 'w') as csvfile:
            
            # Create the header row.
            fieldNames = ['x', 'y']
            
            for key in sorted(rows[0]):
                if key != 'x' and key != 'y':
                    fieldNames.append(key)
            
            # Create the CSV writer.
            writer = csv.DictWriter(csvfile, fieldnames = fieldNames)
            writer.writeheader()

            # Write the rows.
            for row in rows:
                writer.writerow(row)


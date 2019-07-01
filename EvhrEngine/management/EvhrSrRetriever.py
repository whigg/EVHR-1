import os

from django.conf import settings

from EvhrEngine.management.DgFile import DgFile
from EvhrEngine.management.EvhrToaRetriever import EvhrToaRetriever
from EvhrEngine.management.FootprintsQuery import FootprintsQuery
from EvhrEngine.models import EvhrScene

#-------------------------------------------------------------------------------
# class EvhrSrRetriever
#-------------------------------------------------------------------------------
class EvhrSrRetriever(EvhrToaRetriever):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, request, logger, numProcesses):

        # Initialize the base class.
        super(EvhrSrRetriever, self).__init__(request, logger, numProcesses)

        self.srDir = os.path.join(self.request.destination.name, '6-sr')
        
        if not os.path.exists(self.srDir):
            os.mkdir(self.srDir)

    #---------------------------------------------------------------------------
    # aggregate
    #---------------------------------------------------------------------------
    def aggregate(self, outFiles):

        # This is where the mosaic data set is created from the set of ToAs.
        pass

    #---------------------------------------------------------------------------
    # getScenes
    #---------------------------------------------------------------------------
    def getScenes(self, request, ulx, uly, lrx, lry, srs):

        # Check if there are already scenes associated with this request.
        evhrScenes = EvhrScene.objects.filter(request = request)
        sceneFiles = []

        if evhrScenes:
            
            sceneFiles = self._validateScenes(evhrScenes)
            
            for sceneFile in sceneFiles:
                
                dgf = DgFile(sceneFile)
                
                if dgf.isPanchromatic():
                    
                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            sceneFile.fileName + \
                                            ' is being skipped because' + \
                                            ' it is panchromatic.')
                                            
                if dgf.sensor() != 'WV02' and dgf.sensor() != 'WV03':

                    if self.logger:
                        self.logger.warning('Scene ' + \
                                            sceneFile.fileName + \
                                            ' is being skipped because' + \
                                            ' it is not WV02 or WV03.')
                                            
        else:
            
            fpScenes = None
            fpq = FootprintsQuery(logger=self.logger)
            fpq.addAoI(ulx, uly, lrx, lry, srs)
            fpq.setMinimumOverlapInDegrees()
            fpq.addSensors(['WV02', 'WV03'])
            fpq.setPanchromaticOff()

            maxScenes = EvhrToaRetriever.MAXIMUM_SCENES
            
            if hasattr(settings, 'MAXIMUM_SCENES'):
                maxScenes = min(maxScenes, settings.MAXIMUM_SCENES)
                
            fpq.setMaximumScenes(maxScenes)
            fpScenes = fpq.getScenes()
            self._fpScenesToEvhrScenes(fpScenes)
            sceneFiles = [fps.fileName() for fps in fpScenes]
                
        sceneFiles.sort()
        
        return sceneFiles

    #---------------------------------------------------------------------------
    # listConstituents
    #
    # Constituent: SR file
    # Files:  scenes for a single ToA strip
    #---------------------------------------------------------------------------
    def listConstituents(self):

        # Query for scenes.
        scenes = self.getScenes(self.request,
                                self.retrievalUlx,
                                self.retrievalUly,
                                self.retrievalLrx,
                                self.retrievalLry,
                                self.retrievalSRS)

        if not scenes and self.logger:
            self.logger.error('No multispectral scenes for WV2 or WV3.')

        # Aggregate the scenes into ToAs.
        toas = {}
        
        for scene in scenes:
            
            dgf = DgFile(scene, self.logger)
            stripID = dgf.getStripName()
            toaName = os.path.join(self.toaDir, stripID + '-toa.tif')

            if not toas.has_key(toaName):
                toas[toaName] = []
                
            toas[toaName].append(scene)
            
        # Aggregate the ToAs into SRs and create the SR input file.
        constituents = {}
        srInputFileName = os.path.join(self.srDir, 'srInput.txt')

        with open(srInputFileName, 'aw+') as f:
            
            for toa in toas:
                
                toaBaseName = os.path.basename(toa).replace('-toa', '')
                srName = os.path.join(self.srDir, toaBaseName)
                constituents[srName] = toas[toa]
                f.write(os.path.splitext(os.path.basename(toaBaseName))[0]+'\n')

        return constituents

    #---------------------------------------------------------------------------
    # retrieveOne
    #---------------------------------------------------------------------------
    def retrieveOne(self, constituentFileName, fileList):

        # Create the ToA.
        stripName = DgFile(fileList[0], self.logger).getStripName()
        stripBandList = self.scenesToStrip(stripName, fileList)

        toaName = os.path.join(self.toaDir,
                               os.path.basename(constituentFileName))

        self.processStrip(stripBandList, toaName)
            
        # Bin file: extract the ToA's raster.
        toaBin = toaName.replace('.tif', '.bin')
        
        # Meta file
        toaMeta = self.writeMeta(toaName)
        
        # Wv2 file
        toaWv2 = toaName.replace('.tif', '.wv2')
        
    #---------------------------------------------------------------------------
    # writeMeta
    #---------------------------------------------------------------------------
    def writeMeta(self, toaName):
        
        dgFile = DgFile(toaName)

        # Time-related fields.
        date = dgFile.firstLineTime().strftime('%Y-%m-%d')
        hour = dgFile.firstLineTime().strftime('%H')
        minute = dgFile.firstLineTime().strftime('%M')
        minutes = float(hour) * 60.0 + float(minute)

        # Angles, elevations, etc.
        SZA = 90.0 - dgFile.meanSunElevation()
        VZA = 90.0 - dgFile.meanSatelliteElevation()
        SAZ = dgFile.meanSunAzimuth()
        VAZ = dgFile.meanSatelliteAzimuth()
        relAZ = SAZ - VAZ
        
        # Projection information
        lat = float(dgFile.imdTag.find('BAND_B//LRLAT'))
        lon = float(dgFile.imdTag.find('BAND_B//LRLON'))
        projWords = dgFile.srs.GetAttrValue('projcs').split()
        xScale = dgFile.dataset.GetGeoTransform()[1]
        yScale = dgFile.dataset.GetGeoTransform()[5]
        ulx = dgFile.dataset.GetGeoTransform()[0]
        uly = dgFile.dataset.GetGeoTransform()[3]
        
        # Write the file.
        toaMetaFileName = toaName.replace('.tif', '.meta')

        with open(toaMetaFileName, 'w') as f:
            
            f.write(date)
            f.write('   %d\n' % minutes)
            f.write('%f   %f\n' % (lat, lon))
            f.write('%f   %f   %f   %f   %f \n' % (SZA, VZA, SAZ, VAZ, relAZ))
            
            f.write('%d   %d\n' % (dgFile.dataset.RasterYSize, 
                                   dgFile.dataset.RasterXSize))
            
            f.write('%s   %s\n' % (projWords[-1][0:-1], projWords[-1][-1]))
            f.write('%f   %f   %f   %f\n' % (ulx, xScale, uly, yScale))
            f.write(dgFile.dataset.GetProjection())

        return toaMetaFileName
        
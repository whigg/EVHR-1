
import os

#-------------------------------------------------------------------------------
# class Orthorectify
#
# Directory Structure
# - outDir directory
#     - bandFiles directory
#     - orthos directory
#     - clippedDEM.tif
#     - final-output-ortho.tif
#
# The starting point for this class is processScene.
#-------------------------------------------------------------------------------
class Orthorectify(object):

    DEM = '/att/gpfsfs/briskfs01/ppl/mwooten3/Myanmar/Myanmar_SRTM_DEM_30m.tif')

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, outDir, logger):
        
        # Validate the output directory.
        if not outDir:
            raise RuntimeError('An output directory must be specified.')
            
        if not os.path.isdir(outDir)
            raise RuntimeError(str(outDir) + ' must be a directory.')
            
        self.clippedDEMs = {}
        self.logger      = logger
        self.outDir      = outDir
        
    #---------------------------------------------------------------------------
    # clipDEM
    #---------------------------------------------------------------------------
    def clipDEM(self, ulx, uly, lrx, lry, srs):
        
        # If there is already a clipped DEM for this bounding box, use it.
        key = str(ulx) + '-' + \
              str(uly) + '-' + \
              str(lrx) + '-' + \
              str(lry) + '-' + \
              srs.ExportToProj4()
              
        if key in self.clippedDEMs:
            return self.clippedDEMs[key]
        
        # Ensure the clippedDEMs subdirectory exists.
        clipDir = os.path.join(self.outDir, 'clippedDEMs')
        
        if not os.path.exists(clipDir):
            os.mkdir(clipDir)
        
        print '******** MUST EXTEND BBOX BEFORE CLIPPING *********'
        
        # Clip the DEM.
        clippedDemName = os.path.join(clipDir, key + '.tif')
        
        cmd = 'gdalwarp'                       + \
              ' -te '                          + \
              str(ulx) + ' '                   + \
              str(lry) + ' '                   + \
              str(lrx) + ' '                   + \
              str(uly)                         + \
              ' -te_srs'                       + \
              ' "' + srs.ExportToProj4() + '"' + \
              ' ' + DEM                        + \
              ' ' + clippedDemName
              
        self.runSystemCmd(cmd)
        self.clippedDEMS[key] = clippedDemName
        
        return clippedDemName
              
    #---------------------------------------------------------------------------
    # extractBands
    #---------------------------------------------------------------------------
    def extractBands(self, nitfFile):
        
        # Make a directory for temporary band files.
        tempDir = os.path.join(self.outDir, 'bandFiles')

        if not os.path.exists(tempDir):
            os.mkdir(tempDir)
            
        # Get the bands to use.
        bands = ['1', '2', '3', '4'] if nitfFile.numBands() == 8 \
                else ['2', '3', '5', '7']

        # Extract the bands.
        bandFiles = []

        for band in bands:
            
            baseName = os.path.basename(nitfFile).replace('.ntf', \
                                                          'b' + band + '.tif')
                                                          
            tempBandFile = os.path.join(tempDir, baseName)
            
            cmd = 'gdal_translate'          + \
                  ' -b ' + band             + \
                  ' -a_nodata 0'            + \
                  ' ' + nitfFile.fileName() + \
                  ' ' + tempBandFile
                  
            self.runSystemCmd(cmd)

        return bandFiles
        
    #---------------------------------------------------------------------------
    # orthoOne
    #---------------------------------------------------------------------------
    def orthoOne(self, nitfFile):
        
        clippedDEM = self.clipDEM(nitfFile.ulx(),
                                  nitfFile.uly(),
                                  nitfFile.lrx(),
                                  nitfFile.lry(),
                                  nitfFile.srs())
                                
        # Ensure the orthos directory exists.  
        orthoDir = os.path.join(self.outDir, 'orthos')
        
        if not os.path.exists(orthoDir):
            os.mkdir(orthoDir)

        # Orthorectify.
        baseName = os.path.basename(nitfFile).replace('.ntf', '-ortho.tif')
        orthoFile = os.path.join(orthoDir, baseName)
        
        cmd = 'mapproject --nodata-value 0 --threads=2 -t rpc' + \
              ' --mpp=2'                                       + \
              ' ' + clippedDEM                                 + \
              ' ' + nitfFile                                   + \
              ' ' + nitfFile                                   + \
              ' ' + orthoFile

        self.runSystemCmd(cmd)
        
        return orthoFile
        
    #---------------------------------------------------------------------------
    # processScene
    #---------------------------------------------------------------------------
    def processScene(self, inputFile):

        # Get the output name to see if it exists.
        bname      = os.path.basename(inputFile).replace('.ntf', '-ortho.tif')
        orthoFinal = os.path.join(self.outDir, bname)
        
        # If the output file exists, don't bother running it again.
        if os.path.exists(orthoFinal):
            return orthoFinal

        # The output does not exist, so create it.
        nitfFile  = NitfFile(inputFile)
        orthoFile = None
        
        if nitfFile.isMultispectral():
            
            bandFiles  = self.extractBands(nitfFile)
            orthoBands = []
            
            for bandFile in bandFiles:
                orthoBands.append(self.orthoOne(bandFile))
                
            orthoFile = self.mergeBands(orthoBands)
            
        elif nitfFile.isPan():
            
            orthoFile = self.orthoOne(nitfFile)
            
        else:
            raise RuntimeError('Unable to determine if ' + 
                               str(inputFile) + 
                               ' is panchromatic or multispectral.')
                     
        return orthoFile

    #---------------------------------------------------------------------------
    # runSystemCmd
    #---------------------------------------------------------------------------
    def runSystemCmd(self, cmd):
        
        if not cmd:
            return
            
        if self.logger:
            self.logger.info('Command: ' + cmd)

        status = os.system(cmd)

        if status != 0:
            raise RuntimeError('System command failed.')
        

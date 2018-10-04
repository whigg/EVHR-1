import os
import numpy as np
from datetime import datetime
from osgeo import gdal
from EvhrEngine.management.DgFile import DgFile

from EvhrEngine.management.SystemCommand import SystemCommand
from django.core.management.base import BaseCommand
from django.conf import settings

#-------------------------------------------------------------------------------
# class TOA
#-------------------------------------------------------------------------------
class TOA():

    """ New TOA calculation is a bit different from the old. Using gains and
    offsets in addition to solar exoatmospheric irradiance (calibration coeff)

    L = gain * orthoDN * (abscalFactor/bandwidth) + offset --> image
    Reflectance = (L * earthSunDist^2 * pi)/ (calCoeff * cos(sunAngle)) -->image
    Then scale by 10000

    So to obtain Reflectance image in one step:

    Refl = 10000*
    [(((gain * orthoDN * (abscalFactor/bandwidth) + offset) * earthSunDist^2 * pi))/ (calCoeff * cos(sunAngle))]

    """

    # Coefficient values are list of: Calibration coeff, gain, and offset
    # Using Thuillier 2003 cal vals

    CALIBRATION_COEFF_DICT = {
    'QB02_BAND_P':[1370.92,0.870,-1.491],
    'QB02_BAND_B':[1949.59,1.105,-2.820],
    'QB02_BAND_G':[1823.64,1.071,-3.338],
    'QB02_BAND_R':[1553.78,1.060,-2.954],
    'QB02_BAND_N':[1102.85,1.020,-4.722],
    'WV01_BAND_P':[1478.62,1.016,-1.824],
    'WV02_BAND_P':[1571.36,0.942,-2.704],
    'WV02_BAND_C':[1773.81,1.151,-7.478],
    'WV02_BAND_B':[2007.27,0.988,-5.736],
    'WV02_BAND_G':[1829.62,0.936,-3.546],
    'WV02_BAND_Y':[1701.85,0.949,-3.564],
    'WV02_BAND_R':[1538.85,0.952,-2.512],
    'WV02_BAND_RE':[1346.09,0.974,-4.120],
    'WV02_BAND_N':[1053.21,0.961,-3.300],
    'WV02_BAND_N2':[856.599,1.002,-2.891],
    'WV03_BAND_P':[1574.41,0.950,-3.629],
    'WV03_BAND_C':[1757.89,0.905,-8.604],
    'WV03_BAND_B':[2004.61,0.940,-5.809],
    'WV03_BAND_G':[1830.18,0.938,-4.996],
    'WV03_BAND_Y':[1712.07,0.962,-3.649],
    'WV03_BAND_R':[1535.33,0.964,-3.021],
    'WV03_BAND_RE':[1348.08,1.000,-4.521],
    'WV03_BAND_N':[1055.94,0.961,-5.522],
    'WV03_BAND_N2':[858.77,0.978,-2.992],
    'GE01_BAND_P':[1610.73,0.970,-1.926],
    'GE01_BAND_B':[1993.18,1.053,-4.537],
    'GE01_BAND_G':[1828.83,0.994,-4.175],
    'GE01_BAND_R':[1491.49,0.998,-3.754],
    'GE01_BAND_N':[1022.58,0.994,-3.870],
    'IK01_BAND_P':[1353.25,0.907,-4.461],
    'IK01_BAND_B':[1921.26,1.073,-9.699],
    'IK01_BAND_G':[1803.28,0.990,-7.937],
    'IK01_BAND_R':[1517.76,0.940,-4.767],
    'IK01_BAND_N':[1145.8,1.043,-8.869]
    }


    #---------------------------------------------------------------------------
    # calcEarthSunDist()
    #---------------------------------------------------------------------------
    @staticmethod
    def calcEarthSunDist(dt):

        # Astronomical Units (AU), should have a value between 0.983 and 1.017
        year, month, day, hr, minute, sec = dt.year, dt.month, dt.day, \
                                                dt.hour, dt.minute, dt.second

        ut = hr + (minute/60.) + (sec/3600.)
        if month <= 2:
            year = year - 1
            month = month + 12
        a = int(year/100.)
        b = 2 - a + int(a/4.)
        jd = int(365.25*(year+4716)) + int(30.6001*(month+1)) + day + (ut/24) \
                                                                    + b - 1524.5
        g = 357.529 + 0.98560028 * (jd-2451545.0)
        earthSunDistance = 1.00014 - 0.01671 * np.cos(np.radians(g)) - 0.00014 \
                                                    * np.cos(np.radians(2*g))

        return earthSunDistance

    #---------------------------------------------------------------------------
    # calcToaReflectance()
    #---------------------------------------------------------------------------
    @staticmethod
    def calcToaReflectance(orthoBandFile, toaBandFile, logger = None):

        dgOrthoFile = DgFile(orthoBandFile)

        bandName = dgOrthoFile.getBandName()
        key = '{}_{}'.format(dgOrthoFile.sensor(), bandName)
        calCoeff, gain, offset = TOA.CALIBRATION_COEFF_DICT[key]

        sunAngle = 90.0 - dgOrthoFile.meanSunElevation()
        earthSunDist = TOA.calcEarthSunDist(dgOrthoFile.firstLineTime())

        print calCoeff, gain, offset
        print dgOrthoFile.abscalFactor(bandName)
        print dgOrthoFile.effectiveBandwidth(bandName)
        print earthSunDist
        print sunAngle        

        import pdb; pdb.set_trace()

        calc = "10000 * [((({}*var_0*({}/{})+{})*{}*{})) / ({}*{})]" \
                .format(gain, dgOrthoFile.abscalFactor(bandName), \
                 dgOrthoFile.effectiveBandwidth(bandName), offset, \
                 earthSunDist**2, np.pi, calCoeff, np.cos(np.radians(sunAngle)))                   
        
        print calc
        # APPLY TO IMAGE_CALC HERE
        cmd = '/opt/StereoPipeline/bin/image_calc -c "{}" {} -d int16 \
              --output-nodata-value {} -o {}'.format(calc, orthoBandFile, \
                                       settings.NO_DATA_VALUE, toaBandFile)
        
        print cmd
        #toaRadianceCoeff = float(dgFile.abscalFactor(bandName)) \
        #                            / float(dgFile.effectiveBandwidth(bandName))

        #toaReflectanceCoeff = (toaRadianceCoeff * (earthSunDistance**2 * np.pi)\
        #            / (calibrationCoeff * np.cos(np.radians(sunAngle)))) * 10000


    #---------------------------------------------------------------------------
    # run()
    #---------------------------------------------------------------------------
    @staticmethod
    def run(orthoBandFile, outputDir, dgFileName, logger = None):
#        import pdb; pdb.set_trace()
        #dgFile = DgFile(dgFileName)

        #dataset = gdal.Open(orthoBandFile, gdal.GA_ReadOnly)
        #if not dataset:
        #    raise RuntimeError("Could not open {}".format(orthoBandFile))
        #bandName = dataset.GetMetadataItem('bandName')
        #dataset = None

        #toaReflectanceCoeff = TOA.calcToaReflectanceCoeff(dgFile, bandName)

        baseName = os.path.basename(orthoBandFile).replace('.tif', '-toa.tif')
        toaBandFile = os.path.join(outputDir, baseName)

        if not os.path.isfile(toaBandFile):

            try: # new function calcToaReflectance creates toaBandFile
                TOA.calcToaReflectance(orthoBandFile, toaBandFile, logger)
 
            except:
                if logger:
                    logger.error('TOA failed for {}'.format(orthoBandFile))
            
                return None  

            # status = os.system(cmd)
            #
            # if status != 0 or not os.path.exists(toaBandFile):
            #
            #     if logger:
            #         logger.info('Command: ' + str(cmd))
            #
            #     else:
            #         print 'Command: ' + str(cmd)
            #
            #     raise RuntimeError('ToA failed.')

           
        return toaBandFile

#-------------------------------------------------------------------------------
# class Command
#-------------------------------------------------------------------------------
class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('-o', help = 'Full path to output directory.')
        parser.add_argument('-b', help = 'Full path to band file.')
        parser.add_argument('-n', help = 'Full path to NITF file')


    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        TOA.run(options['b'], options['o'], options['n'])



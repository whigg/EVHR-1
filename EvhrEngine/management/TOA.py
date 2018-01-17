import os
import numpy as np
from datetime import datetime
from osgeo import gdal

class TOA:

    #* general questions/comments:
    #* what's the correct way to pass through variables such as orthoBand and output dir?
    #* correct way to do the methods etc (i.e. &staticmethod) ?
    #* should i be trying to avoid using dgFile/DgFile or what?

    #* where does this go? These values may change at some point
    calibrationCoeffDict = {
    'QB02_BAND_P':1381.79,
    'QB02_BAND_B':1924.59,
    'QB02_BAND_G':1843.08,
    'QB02_BAND_R':1574.77,
    'QB02_BAND_N':1113.71,
    'WV01_BAND_P':1487.54715,
    'WV02_BAND_P':1580.8140,
    'WV02_BAND_C':1758.2229,
    'WV02_BAND_B':1974.2416,
    'WV02_BAND_G':1856.4104,
    'WV02_BAND_Y':1738.4791,
    'WV02_BAND_R':1559.4555,
    'WV02_BAND_RE':1342.0695,
    'WV02_BAND_N':1069.7302,
    'WV02_BAND_N2':861.2866,
    'WV03_BAND_P':1616.4508,
    'WV03_BAND_C':1544.5748,
    'WV03_BAND_B':1971.4957,
    'WV03_BAND_G':1821.7494,
    'WV03_BAND_Y':1779.2849,
    'WV03_BAND_R':1586.8104,
    'WV03_BAND_RE':1320.2137,
    'WV03_BAND_N':1088.7935,
    'WV03_BAND_N2':777.5231,
    'GE01_BAND_P':1617,
    'GE01_BAND_B':1960,
    'GE01_BAND_G':1853,
    'GE01_BAND_R':1505,
    'GE01_BAND_N':1039,
    'IK01_BAND_P':1375.8,
    'IK01_BAND_B':1930.9,
    'IK01_BAND_G':1854.8,
    'IK01_BAND_R':1556.5,
    'IK01_BAND_N':1156.9
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
    # calcToaReflectanceCoeff()
    #---------------------------------------------------------------------------
    def calcToaReflectanceCoeff(dgFile, bandName):

        key = '{}_{}'.format(dgFile.sensor, bandName)
        calibrationCoeff = calibrationCoeffDict[key]

        sunAngle = 90.0 - dgFile.meanSunElevation
        earthSunDistance = TOA.calcEarthSunDist(dgFile.firstLineTime) #* TOA. ??

        toaRadianceCoeff = float(dgFile.abscalFactor) \
                                            / float(dgFile.effectiveBandwidth)

        toaReflectanceCoeff = (toaRadianceCoeff * (earthSunDistance**2 * np.pi) \
                    / (calibrationCoeff * np.cos(np.radians(sunAngle)))) * 10000 #* i need to check with mark to ensure we are still scaling

        return toaReflectanceCoeff


    #---------------------------------------------------------------------------
    # run()
    #---------------------------------------------------------------------------
    def run(orthoBandFile, outputDir, dgFile): #* dgFile  or DgFile or something else?

        dataset = gdal.Open(orthoBandFile, gdal.GA_ReadOnly)
        if not dataset:
            raise RuntimeError("Could not open {}".format(orthoBandFile))
        bandName = dataset.GetMetadataItem('bandName')
        dataset = None

        toaReflectanceCoeff = TOA.calcToaReflectanceCoeff(dgFile, bandName)

        baseName = os.path.basename(orthoBandFile).replace('.tif', '_TOA.tif') #* not sure how you wanna name it
        toaBandFile = os.path.join(outputDir, baseName)

        #* also need to look into ASP's image calc function
        #* do we need to do cmd with + like in retriever ?
        cmd = 'gdal_calc.py -A {} --calc="A*{}" --outfile={} --NoDataValue=0 \
                                    --type=\'Int16\''.format(orthoBandFile,  \
                                            toaReflectanceCoeff, toaBandFile)

        if not os.path.isfile(toaBandFile):
            os.system(cmd)

        return toaBandFile









File naming convention:

WV01_20080324_P1BS_10200100010A0900-toa.tif
 1      2      3           4
         
1) Sensor: WV01, WV02, or WV03
2) Date: YYYYMMDD
3) Spectral code: P1BS (Panchromatic) or M1BS (Multispectral)
4) Catalog ID: Digital Globe’s unique strip identifier


Example output directory: 

WV02_20100902_M1BS_1030010007C2B700-toa.tif
WV02_20100902_M1BS_1030010007C2B700-toa.xml	
WV02_20100911_M1BS_1030010006788900-toa.tif	
WV02_20100911_M1BS_1030010006788900-toa.xml
toa-multispec.vrt
toa-multispec.vrt.ovr

WV01_20080324_P1BS_10200100010A0900-toa.tif
WV01_20080324_P1BS_10200100010A0900-toa.xml	
WV01_20080415_P1BS_1020010002407E00-toa.tif	
WV01_20080415_P1BS_1020010002407E00-toa.xml
toa-pan.vrt
toa-pan.vrt.ovr


• Raw imagery is first orthorectified* to:
    1) 30 m ASTER GDEM If latitude is less than -54 degrees or greater than 60 degrees
    2) 30 m SRTM DEM elsewhere
    *Prior to orthorectification, the DEM is adjusted so that its values are relative to the WGS84 datum instead of the EGM96 geoid
• Top of atmosphere reflectance is then calculated using Thuillier 2003 calibration values and algorithm from Digital Globe (See https://dg-cms-uploads-production.s3.amazonaws.com/uploads/document/file/209/ABSRADCAL_FLEET_2016v0_Rel20170606.pdf):
    L = calibrationGain * orthoDN * (abscalFactor / effectiveBandwidth) + calibrationOffset
    ToA = (L * earthSunDistance^2 * pi)/ (calibrationCoefficient * cos(solarZenithAngle))
• Final ToA values are scaled up by a factor of 10,000
• Each strip (*toa.tif) is accompanied by an .xml metadata file
• Multispec (M1BS) and Pan (P1BS) outputs are mosaicked into separate .vrt files (Virtual Raster Format)
• The strips in the .vrt are ordered so that those with the lowest reported cloud score are on top
• Each .vrt mosaic is accompanied by an overview file (.vrt.ovr)


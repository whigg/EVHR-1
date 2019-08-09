#!/usr/bin/python

import math
from  xml.etree import cElementTree as ET
import os
from osgeo import gdal
from osgeo import osr
import numpy as np
import numpy.ma as ma
# import matplotlib.pyplot as plt
# import matplotlib.image as mpimg
import sys
nBands = 5
BandName =["BAND_C", "BAND_B","BAND_G","BAND_R", "BAND_N"]
BandNum = [1, 2, 3, 5, 7] 
RGBNum =  [-1, 2, 1, 0, -1]
AbScal = []
EBWidth = []
gain = [ 1.151, 0.988, 0.936, 0.952, 0.961]
offset=[ -7.478, -5.736,-3.546, -2.512,  -3.300]
#WRC Solar Irradiance
#S0 = [1974.2416, 1856.4104, 1559.4555, 1069.7302]
#Thuillier 2003
#S0=[ 2007.27, 1829.62, 1538.85, 1053.21]
S0=[1773.81, 2007.27, 1829.62, 1538.85, 1053.21]

PI = 3.14159265358979
D2R = PI/180
# datapath = '/att/gpfsfs/briskfs01/ppl/mwooten3/AIST/forYujie/2/' + sys.argv[2] + '/'
# outpath = '../TOA/' + sys.argv[2] + '/'
datapath = sys.argv[2]
outpath = sys.argv[2]

f =open(sys.argv[1], "r")
f1=f.readlines()

for filebase in f1:

     filebase=filebase.strip("\n")
     print filebase

     # WVfile = datapath + filebase + '-ortho.tif'
     # xmlfile= datapath + 'EVHR_' + filebase + '-TOA.xml'
     WVfile = os.path.join(datapath, filebase + '.tif')
     xmlfile = os.path.join(datapath, filebase + '.xml')
     outbin = os.path.join(outpath, filebase + '.bin')
     outmeta = os.path.join(outpath, filebase + '.meta')

     with open(xmlfile, 'rt') as f:
         tree = ET.parse(f)
         
     node  = tree.find('.//MEANSUNEL')
     SZA = 90 - float(node.text)
     node  = tree.find('.//MEANSUNAZ')
     SAZ = float(node.text)
     node  = tree.find('.//MEANSATEL')
     VZA = 90 - float(node.text)
     node  = tree.find('.//MEANSATAZ')
     VAZ = float(node.text)
     RelAZ = SAZ-VAZ
     print "???", RelAZ
     if(RelAZ > 360):
         RelAZ -=360
     if(RelAZ<-360):
         RelAZ +=360
     print "???", RelAZ
     RelAZ = 180 - math.fabs(RelAZ)
     print "???", RelAZ
     RelAZ= math.fabs(RelAZ)
     print "???", RelAZ
     node  = tree.find('.//NUMROWS')
     dimy = int(node.text)

     node  = tree.find('.//NUMCOLUMNS')
     dimx = int(node.text)

     node  = tree.find('.//FIRSTLINETIME')
     overpasstime = node.text
     #overpasstime = "2009-10-08T18:51:00.000000Z"
     date, t = overpasstime.split("T")
     h, m, sec = t.split(":")
     h = float(h)
     m = float(m)
     ssec = float(sec[:-2])
     UT = h + m/60 + ssec/3600

     year, month, day = date.split("-")
     year = float(year)
     month = float(month)
     day = float(day)
     if(month == 1 or month ==2):
         year = year-1
         month = month +12
     A = int(year/100)
     B = 2-A +int(A/4)
     JD=int(365.25*(year+4716)) + int(30.6001*(month+1)) +day + UT/24 +B -1524.5
     D = JD - 2451545.0
     g = 357.529+0.98560028*D
     g= g*D2R
     des=1.00014 -0.01671*math.cos(g)-0.00014*math.cos(2*g)

     print dimy, dimx, date, m,year, month, day, UT,A, B, JD,  des
     m = h *60+ float(m)
     node = tree.find(".//BAND_B//ULLON")
     # The xml file has messed up UL and LR
     LRLon = float(node.text)
            
     node = tree.find(".//BAND_B//LRLON")
     ULLon = float(node.text)

     lon =  ULLon
     print "UL-LR", ULLon, LRLon, lon
     node = tree.find(".//BAND_B//ULLAT")
     LRLat = float(node.text)
     node = tree.find(".//BAND_B//LRLAT")
     ULLat = float(node.text)

     lat = ULLat
     print "LAT--", ULLat, LRLat, lat

     AbScal = []
     EBWidth = []
     for bname in BandName:
         s= ".//"+bname+"//"+"ABSCALFACTOR"
         node = tree.find(s)
         AbScal.append(float(node.text))
         s= ".//"+bname+"//"+"EFFECTIVEBANDWIDTH"
         node = tree.find(s)
         EBWidth.append(float(node.text))

     print lat, lon, SZA, VZA, SAZ, VAZ, RelAZ, overpasstime, AbScal, EBWidth

     ds = gdal.Open(WVfile)
     if ds is None:
         print "Error: cannot open file", WVfile
         sys.exit(1)

     dimy =  ds.RasterYSize
     dimx =  ds.RasterXSize
     startx=0
     starty=0
     SizeX = dimx
     SizeY= dimy
     print  "startx, starty=", startx, starty, SizeX, SizeY, dimy, dimx

     outfile=open(outmeta, 'w')
     outfile.write(date)
     outfile.write('   %d\n'%m)
     outfile.write('%f   %f\n'% (lat, lon))
     outfile.write('%f   %f   %f   %f   %f \n'% (SZA, VZA, SAZ, VAZ, RelAZ))
     outfile.write('%d   %d\n'% (SizeY, SizeX))
     gtf= ds.GetGeoTransform()
     print gtf
     proj= ds.GetProjection()
     print proj
     sr = osr.SpatialReference()
     sr.ImportFromWkt(proj)
     words = sr.GetAttrValue('projcs').split()
     print words[-1][0:-1], "   ", words[-1][-1]
     outfile.write('%s   %s\n'% (words[-1][0:-1],words[-1][-1]))
         
	 
     ulcX = gtf[0] + startx*gtf[1];
     ulcY = gtf[3] + gtf[5]*starty;
     outfile.write('%f   %f   %f   %f\n'% (ulcX, gtf[1], ulcY, gtf[5]))
     #outfile.write('%f   %f   %f   %f\n'% (gtf[0], gtf[1], gtf[3], gtf[5]))
     outfile.write(proj)
     outfile.close()

     TOAfile = datapath + 'EVHR_' +  filebase + '-TOA.tif'
     TOAary = np.zeros((SizeY, SizeX), dtype=np.float32)
     ds2 = gdal.Open(TOAfile)
     if ds2 is None:
         print "Error: cannot open file", WVfile
         sys.exit(1)
    
   
     outary=np.zeros((SizeY, SizeX), dtype=np.float32)
     bandary= np.zeros((SizeY,SizeX,3)).astype(np.float32)
     fd=open(outbin, 'wb')
     for i in range(0, nBands):
         band=ds.GetRasterBand(BandNum[i])
         buf= np.array(band.ReadAsArray(startx, starty, SizeX, SizeY))
         outary= np.float32((buf*gain[i]*(AbScal[i]/EBWidth[i]) + offset[i])*PI*des*des/(S0[i]*math.cos(SZA*D2R)))
	 #outary= np.float32(buf)
	 band2 = ds2.GetRasterBand(BandNum[i])
	 buf = np.array(band2.ReadAsArray(startx, starty, SizeX, SizeY))
	 TOAary = np.float32(buf)
	 
         print i, gain[i], AbScal[i],EBWidth[i],  offset[i],S0[i],SZA, math.cos(SZA*D2R) , outary[1000][1000], TOAary[1000][1000]
         #print "outary=", outary.dtype
         if(RGBNum[i]>=0):
             bandary[:,:, RGBNum[i]]=np.float32(TOAary/10000.0)
	    # print RGBNum[i], BandNum[i], outary[1000][1000], buf[1000][1000],  outary[10][10], buf[10][10]
         outary.tofile(fd)
     fd.close()
     print "....\n"
     #plt.imshow(bandary)
     #plt.show()
 
     #TOAfile = datapath + filebase + '-TOA.tif'
     #TOAary = np.zeros((SizeY, SizeX), dtype=np.float32)
     #ds2 = gdal.Open()
     #if ds2 is None:
     #    print "Error: cannot open file", WVfile
     #    sys.exit(1)
     #for i in range(0, nBands):
     #    band=ds.GetRasterBand(BandNum[i])
     #    buf= np.array(band.ReadAsArray(startx, starty, SizeX, SizeY))
     #	  outary = 


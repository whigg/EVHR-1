File naming convention:

WV01_20110804_1020010015973400_10200100152A5F00.tif
 1      2            3                4              
         
1) Sensor: WV01, WV02, or WV03
2) Date: YYYYMMDD
3) Left Strip Catalog ID (Digital Globe’s unique strip identifier)
4) Right Strip Catalog ID 


Example output directory: 

WV01_20110804_1020010015973400_10200100152A5F00.tif
WV01_20121011_102001001D7BF600_102001001B5FD900.tif
WV02_20161122_103001006047D300_10300100604FFF00.tif
WV03_20161227_10400100274B5600_10400100278D4300.tif


• Output directory consists of one 4 m DEM per valid pair
• The DEMs are generated using open source stereogrammatery software, Ames Stereo Pipeline (ASP): https://ti.arc.nasa.gov/tech/asr/groups/intelligent-robotics/ngt/stereo/
• For more information, see David Shean's paper "An automated, open-source pipeline for mass production of digital elevation models (DEMs) from very-high-resolution commercial stereo satellite imagery" (https://doi.org/10.1016/j.isprsjprs.2016.03.012)
• See also Paul Montesano's paper "Boreal canopy surfaces from spaceborne stereogrammetry" (https://doi.org/10.1016/j.rse.2019.02.012)

• A sample call to the algorithm's central ASP function, parallel_stereo, which includes the default parameters used in the API, is shown below:
"parallel_stereo -e 0 --job-size-w 3000 --job-size-h 3000 --threads-singleprocess 16 --processes 16 --threads-multiprocess 1 --nodes-list=/att/nobackup/rlgill/DgStereo/nodeList.txt -t dg --alignment-method AffineEpipolar --subpixel-kernel 15 15 --erode-max-size 24 --corr-kernel 21 21 --corr-timeout 300 --individually-normalize --tif-compress LZW --subpixel-mode 2 --filter-mode 1 --cost-mode 2 <leftStrip.tif> <rightStrip.tif> <leftStrip.xml> <rightStrip.xml> <outputDirectory>"
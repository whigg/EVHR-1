
import datetime

#-------------------------------------------------------------------------------
# class LandsatProduct
#
# https://landsat.usgs.gov/landsat-collections#C1%20Tiers
#-------------------------------------------------------------------------------
class LandsatProduct():

    #---------------------------------------------------------------------------
    # __init__
    #
    # LC08_L1TP_040030_20161122_20170219_01_T1
    #---------------------------------------------------------------------------
    def __init__(self, productID, logger = None):

        if not productID or productID == '':
            raise RuntimeError('A product ID must be specified.')
        
        self.logger = logger
        
        if self.logger:
            self.logger.info('Product: ' + str(productID))
            
        self.productID = productID
        
        components              = productID.split('_')
        collAndSensor           = components[0]
        self.sensor             = collAndSensor[1:2]
        self.satellite          = collAndSensor[2:]
        self.acquisitionDateStr = components[3]
        year                    = int(self.acquisitionDateStr[0:4])
        month                   = int(self.acquisitionDateStr[4:6])
        day                     = int(self.acquisitionDateStr[6:8])
        self.date               = datetime.datetime(year, month, day)
        
    #---------------------------------------------------------------------------
    # available
    #
    # There are various reasons why landsat is unavailable 
    #---------------------------------------------------------------------------
    def available(self):
        
        startDate = datetime.datetime(2016, 5, 30)
        endDate   = datetime.datetime(2016, 6, 12)
        
        if self.date >= startDate and self.date <= endDate:
            
            return False

        if self.satellite == '07':
            
            return self.l7Available()
            
        elif self.satellite == '08':
            
            return self.l8Available()
            
        else:
            
            raise RuntimeError('Unknown satellite: ' + str(self.satellite))

    #---------------------------------------------------------------------------
    # l8Available
    #---------------------------------------------------------------------------
    def l8Available(self):
        
        startDate1 = datetime.datetime(2016, 2, 19)
        endDate1   = datetime.datetime(2016, 2, 27)
        startDate2 = datetime.datetime(2016, 8,  8)
        endDate2   = datetime.datetime(2016, 8, 10)
        
        if (self.date >= startDate1 and self.date <= endDate1) or \
           (self.date >= startDate2 and self.date <= endDate2):
            
            return False
            
        return True

    #---------------------------------------------------------------------------
    # l7Available
    #---------------------------------------------------------------------------
    def l7Available(self):
        
        return True


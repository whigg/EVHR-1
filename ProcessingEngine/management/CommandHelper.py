
import datetime
import logging
import traceback

from ProcessingEngine.models import Constituent
from ProcessingEngine.management.RequestProcessor import RequestProcessor

#-------------------------------------------------------------------------------
# class CommandHelper
#-------------------------------------------------------------------------------
class CommandHelper(object):
    
    #---------------------------------------------------------------------------
    # addCommonArgs
    #---------------------------------------------------------------------------
    @staticmethod
    def addCommonArgs(parser):
        
        parser.add_argument('--name')
        parser.add_argument('-o', help = 'path to output directory')
        parser.add_argument('-n', default = -1, help = 'number of proceses')
        parser.add_argument('--startDate', type = makeDate, help = 'mm-dd-yyyy')
        parser.add_argument('--endDate',   type = makeDate, help = 'mm-dd-yyyy')

    #---------------------------------------------------------------------------
    # addReprocessingArgs
    #---------------------------------------------------------------------------
    @staticmethod
    def addReprocessingArgs(parser):
        
        parser.add_argument('--id')
        
        parser.add_argument('--duplicate', 
                            action = 'store_true',
                            help = 'Duplicate the existing request.')

        CommandHelper.addCommonArgs(parser)
        
    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    @staticmethod
    def handle(request, args = [], options = []):

        numProcesses = int(options['n']) if 'n' in options else -1
        logger       = logging.getLogger('console') # standard output.
        reqProc      = RequestProcessor(request, numProcesses, logger)
        
        if numProcesses == 1:
       
            retriever = reqProc.chooseRetriever()
            constituentFileDict = retriever.listConstituents()
            aggregateDict = dict(constituentFileDict)
        
            while len(constituentFileDict) > 0:
                
                oneConstituentAndFiles = constituentFileDict.popitem()

                # Get or create a constituent.
                constituent = None
                
                consQuerySet = Constituent.objects.filter( \
                                    request=request,
                                    destination=oneConstituentAndFiles[0])
                                    
                if len(consQuerySet) != 0:
                    
                    constituent = consQuerySet[0]
                    
                else:
                                                   
                    constituent = Constituent()
                    constituent.request = request
                    constituent.started = True
                    constituent.destination = oneConstituentAndFiles[0]
                    constituent.save()

                retriever.retrieveOne(oneConstituentAndFiles[0],
                                      oneConstituentAndFiles[1])
        
            aggFile = retriever.aggregate(aggregateDict)

        else:
            try:
                reqProc()

            except Exception as e:
            
                print traceback.format_exc()
                reqProc.cleanUp()

    #--------------------------------------------------------------------
    # handleReprocessing
    #--------------------------------------------------------------------
    @staticmethod
    def handleReprocessing(request, args, options):
        
        if options['duplicate']:
           
            dup = request
            dup.save()
            request = dup

        CommandHelper.handle(request, args, options)

#-------------------------------------------------------------------------------
# makeDate
#-------------------------------------------------------------------------------
def makeDate(dateString):
    return datetime.datetime.strptime(dateString, '%m-%d-%Y').date()
        


from django.core.management.base import BaseCommand

from EvhrEngine.models import EvhrNodePID

class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        nodePIDs = EvhrNodePID.objects.all()
        
        for nodePID in nodePIDs:
            
            try:
                print 'Deleting NodePID with invalid pid.'
                os.kill(nodePID, 0)
                
            except OSError:

                nodePID.delete()

            else:
                return True
    
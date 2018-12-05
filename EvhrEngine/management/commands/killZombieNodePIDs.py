
from django.core.management.base import BaseCommand

from EvhrEngine.models import EvhrNodePID

class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        for nodePID in nodePIDs:
            
            try:
                os.kill(nodePID, 0)
                
            except OSError:

                nodePID.delete()

            else:
                return True
    
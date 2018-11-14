from EvhrEngine.management.DgFile import DgFile

from django.core.management.base import BaseCommand

class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('-n', help='Full path to NITF file', required=True)

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        dgFile = DgFile(options['n'])

        print 'Pair name:  ' + str(dgFile.getPairName())



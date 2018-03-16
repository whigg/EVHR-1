from EvhrEngine.management.DgFile import DgFile

from django.core.management.base import BaseCommand

class Command(BaseCommand):

    #---------------------------------------------------------------------------
    # add_arguments
    #---------------------------------------------------------------------------
    def add_arguments(self, parser):

        parser.add_argument('-o', help = 'Full path to output directory.')
        parser.add_argument('-b', help = 'Band name (eg. BAND_B).')
        parser.add_argument('-n', help = 'Full path to NITF file')

    #---------------------------------------------------------------------------
    # handle
    #---------------------------------------------------------------------------
    def handle(*args, **options):

        dgFile = DgFile(options['n'])
        dgFile.getBand(options['o'], options['b'])




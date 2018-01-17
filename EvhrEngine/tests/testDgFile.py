from django.test import TestCase
from EvhrEngine.management.DgFile import DgFile

class DgFileTestCase(TestCase):

    file_works = 'EvhrEngine/tests/WV02_20120914215615_103001001B29FF00_12SEP14215615-M1BS-052903555050_01_P002.ntf'
    file_badxml = 'EvhrEngine/tests/WV01_20130613214651_1020010022CE5C00_13JUN13214651-P1BS-500097581160_01_P001.ntf'
    file_noxml = 'EvhrEngine/tests/WV02_20160728063958_1030010059C17B00_16JUL28063958-M1BS-500852804030_01_P001.ntf'

    def testinit(self):

        with self.assertRaises(RuntimeError):
            filename = DgFile('/path/to/test.py')


        with self.assertRaises(RuntimeError):
            filename = DgFile('/path/to/test.tif')

        with self.assertRaises(RuntimeError):
           filename = DgFile('bad.tif')

##        import pdb
##        pdb.set_trace()
        filename = DgFile(DgFileTestCase.file_works)

        with self.assertRaises(RuntimeError):
           filename = DgFile(DgFileTestCase.file_noxml)




    def testabscalFactor(self):

        fn_w = DgFile(DgFileTestCase.file_works)
        fn_bx = DgFile(DgFileTestCase.file_badxml)

        with self.assertRaises(RuntimeError):
            fn_w.abscalFactor('R')

        with self.assertRaises(AttributeError):
            fn_bx.abscalFactor('BAND_P')

        blue_AF = fn_w.abscalFactor('BAND_B')
        self.assertEqual(blue_AF, 0.007291212)



'''Unittests for idlesporklib/configHandler.py

Coverage: 46% just by creating dialog. The other half is change code.

'''
import unittest
from test.test_support import requires
from Tkinter import Tk
from idlesporklib.configDialog import ConfigDialog
from idlesporklib.macosxSupport import _initializeTkVariantTests


class ConfigDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        requires('gui')
        cls.root = Tk()
        _initializeTkVariantTests(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
        del cls.root

    def test_dialog(self):
        d=ConfigDialog(self.root, 'Test', _utest=True)
        d.destroy()


if __name__ == '__main__':
    unittest.main(verbosity=2)

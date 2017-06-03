import unittest
from test.test_support import captured_stderr, findfile
from idlesporklib import Suggest, sporktools
from idle_test import mock_world, mock_idle
import sys


__file__ = findfile('idle_test') + '/test_suggest.py'

class SuggestTest(unittest.TestCase):
    IMPORT_STR = 'Do you want to LINK?'
    SUGGEST_STR = 'Did you mean LINK?'

    @classmethod
    def setUpClass(cls):
        cls.old_World = sporktools._World
        sporktools._World = mock_world.MockWorld()

    @classmethod
    def tearDownClass(cls):
        sporktools._World = cls.old_World

    def test_import(self):
        res = self._test_suggest("time", NameError)
        self.assertEqual(res, self.IMPORT_STR)
        self._test_link_created("import time")

    def test_spelling(self):
        res = self._test_suggest("tulpe", NameError, {})
        self.assertEqual(res, self.SUGGEST_STR)
        self._test_link_created("tuple")

    def test_spelling_attr(self):
        import time
        res = self._test_suggest("time.lseep", AttributeError, {"time": time})
        self.assertEqual(res, self.SUGGEST_STR)
        self._test_link_created("sleep")

    def _test_suggest(self, code, exc_typ, globals=None):
        if globals is None: globals = {}

        sporktools._World.interp.create_link = mock_idle.Func("LINK")

        with self.assertRaises(exc_typ) as cm:
            exec code in globals
        tb = sys.exc_traceback
        import traceback
        filename = traceback.extract_tb(tb)[-1][0]
        with captured_stderr() as err:
            Suggest.exception_suggest(exc_typ, cm.exception, tb, code, filename)
        return err.getvalue().strip()

    def _test_link_created(self, expected_txt):
        create_link = sporktools._World.interp.create_link
        self.assertTrue(create_link.called)
        self.assertEqual(create_link.args[0].txt, expected_txt)

if __name__ == '__main__':
    unittest.main(verbosity=2, exit=False)

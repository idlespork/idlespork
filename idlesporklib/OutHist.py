from collections import deque

from idlesporklib.configHandler import idleConf
from idlesporklib.EnablableExtension import boundremotefunc


class OutHist:
    """
    Extension to save outputs history

    Creates a variable OutHist in the namespace
    """

    # Size of history.
    _histsize = idleConf.GetOption("extensions", "OutHist",
                                   "histsize", type="int", default=10)

    history = deque(maxlen=_histsize)

    def __init__(self, editwin=None):
        if editwin is not None and hasattr(editwin, 'interp'):
            self.editwin = editwin
            self._loop_init()

    def _loop_init(self):
        try:
            rpc = self.editwin.flist.pyshell.interp.rpcclt
            notyet = False
        except AttributeError:
            notyet = True

        if notyet or not self._remote_init():
            self.editwin.text.after_idle(self._loop_init)

    @boundremotefunc
    def _remote_init(self):
        try:
            import sys
            old_displayhook = sys.displayhook
            import os

            def displayhook(val):
                if val is not None and val is not OutHist.history:
                    OutHist.history.append(val)
                old_displayhook(val)

            sys.displayhook = displayhook
            from idlesporklib.run import World
            World.executive.runcode("from idlesporklib.OutHist import OutHist")
            return True
        except AttributeError:
            return False

    @staticmethod
    def clear():
        OutHist.history = deque(maxlen=OutHist._histsize)

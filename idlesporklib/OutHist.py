from collections import deque

from idlesporklib.configHandler import idleConf
from idlesporklib.EnablableExtension import remoteboundmethod, EnablableExtension, boundguifunc, remoteclassmethod


class OutHist(EnablableExtension):
    """
    Extension to save outputs history

    Creates a variable Out in the namespace, like in IPython.
    Don't forget to enable CustomizePrompt and add %OutIndex in your prompt.
    """
    class __metaclass__(EnablableExtension.__metaclass__):
        _index_by_previous_line = idleConf.GetOption("extensions", "OutHist",

                                                     "index_by_previous_line", type="bool", default=False,
                                                     member_name='index_by_previous_line')
        just_changed = False

        @property
        def index_by_previous_line(cls):
            return cls._index_by_previous_line

        @index_by_previous_line.setter
        def index_by_previous_line(cls, value):
            cls._index_by_previous_line = value
            cls.set_index_by_previous_line(value)

    @remoteclassmethod
    def set_index_by_previous_line(cls, value):
        if not value:
            cls.just_changed = True
        OutHist._index_by_previous_line = value

    # Size of history.
    # _histsize = idleConf.GetOption("extensions", "OutHist",
    #                                "histsize", type="int", default=10)

    history = {}
    cursor = 1

    def __init__(self, editwin=None):
        OutHist.cursor = 0 if OutHist.index_by_previous_line else 1
        if editwin is not None and hasattr(editwin, 'interp'):
            self.editwin = editwin
            self.editwin.interp.register_onrestart(self._loop_init)
            self._loop_init()

    def _loop_init(self):
        try:
            rpc = self.editwin.flist.pyshell.interp.rpcclt
            notyet = False
        except AttributeError:
            notyet = True

        if notyet or not self._remote_init():
            self.editwin.text.after_idle(self._loop_init)

    @remoteboundmethod
    def _remote_init(self):
        try:
            import sys
            old_displayhook = sys.displayhook
            import os

            def displayhook(val):
                if val is not None and val is not OutHist.history:
                    OutHist.history[OutHist.cursor] = val

                if OutHist.index_by_previous_line:
                    self.set_cursor(OutHist.cursor)
                    OutHist.cursor += 1
                else:
                    if OutHist.just_changed:
                        OutHist.just_changed = False
                    else:
                        OutHist.cursor += 1
                    self.set_cursor(OutHist.cursor)

                old_displayhook(val)

            sys.displayhook = displayhook
            from idlesporklib.run import World
            World.executive.runcode("from idlesporklib.OutHist import OutHist as __OutHist")
            World.executive.runcode("Out = __OutHist.history")
            World.executive.runcode("del __OutHist")
            return True
        except AttributeError:
            return False

    @boundguifunc
    def set_cursor(self, cursor):
        OutHist.cursor = cursor

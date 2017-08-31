from __future__ import print_function
##############################
#
# This module tries to prevent the horrible bug.
#


# noinspection PyCompatibility
import Tkinter
# import _tkinter
import threading
# import matplotlib
# matplotlib.use('agg')
# noinspection PyCompatibility
from Queue import Queue
from matplotlib import pyplot as plt
import random
import time
from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
from types import MethodType

from idlesporklib.EnablableExtension import boundremotefunc

dont_delete_yet = Queue()


# oldcreate = _tkinter.create
#
#
# def newcreate(*args, **kwargs):
#     ret = oldcreate(*args, **kwargs)
#     dont_delete_yet.put(ret)
#     print("saved reference to:", ret)
#     return ret
#
#
# _tkinter.create = newcreate


class PatchTkinter(object):
    def __init__(self, editwin=None):
        if editwin is not None and hasattr(editwin, 'interp'):
            self.editwin = editwin
            editwin.interp.register_onrestart(self._loop_init)
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
            print("patching Tkinter delete functions")
            old_del = Tkinter.PhotoImage.__del__

            def newdel(self_):
                global dont_delete_yet
                # noinspection PyProtectedMember
                if isinstance(threading.current_thread(), threading._MainThread):
                    old_del(self_)
                else:
                    if dont_delete_yet:
                        dont_delete_yet.put(self_)

            Tkinter.PhotoImage.__del__ = newdel

            def newdel2(self_):
                global dont_delete_yet
                # noinspection PyProtectedMember
                if not isinstance(threading.current_thread(), threading._MainThread):
                    if dont_delete_yet:
                        dont_delete_yet.put(self_)

            Tkinter.Tk.__del__ = newdel2
            return True
        except:
            return False


# def shimi():
#     time.sleep(0.1)
#     z = plt.plot([random.randint(1,1000000)])
#     plt.close()
#
# for i in range(1000):
#     threading.Thread(target=shimi).start()
#
# print("done, now sleeping a bit")
# time.sleep(10)
# print("ok bye")

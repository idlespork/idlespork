from __future__ import print_function
##############################
#
# This file recreates the horrible bug.
# Overriding __del__ of PhotoImage is not enough to solve it :(
#

import Tkinter
import threading
# import matplotlib
# matplotlib.use('agg')
from matplotlib import pyplot as plt
import random
import time
from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
from types import MethodType


old_del = Tkinter.PhotoImage.__del__


def newdel(self):
    if isinstance(threading.current_thread(), threading._MainThread):
        old_del(self)
    else:
        print('prevented delete to save shell')


Tkinter.PhotoImage.__del__ = newdel
print("overriding Tkinter.PhotoImage.__del__")


def shimi():
    time.sleep(0.1)
    z = plt.plot([random.randint(1,1000000)])
    plt.close()


threading.Thread(target=shimi).start()

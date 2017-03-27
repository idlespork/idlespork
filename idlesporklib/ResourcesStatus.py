#! /usr/bin/env python
from __future__ import print_function

from Tkinter import RIGHT

try:
    import psutil
except ImportError:
    psutil = None


class ResourcesStatus(object):
    def __init__(self, editwin):
        if psutil is not None:
            self.editwin = editwin
            self.text = self.editwin.text
            self.editwin.status_bar.set_label('cpu', 'Cpu: ?', side=RIGHT)
            self.editwin.status_bar.set_label('mem', 'Mem: ?', side=RIGHT)
            self.text.after_idle(self.set_cpu_and_mem)
        else:
            print("ResourcesStatus extension could not find the psutil module.")

    def set_cpu_and_mem(self, event=None):
        process = psutil.Process(self.editwin.interp.rpcpid)
        cpu = process.cpu_percent(0.1)
        mem = process.memory_percent()
        self.editwin.status_bar.set_label('cpu', 'Cpu: %.1f' % cpu)
        self.editwin.status_bar.set_label('mem', 'Mem: %.1f' % mem)
        self.text.after(1000, self.set_cpu_and_mem)

#! /usr/bin/env python
from __future__ import print_function

from Tkinter import RIGHT
from idlesporklib.EnablableExtension import EnablableExtension

try:
    import psutil
except ImportError:
    psutil = None


class ResourcesStatus(EnablableExtension):
    """
    Extension to show cpu and memory usage in the status bar.

    * Must have the package psutil installed.
    """
    def __init__(self, editwin):
        if psutil is not None:
            self.editwin = editwin
            self.text = self.editwin.text
            try:
                interp = self.editwin.interp
                self.editwin.status_bar.set_label('cpu', 'Cpu: ?', side=RIGHT)
                self.editwin.status_bar.set_label('mem', 'Mem: ?', side=RIGHT)
                self.text.after_idle(self.set_cpu_and_mem)
            except AttributeError:
                pass
        else:
            print("ResourcesStatus extension could not find the psutil module.")

    def set_cpu_and_mem(self, event=None):
        # Check if extension is still enabled.
        if ResourcesStatus.enable:
            process = psutil.Process(self.editwin.interp.rpcpid)
            cpu = process.cpu_percent(0.1)
            mem = process.memory_percent()
            self.editwin.status_bar.set_label('cpu', 'Cpu: %.1f' % cpu)
            self.editwin.status_bar.set_label('mem', 'Mem: %.1f' % mem)
            self.text.after(1000, self.set_cpu_and_mem)
        else:
            self.editwin.status_bar.set_label('cpu', '')
            self.editwin.status_bar.set_label('mem', '')

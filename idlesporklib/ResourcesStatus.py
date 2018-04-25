#! /usr/bin/env python
from __future__ import print_function

import time
from types import MethodType
from Tkinter import RIGHT
from idlesporklib.EnablableExtension import EnablableExtension
from idlesporklib import Commands

try:
    import psutil
except ImportError:
    psutil = None


class ResourcesStatus(EnablableExtension):
    """
    Extension to show cpu and memory usage in the status bar.
    Also shows time since last execution.

    * Must have the package psutil installed.
    """

    last_exec = None

    def __init__(self, editwin):
        """
        Args:
            editwin (PyShell): pyshell.
        """
        if psutil is not None:
            self.editwin = editwin
            self.text = self.editwin.text
            try:
                # interp = self.editwin.interp
                #
                # old_runcmd_from_source = editwin.interp.runcmd_from_source

                def runcmd_from_source(self_, source):
                    console = self_.tkconsole
                    try:
                        cmd = Commands.parse(self_, source)
                    except Exception as e:
                        console.beginexecuting()
                        print(str(e), file=console.stderr)
                        console.endexecuting()
                        return
                    if cmd is None:
                        return
                    ResourcesStatus.last_exec = time.time()
                    console.query_prompt()
                    console.beginexecuting()
                    if self_.runcmd(cmd):
                        console.endexecuting()

                editwin.interp.runcmd_from_source = MethodType(runcmd_from_source, editwin.interp)

                old_endexecuting = editwin.endexecuting

                def endexecuting(self_):
                    ResourcesStatus.last_exec = None
                    return old_endexecuting()

                editwin.endexecuting = MethodType(endexecuting, editwin)

                old_restart_shell = editwin.restart_shell

                def restart_shell(self_, event=None):
                    ResourcesStatus.last_exec = None
                    return old_restart_shell(event)

                editwin.restart_shell = MethodType(restart_shell, editwin)

                self.editwin.status_bar.set_label('cpu', 'Cpu: ?', side=RIGHT)
                self.editwin.status_bar.set_label('mem', 'Mem: ?', side=RIGHT)
                self.editwin.status_bar.set_label('time', '', side=RIGHT)
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

            if ResourcesStatus.last_exec:
                time_diff = int(time.time() - ResourcesStatus.last_exec)
                mins, secs = divmod(time_diff, 60)
                self.editwin.status_bar.set_label('time', '%02d:%02d' % (mins, secs))
            else:
                self.editwin.status_bar.set_label('time', '')

            self.text.after(1000, self.set_cpu_and_mem)
        else:
            self.editwin.status_bar.set_label('cpu', '')
            self.editwin.status_bar.set_label('mem', '')
            self.editwin.status_bar.set_label('time', '')

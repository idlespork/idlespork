from __future__ import print_function
##############################
#
# This module tries to prevent the horrible bug.
#

import threading
import random
import time
from threading import Thread

# noinspection PyCompatibility
from Queue import Queue, Empty

# noinspection PyCompatibility
import Tkinter

from idlesporklib.EnablableExtension import remoteboundmethod


# Queues for objects not to delete yet.
# Experimentation has shown that trying to delete a Tk object will always fail, so we'll simply keep them.
_delete_photos_queue = Queue()
_delete_tk_queue = Queue()


class PatchTkinter(object):
    """Module to prevent shell crashes caused by Tkinter deletes in wrong thread."""
    def __init__(self, editwin=None):
        # Patch if editwin is an interpreter window.
        if editwin is not None and hasattr(editwin, 'interp'):
            self.editwin = editwin
            # Register to patch when shell is restarted.
            editwin.interp.register_onrestart(self._loop_init)
            self._loop_init()

    def _loop_init(self):
        """Wait until rpc is up and running."""
        try:
            notyet = not hasattr(self.editwin.flist.pyshell.interp, "rpcclt")
        except AttributeError:
            notyet = True

        if notyet or not self._remote_init():
            self.editwin.text.after_idle(self._loop_init)

    @remoteboundmethod
    def _remote_init(self):
        """Patch Tkinter delete functions. This happens in rpc."""
        try:
            old_photoimage = Tkinter.PhotoImage

            class NewPhotoImage(old_photoimage):
                # noinspection PyMissingConstructor
                def __init__(self_, *args, **kwargs):
                    self_._my_thread = threading.currentThread()
                    old_photoimage.__init__(self_, *args, **kwargs)

                def __del__(self_):
                    """Deletes PhotoImage only if in main thread, otherwise queues to be deleted."""
                    global _delete_photos_queue
                    # noinspection PyProtectedMember
                    if threading.current_thread() is self_._my_thread:
                        old_photoimage.__del__(self_)
                    else:
                        if _delete_photos_queue:
                            _delete_photos_queue.put(self_)

            # Replace PhotoImage delete method.
            Tkinter.PhotoImage = NewPhotoImage

            def delete_tk(self_):
                """Deletes Tk only if in main thread, otherwise queues to be deleted."""
                global _delete_photos_queue
                # noinspection PyProtectedMember
                if not isinstance(threading.current_thread(), threading._MainThread):
                    if _delete_photos_queue:
                        _delete_tk_queue.put(self_)

            Tkinter.Tk.__del__ = delete_tk

            from idlesporklib.run import MainThreadCaller

            # This is a method that we know is called from main thread.
            old_wait_for_call = MainThreadCaller.wait_for_call

            def new_wait_for_call(timeout):
                """New wait_for_call tries to delete queued PhotoImages."""
                try:
                    while True:
                        _delete_photos_queue.get_nowait()
                except Empty:
                    pass

                return old_wait_for_call(timeout)

            MainThreadCaller.wait_for_call = new_wait_for_call

            print("Patched Tkinter delete functions. ")

            return True
        except AttributeError:
            return False

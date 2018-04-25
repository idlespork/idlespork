from __future__ import print_function
"""Implement Idle Shell history mechanism with History class"""

import os
from types import MethodType

from idlesporklib.configHandler import idleConf
from idlesporklib.IdlePrehistory import Prehistory


class SuperHistory(object):
    def __init__(self, history):
        self.history = history

    def __getitem__(self, item):
        pass


class History(object):
    """Implement Idle Shell history mechanism.

    store - Store source statement (called from PyShell.resetoutput).
    fetch - Fetch stored statement matching prefix already entered.
    history_next - Bound to <<history-next>> event (default Alt-N).
    history_prev - Bound to <<history-prev>> event (default Alt-P).
    """
    def __init__(self, pyshell):
        """Initialize data attributes and bind event methods.

        .text - Idle wrapper of tk Text widget, with .bell().
        .history - source statements, possibly with multiple lines.
        .prefix - source already entered at prompt; filters history list.
        .pointer - index into history.
        .cyclic - wrap around history list (or not).

        @type pyshell: idlesporklib.PyShell.PyShell
        """
        if 'SPORKPATH' not in os.environ.keys():
            self.ph = Prehistory(os.path.expanduser('~'))
        else:
            self.ph = Prehistory(os.environ['SPORKPATH'])
        self.pyshell = pyshell
        self.text = text = pyshell.text
        self.history = self.ph.get()
        self.super_history = list(enumerate(self.history))
        self.smart_history = []
        self.prefix = None
        self.pointer = None
        self.suggested = []
        self.cyclic = idleConf.GetOption("main", "History", "cyclic", 1, "bool")
        text.bind("<<history-previous>>", self.history_prev)
        text.bind("<<history-next>>", self.history_next)
        text.bind("<<history-guess>>", self.history_guess)

    def check_changed(self):
        # If pointer and prefix are set, check if they are still "true", i.e. user didn't change line since
        # last fetch.
        if self.pointer is not None and self.prefix is not None:
            if self.text.compare("insert", "!=", "end-1c") or \
                    (self.suggested and self.text.get("iomark", "end-1c") != self.suggested[-1][0]):
                # Things have changed - reset pointer and prefix.
                self.pointer = self.prefix = None
                self.suggested[:] = []
                self.text.mark_set("insert", "end-1c")  # != after cursor move

    # noinspection PyUnusedLocal
    def history_next(self, event):
        """Fetch later statement; start with ealiest if cyclic."""
        # self.fetch(reverse=False)

        self.check_changed()

        if len(self.suggested):
            self.suggested.pop()

            if len(self.suggested):
                item, pointer = self.suggested[-1]
                self.text.delete("iomark", "end-1c")
                self.text.insert("iomark", item)
                self.histwin.goto(self.super_history[pointer][0])
            else:
                if self.text.get("iomark", "end-1c") != self.prefix:
                    self.text.delete("iomark", "end-1c")
                    self.text.insert("iomark", self.prefix)
                self.pointer = self.prefix = None
                self.text.see("insert")
                self.text.tag_remove("sel", "1.0", "end")

        return "break"

    # noinspection PyUnusedLocal
    def history_prev(self, event):
        """Fetch earlier statement; start with most recent."""
        self.fetch(self.super_history)
        return "break"

    # noinspection PyUnusedLocal
    def history_guess(self, event):
        """Guess next line based on previous line."""
        self.fetch(self.smart_history)
        return "break"

    def fetch(self, history):
        """Fetch statememt and replace current line in text widget.

        Set prefix and pointer as needed for successive fetches.
        Reset them to None, None when returning to the start line.
        Sound bell when return to start line or cannot leave a line
        because cyclic is False.
        """
        self.check_changed()

        nhist = len(history)
        pointer = self.pointer
        prefix = self.prefix
        suggested = self.suggested

        # If pointer or prefix are not set, maybe because of reset above, need to get them.
        if pointer is None or prefix is None:
            prefix = self.text.get("iomark", "end-1c")
            pointer = nhist  # will be decremented

        suggested_items = zip(*suggested)[0] if suggested else []

        nprefix = len(prefix)
        while True:
            pointer -= 1

            # Is it the end of the line?
            if pointer < 0 or pointer >= nhist:
                self.text.bell()

                # Yes.
                if not self.cyclic and pointer < 0:  # abort history_prev
                    return
                # No.
                else:
                    if self.text.get("iomark", "end-1c") != prefix:
                        self.text.delete("iomark", "end-1c")
                        self.text.insert("iomark", prefix)
                    pointer = prefix = None
                break

            # Check the line for a match.
            real_pointer, item = history[pointer]

            if item not in suggested_items and item[:nprefix] == prefix and len(item) > nprefix:
                self.text.delete("iomark", "end-1c")
                self.text.insert("iomark", item)
                self.histwin.goto(real_pointer)
                suggested.append((item, pointer))
                break

        self.text.see("insert")
        self.text.tag_remove("sel", "1.0", "end")
        self.pointer = pointer
        self.prefix = prefix

    def update_smart_history(self, source):
        source = source.strip()
        self.smart_history = [(i, line.strip())
                              for i, line in self.super_history if self.super_history[i - 1][1].strip() == source]

    def store(self, source):
        """Store Shell input statement into history list."""
        source = source.strip()
        history = self.history

        if len(source) > 0:
            history.append(source)
            self.ph.append(source)
            self.histwin.store(source)

            self.super_history = list(enumerate(history))
            self.update_smart_history(source)

        self.pointer = None
        self.prefix = None
        self.suggested[:] = []


if __name__ == "__main__":
    from unittest import main
    main('idlesporklib.idle_test.test_idlehistory', verbosity=2, exit=False)

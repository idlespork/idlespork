"""AutoComplete.py - An IDLE extension for automatically completing names.

This extension can complete either attribute names of file names. It can pop
a window with all available names, for the user to select from.
"""
import os
import sys
import string
import keyword
import PyShell

from configHandler import idleConf
from CallTipWindow import CallTip
from idlesporklib.ModuleCompletion import ModuleCompletion
from idlesporklib.EnablableExtension import boundremotefunc

# This string includes all chars that may be in a file name (without a path
# separator)

FILENAME_CHARS = string.ascii_letters + string.digits + os.curdir + "._~#$:-"
# This string includes all chars that may be in an identifier
ID_CHARS = string.ascii_letters + string.digits + "_"
# Flag to show tool tip instead of completion window.
SHOWCALLTIP = 'SHOWCALLTIP'

# These constants represent the three different types of completions
COMPLETE_ATTRIBUTES, COMPLETE_FILES, COMPLETE_KEYS = range(1, 3+1)

import AutoCompleteWindow
from HyperParser import HyperParser

import __main__

SEPS = os.sep
if os.altsep:  # e.g. '/' on Windows...
    SEPS += os.altsep

class AutoComplete:
    """
    Extension to allow automatic completion of text.

    Set the autocomplete and try-open-completions key bindings.
    Options:
        popupwait - how many millisecs to wait before opening window.

        onlycontaining - if True, the autocomplete window will first only show names that contain the typed text.
    If you double press the key for autocomplete, the list of names will grow to include all names.

        imports - if True, names available for import statements will be completed too.

        imports-timeout - (proximal) maximum delay until import completion returns.

        twotabstocomplete - sets if two tabs are required to complete text once window is open.

        entertocomplete - sets if pressing enter completes a name.

        dictkeys - if forced open is fired and cursor is just after '[', show window containing the dict keys.

        showlengths - allows showing of lengths of lists and tuples.
    """

    menudefs = [
        ('edit', [
            ("Show Completions", "<<force-open-completions>>"),
        ])
    ]

    popupwait = idleConf.GetOption("extensions", "AutoComplete",
                                   "popupwait", type="int", default=0)

    # Flag to show only completions that actually contain typed word.
    onlycontaining = idleConf.GetOption("extensions", "AutoComplete",
                                        "onlycontaining", type="bool", default=False, member_name='onlycontaining')

    # Flag to auto complete imports.
    imports = idleConf.GetOption("extensions", "AutoComplete",
                                 "imports", type="bool", default=False, member_name='imports')

    # Flag to complete after two tabs.
    twotabstocomplete = idleConf.GetOption("extensions", "AutoComplete",
                                           "twotabstocomplete", type="bool", default=True, member_name='twotabstocomplete')

    # Flag to complete when enter is pressed.
    entertocomplete = idleConf.GetOption("extensions", "AutoComplete",
                                         "entertocomplete", type="bool", default=False, member_name='entertocomplete')

    # Flag to show dictionary keys.
    dictkeys = idleConf.GetOption("extensions", "AutoComplete",
                                  "dictkeys", type="bool", default=False, member_name='dictkeys')

    # Flag to allow showing length of lists and tuples.
    showlengths = idleConf.GetOption("extensions", "AutoComplete",
                                     "showlengths", type="bool", default=False, member_name='showlengths')

    def __init__(self, editwin=None):
        self.editwin = editwin
        if editwin is None:  # subprocess and test
            return
        self.text = editwin.text
        self.autocompletewindow = None

        # id of delayed call, and the index of the text insert when the delayed
        # call was issued. If _delayed_completion_id is None, there is no
        # delayed call.
        self._delayed_completion_id = None
        self._delayed_completion_index = None

    def _make_autocomplete_window(self):
        return AutoCompleteWindow.AutoCompleteWindow(self.text, self.twotabstocomplete, self.entertocomplete)

    def _remove_autocomplete_window(self, event=None):
        if self.autocompletewindow:
            self.autocompletewindow.hide_window()
            self.autocompletewindow = None

    def is_executing(self):
        return isinstance(self.editwin, PyShell.PyShell) and \
            self.editwin.executing

    def force_open_completions_event(self, event):
        """
        Happens when the user really wants to open a completion list, even
        if a function call is needed.
        """
        if self.is_executing():
            return
        self.open_completions(True, False, True)

    def try_open_completions_event(self, event):
        """
        Happens when it would be nice to open a completion list, but not
        really necessary, for example after an dot, so function
        calls won't be made.
        """

        if self.is_executing():
            return

        lastchar = self.text.get("insert-1c")
        if lastchar == ".":
            self._open_completions_later(False, False, False,
                                         COMPLETE_ATTRIBUTES)
        elif lastchar in SEPS:
            self._open_completions_later(False, False, False,
                                         COMPLETE_FILES)

    def autocomplete_event(self, event):
        """
        Happens when the user wants to complete his word, and if necessary,
        open a completion list after that (if there is more than one
        completion)
        """
        if hasattr(event, "mc_state") and event.mc_state:
            # A modifier was pressed along with the tab, continue as usual.
            return
        if self.autocompletewindow and self.autocompletewindow.is_active():
            self.autocompletewindow.complete()
            return "break"
        else:
            opened = self.open_completions(False, True, True)
            if opened:
                return "break"

    def _open_completions_later(self, *args):
        self._delayed_completion_index = self.text.index("insert")
        if self._delayed_completion_id is not None:
            self.text.after_cancel(self._delayed_completion_id)
        self._delayed_completion_id = \
            self.text.after(self.popupwait, self._delayed_open_completions,
                            *args)

    def _delayed_open_completions(self, *args):
        self._delayed_completion_id = None
        if self.text.index("insert") != self._delayed_completion_index:
            return
        self.open_completions(*args)

    def open_completions(self, evalfuncs, complete, userWantsWin, mode=None):
        """Find the completions and create the AutoCompleteWindow.
        Return True if successful (no syntax error or so found).
        if complete is True, then if there's nothing to complete and no
        start of completion, won't open completions and return False.
        If mode is given, will open a completion list only in this mode.
        """
        # Cancel another delayed call, if it exists.
        if self._delayed_completion_id is not None:
            self.text.after_cancel(self._delayed_completion_id)
            self._delayed_completion_id = None

        # If the window is already open, show the big list of completions.
        # This means that a double Ctrl-space opens the big list every time, which is nice.
        if self.autocompletewindow is not None and self.autocompletewindow.autocompletewindow is not None:
            showbig = True
        else:
            showbig = False

        hp = HyperParser(self.editwin, "insert")
        curline = self.text.get("insert linestart", "insert")
        i = j = len(curline)

        # Check if it's an import statement.
        # This is seperated from the rest since the pattern check is in ModuleCompletion.
        imports = self.get_module_completion(curline)
        if imports:
            if imports == ([], []):
                return
            comp_lists = imports
            while i and curline[i - 1] in ID_CHARS:
                i -= 1
            comp_start = curline[i:j]
        elif self.dictkeys and hp.is_in_dict() and (not mode or mode==COMPLETE_KEYS) and evalfuncs:
            self._remove_autocomplete_window()
            mode = COMPLETE_KEYS
            while i and curline[i - 1] in ID_CHARS + '"' + "'":
                i -= 1
            comp_start = curline[i:j]
            if curline[i - 1:i] == "[":
                hp.set_index("insert-%dc" % (len(curline) - (i - 1)))
                comp_what = hp.get_expression()
            else:
                comp_what = ""
        elif (hp.is_in_string() or hp.is_in_command()) \
            and (not mode or mode==COMPLETE_FILES):
            self._remove_autocomplete_window()
            mode = COMPLETE_FILES
            while i and curline[i-1] in FILENAME_CHARS:
                i -= 1
            comp_start = curline[i:j]
            j = i
            while i and curline[i-1] in FILENAME_CHARS + SEPS:
                i -= 1
            comp_what = curline[i:j]
        elif hp.is_in_code() and (not mode or mode==COMPLETE_ATTRIBUTES):
            self._remove_autocomplete_window()
            mode = COMPLETE_ATTRIBUTES

            while i and curline[i-1] in ID_CHARS:
                i -= 1
            comp_start = curline[i:j]
            if i and curline[i-1] == '.':
                hp.set_index("insert-%dc" % (len(curline)-(i-1)))
                comp_what = hp.get_expression()

                if not comp_what or \
                   (not evalfuncs and comp_what.find('(') != -1):
                    return
            else:
                comp_what = ""
        else:
            return

        # For everything but imports, call fetch_completions
        if not imports:
            if complete and not comp_what and not comp_start:
                return
            comp_lists = self.fetch_completions(comp_what, mode)
            if not comp_lists[0]:
                return

        # It's nice to be able to see the length of a tuple/list (but not anything more complicated)
        if comp_lists[0] == SHOWCALLTIP:
            parenleft = self.text.index('insert-1c')
            CallTip(self.text).showtip(comp_lists[1], parenleft, parenleft.split('.')[0] + '.end')
            return

        if mode == COMPLETE_ATTRIBUTES and not imports:
            calltips = self.editwin.extensions.get('CallTips')
            if calltips:
                args = calltips.arg_names(evalfuncs)
                if args:
                    args = [a + '=' for a in args]
                    comp_lists = sorted(comp_lists[0] + args), sorted(comp_lists[1] + args)

        # Check if we want to show only completion containing typed word.
        if self.onlycontaining:
            # Small optimization
            comp_lower = comp_start.lower()
            # Find such completions.
            comp_lists = [name for name in comp_lists[0] if comp_lower in name.lower()], comp_lists[1]
            # If none were found, look in big list.
            if not comp_lists[0]:
                comp_lists = [name for name in comp_lists[1] if comp_lower in name.lower()], comp_lists[1]
            # If still none were found, just return the big list - which is the default anyway.
            if not comp_lists[0]:
                comp_lists = comp_lists[1], comp_lists[1]

        if showbig:
            comp_lists = comp_lists[1], []

        self.autocompletewindow = self._make_autocomplete_window()
        return not self.autocompletewindow.show_window(
                comp_lists, "insert-%dc" % len(comp_start),
                complete, mode, userWantsWin, onlycontaining=self.onlycontaining)

    def fetch_completions(self, what, mode):
        """Return a pair of lists of completions for something. The first list
        is a sublist of the second. Both are sorted.

        If there is a Python subprocess, get the comp. list there.  Otherwise,
        either fetch_completions() is running in the subprocess itself or it
        was called in an IDLE EditorWindow before any script had been run.

        The subprocess environment is that of the most recently run script.  If
        two unrelated modules are being edited some calltips in the current
        module may be inoperative if the module was not the last to run.
        """
        try:
            rpcclt = self.editwin.flist.pyshell.interp.rpcclt
        except:
            rpcclt = None
        if rpcclt:
            return rpcclt.remotecall("exec", "get_the_completion_list",
                                     (what, mode), {})
        else:
            bigl = smalll = []
            if mode == COMPLETE_ATTRIBUTES:
                if what == "":
                    namespace = __main__.__dict__.copy()
                    namespace.update(__main__.__builtins__.__dict__)
                    bigl = eval("dir()", namespace) + keyword.kwlist
                    bigl = sorted(set(bigl))
                    if "__all__" in bigl:
                        smalll = sorted(set(eval("__all__", namespace)))
                    else:
                        smalll = [s for s in bigl if s[:1] != '_']
                else:
                    try:
                        entity = self.get_entity(what)
                        bigl = dir(entity)
                        bigl = sorted(set(bigl))
                        if "__all__" in bigl:
                            smalll = sorted(set(entity.__all__))
                        else:
                            smalll = [s for s in bigl if s[:1] != '_']
                    except:
                        return [], []

            elif mode == COMPLETE_FILES:
                if what == "":
                    what = "."
                try:
                    from os.path import normcase
                    expandedpath = os.path.expanduser(what)
                    bigl = os.listdir(expandedpath)
                    try:
                        cmp_ = cmp
                    except NameError:
                        cmp_ = lambda x, y: (x > y) - (x < y)
                    bigl = sorted(set(bigl), cmp=lambda x,y: cmp_(normcase(x), normcase(y)))
                    smalll = [s for s in bigl if s[:1] != '.']
                except OSError:
                    return [], []
            elif mode == COMPLETE_KEYS:
                entity = None
                try:
                    entity = self.get_entity(what)
                    keys = set()
                    for key in entity.keys():
                        try:
                            r = repr(key)
                            if not r.startswith('<'):
                                keys.add(r)
                        except:
                            pass
                    smalll = bigl = sorted(keys)
                except:
                    # If the entity is a list or tuple let's show the length.
                    # It is so common to go back to the start of the line, write "len(", go to the end, write ")",
                    # evaluate, then remove the "len", and finally do what you actually wanted to do...
                    # In any case, it's configurable.
                    try:
                        if isinstance(entity, list):
                            return SHOWCALLTIP, 'list[0..%d]' % len(entity)
                        elif isinstance(entity, tuple):
                            return SHOWCALLTIP, 'tuple[0..%d]' % len(entity)
                    except:
                        pass
                    return [], []

            if not smalll:
                smalll = bigl
            return smalll, bigl

    def get_entity(self, name):
        """Lookup name in a namespace spanning sys.modules and __main.dict__ or import module"""
        namespace = sys.modules.copy()
        namespace.update(__main__.__dict__)
        return eval(name, namespace)

    @boundremotefunc
    def get_module_completion(self, line):
        """Get module completions for the line"""
        return ModuleCompletion.module_completion(line)


if __name__ == '__main__':
    from unittest import main
    main('idlesporklib.idle_test.test_autocomplete', verbosity=2)

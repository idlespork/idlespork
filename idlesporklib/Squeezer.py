# This file was originally copied for Tal Einat's Squeezer package.
# It was slightly modified by the idlespork team

"""
Squeezer - using this extension will make long texts become a small button.
"""

import re
from PyShell import PyShell
from configHandler import idleConf
import Tkinter
import tkFont
import os


# define IDLE-infrastructure specific functions

def _get_base_text(editwin):
    "Return the base Text widget of an editwin, which can be changed before "\
    "the iomark."
    return editwin.per.bottom

def _add_to_rmenu(editwin, specs):
    "Add specs to the right-click menu of the given editwin."
    editwin.rmenu_specs = editwin.rmenu_specs + specs


# define a function to count the number of lines in a given string
_TABWIDTH = 8
_LINEWIDTH = 80
_tab_newline_re = re.compile(r"[\t\n]")
_tab_table_cache = {}

def _countlines(s, linewidth=_LINEWIDTH, tabwidth=_TABWIDTH):
    if (tabwidth, linewidth) not in _tab_table_cache:
        _tab_table_cache[(tabwidth, linewidth)] = \
            [ncols+tabwidth-(ncols%tabwidth) for ncols in xrange(linewidth)]
    tab_table = _tab_table_cache[(tabwidth, linewidth)]

    pos = 0
    linecount = 1
    current_column = 0

    for m in _tab_newline_re.finditer(s):
        # process the normal chars up to tab or newline
        numchars = m.start() - pos
        if numchars > 0: # must special-case, otherwise divmod(-1, linewidth)
            # If the length was exactly linewidth, divmod would give
            # (1,0), even though a new line hadn't yet been started.
            # Therefore subtract 1 before doing divmod, and later add
            # 1 to the column to compensate.
            lines, column = divmod(current_column + numchars - 1, linewidth)
            linecount += lines
            current_column = column + 1
            pos += numchars

        # deal with tab or newline
        if s[pos] == '\n':
            linecount += 1
            current_column = 0
        else:
            assert s[pos] == '\t'
            current_column = tab_table[current_column]

        pos += 1 # after the tab or newline

    # process remaining chars (no more tabs or newlines)
    numchars = len(s) - pos
    if numchars > 0: # must special-case, otherwise divmod(-1, linewidth)
        linecount += (current_column + numchars - 1) // linewidth
    return linecount


def tags_in_range(text, start, end):
    """Helper function to get all the tags between two indexes"""
    tags = []
    start = text.index(start)
    names = text.tag_names()

    for name in names:
        rng = text.tag_prevrange(name, end)
        while rng:
            i0, i1 = rng
            if text.compare(i0, '<', start):
                i0 = start
            if text.compare(end, '<', i1):
                i1 = end
            if text.compare(i1, '<=', i0):
                break
            tags.append((name, len(text.get(start, i0)), len(text.get(i0, i1))))
            newrng = text.tag_prevrange(name, i0)
            if rng == newrng:
                break
            rng = newrng

    return tags


# define the extension's classes

class ExpandingButton(Tkinter.Button):
    def __init__(self, s, tags, numoflines, squeezer, def_line=None, rangetags=()):
        self.s = s
        self.tags = tags
        self.squeezer = squeezer
        self.editwin = editwin = squeezer.editwin
        self.text = text = editwin.text
        self.rangetags = rangetags

        # If this is for a stdin area, we should remember the line just before so it will appear in preview and copy.
        self.def_line = def_line
        
        Tkinter.Button.__init__(self, text,
                                text=self.get_caption(numoflines),
                                background="#FFFFC0",
                                activebackground="#FFFFE0")
        self.bind("<Double-Button-1>", self.expand)
        self.bind("<Button-2>", self.copy)
        if squeezer._PREVIEW_COMMAND:
            self.bind("<Button-3>", self.preview)
        self.selection_handle(lambda offset,length: s[int(offset):int(offset)+int(length)])

    def get_caption(self, numoflines=None):
        if numoflines is None:
            numoflines = self.squeezer.count_lines(self.s)

        # This is just a cute indicator if the squeezed area is stdout/stderr or stdin.
        typ = 'code' if self.tags == 'stdin' else 'text'

        caption = "Squeezed %s (about %d lines). "\
                  "Double-click to expand, middle-click to copy" % (typ, numoflines)
        if self.squeezer._PREVIEW_COMMAND:
            caption += ", right-click to preview."
        else:
            caption += "."
        return caption

    def update_btn(self):
        self['text'] = self.get_caption()
        
    def expand(self, event):
        # We must use the original insert and delete methods of the Text widget,
        # to be able to change text before the iomark.
        expanded_txt = self.s[:Squeezer._MAX_EXPAND]
        rem_txt = self.s[Squeezer._MAX_EXPAND:]

        basetext = _get_base_text(self.editwin)
        start = self.text.index(self)
        basetext.insert(start, expanded_txt, self.tags)

        if self.rangetags:
            for name, i0, i1, in self.rangetags:
                basetext.tag_add(name, start + '+%dc' % i0, start + '+%dc+%dc' % (i0, i1))

        if len(rem_txt) == 0:
            basetext.delete(self)
            self.squeezer.expandingbuttons.remove(self)
        else:
            self.s = rem_txt
            self.update_btn()

    def copypreview_txt(self):
        # Return correct text for copy and preview.
        if self.tags == 'stdin':
            return self.def_line + '\n' + self.s
        else:
            return self.s
        
    def copy(self, event):
        self.clipboard_clear()
        self.clipboard_append(self.copypreview_txt(), type='STRING')
        self.selection_own()

    def preview(self, event):
        from tempfile import mktemp
        fn = mktemp("longidletext")
        f = open(fn, "w")
        f.write(self.copypreview_txt())
        f.close()
        os.system(self.squeezer._PREVIEW_COMMAND % {"fn":fn})
            
    def expand_back(self, s):
        self.s = s + self.s
        self.update_btn()

class Squeezer:
    """
    Extension to squeeze long output into a button

    This file was originally copied for Tal Einat's Squeezer package.

    Options:
        max-num-of-lines - output bigger than this will be squeezed.

        max-expand - output will never be more than this amount of characters.

        preview-command-nt(-win) - command to open preview application.

        squeeze-code - flag for allowing to squeeze code.

    Configure the key bindings expand-last-squeezed, preview-last-squeezed and squeeze-current-text.
    """
    _MAX_NUM_OF_LINES = idleConf.GetOption("extensions", "Squeezer",
                                           "max-num-of-lines", type="int",
                                           default=30)

    _MAX_EXPAND = idleConf.GetOption(
        "extensions", "Squeezer", "max-expand", type="int", default=50000)

    _PREVIEW_COMMAND = idleConf.GetOption(
        "extensions", "Squeezer",
        "preview-command-"+{"nt":"win"}.get(os.name, os.name),
        default="", raw=True)

    # Flag for whether or not stdin can be squeezing
    _SQUEEZE_CODE = idleConf.GetOption("extensions", "Squeezer", "squeeze-code", type="bool", default=False,
                                       member_name='_SQUEEZE_CODE')

    menudefs = [
        ('edit', [
            None,   # Separator
            ("Expand last squeezed text", "<<expand-last-squeezed>>"),
        ])
    ]
    if _PREVIEW_COMMAND:
        menudefs[0][1].append(("Preview last squeezed text",
                               "<<preview-last-squeezed>>"))

        
    def __init__(self, editwin):
        self.editwin = editwin
        self.text = text = editwin.text
        self.expandingbuttons = []
        if isinstance(editwin, PyShell):
            # If we get a PyShell instance, replace its write method with a
            # wrapper, which inserts an ExpandingButton instead of a long text.
            def mywrite(s, tags=(), write=editwin.write):
                if tags != "stdout":
                    return write(s, tags)
                else:
                    numoflines = self.count_lines(s)
                    if numoflines < self._MAX_NUM_OF_LINES:
                        return write(s, tags)
                    else:
                        expandingbutton = ExpandingButton(s, tags, numoflines,
                                                          self)
                        text.mark_gravity("iomark", Tkinter.RIGHT)
                        text.window_create("iomark",window=expandingbutton,
                                           padx=3, pady=5)
                        text.see("iomark")
                        text.update()
                        text.mark_gravity("iomark", Tkinter.LEFT)
                        self.expandingbuttons.append(expandingbutton)
            editwin.write = mywrite

            # Add squeeze-current-text to the right-click menu
            text.bind("<<squeeze-current-text>>",
                      self.squeeze_current_text_event)
            _add_to_rmenu(editwin, [("_Squeeze current text",
                                     "<<squeeze-current-text>>")])

    def count_lines(self, s):
        "Calculate number of lines in given text.\n\n" \
        "Before calculation, the tab width and line length of the text are" \
        "fetched, so that up-to-date values are used."
        # Tab width is configurable
        tabwidth = self.editwin.get_tabwidth()

        text = self.editwin.text
        # Get the Text widget's size
        linewidth = text.winfo_width()
        # Deduct the border and padding
        linewidth -= 2*sum([int(text.cget(opt))
                            for opt in ('border','padx')])

        # Get the Text widget's font
        font = tkFont.Font(text, name=text.cget('font'))

        # Divide the size of the Text widget by the font's width.
        # According to Tk8.4 docs, the Text widget's width is set
        # according to the width of its font's '0' (zero) character,
        # so we will use this as an approximation.
        linewidth //= font.measure('0')
        
        return _countlines(s, linewidth, tabwidth)

    def expand_last_squeezed_event(self, event):
        """Expands bottom most squeezed block"""
        if self.expandingbuttons:
            self.expandingbuttons[-1].expand(event)
        else:
            self.text.bell()
        return "break"

    def preview_last_squeezed_event(self, event):
        """Opens a defined application to show squeezed text"""
        if self._PREVIEW_COMMAND and self.expandingbuttons:
            self.expandingbuttons[-1].preview(event)
        else:
            self.text.bell()
        return "break"

    def squeeze_last_output_event(self, event):
        """Squeezes bottom most un-squeezed block"""
        last_console = self.text.tag_prevrange("console",Tkinter.END)
        if not last_console:
            return "break"

        prev_ranges = []
        for tag_name in ("stdout","stderr"):
            rng = last_console
            while rng:
                rng = self.text.tag_prevrange(tag_name, rng[0])
                if rng and self.text.get(*rng).strip():
                    prev_ranges.append((rng, tag_name))
                    break
        if not prev_ranges:
            return "break"

        # Get max element dynamically, in case the number of allowed tags to squeeze ever changes.
        max_rng = prev_ranges[0]
        for rng in prev_ranges[1:]:
            if self.text.compare(max_rng[0][0], '<', rng[0][0]):
                max_rng = rng

        if not self.squeeze_range(*max_rng):
            self.text.bell()
        return "break"
        
    def squeeze_current_text_event(self, event):
        """Squeeze selected block"""
        insert_tag_names = self.text.tag_names(Tkinter.INSERT)
        for tag_name in ("stdout", "stderr"):
            if tag_name in insert_tag_names:
                break
        else:
            # Check if code squeezing is enabled.
            if self._SQUEEZE_CODE and 'stdin' in insert_tag_names:
                tag_name = 'stdin'
            else:
                # no tag associated with the index
                self.text.bell()
                return "break"

        # find the range to squeeze
        rng = self.text.tag_prevrange(tag_name, Tkinter.INSERT+"+1c")
        if not self.squeeze_range(rng, tag_name):
            self.text.bell()
        return "break"

    def squeeze_range(self, rng, tag_name):
        if not rng or rng[0]==rng[1]:
            return False
        start, end = rng

        # If it's code that we are squeezing then we only squeeze from the second row. I think this is nicer, because
        # mostly we'll be squeezing function definitions, and this will keep the 'def ...' visible.
        if tag_name == 'stdin':
            # It's nice to save the line just before, the "def" line, so it appears in preview and copy
            # of the ExpandingButton.
            def_line = self.text.get(start, start + " lineend")
            start = self.text.index("%s+1l linestart" % start)
        else:
            def_line = None

        old_expandingbutton = self.find_button(end)
        
        s = self.text.get(start, end)
        # if the last char is a newline, remove it from the range
        if s and s[-1] == '\n':
            end = self.text.index("%s-1c" % end)
            s = s[:-1]

        # This will preserve all tags, such as for colors and links
        rangetags = tags_in_range(self.text, start, end)
        # delete the text
        _get_base_text(self.editwin).delete(start, end)

        if old_expandingbutton is not None and \
           old_expandingbutton.tags == tag_name:
            old_expandingbutton.expand_back(s)
            return True

        # prepare an ExpandingButton
        numoflines = self.count_lines(s)
        expandingbutton = ExpandingButton(s, tag_name, numoflines, self, def_line=def_line, rangetags=rangetags)
        # insert the ExpandingButton to the Text
        self.text.window_create(start, window=expandingbutton,
                                padx=3, pady=5)
        # insert the ExpandingButton to the list of ExpandingButtons
        i = len(self.expandingbuttons)
        while i > 0 and self.text.compare(self.expandingbuttons[i-1],
                                          ">", expandingbutton):
            i -= 1
        self.expandingbuttons.insert(i, expandingbutton)
        return True

    def find_button(self, pos):
        for btn in self.expandingbuttons:
            if self.text.compare(pos, "==", btn):
                return btn
        return None

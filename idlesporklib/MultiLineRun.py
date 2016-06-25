# IDLEX EXTENSION
##    """
##    Copyright(C) 2012 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##    License: See LICENSE.txt
##    """

##
##  This extension allows for pasting of multiple lines of code into the shell
##  for execution. This addresses http://bugs.python.org/issue3559
##  Ofir: I fixed the function "dedent", still needs work.

from __future__ import print_function

config_extension_def = """
[MultiLineRun]
enable=1
enable_editor=0
enable_shell=1
"""

from idlesporklib.configHandler import idleConf
from idlesporklib.Delegator import Delegator
import time
import re
import sys
import traceback

INDENT_CHARS = set(" \t")

class MultiLineDelegator(Delegator):
    def __init__(self, callback):
        Delegator.__init__(self)
        self.callback = callback
        self.paste = False

    def insert(self, index, chars, tags=None):
        if self.paste:
            self.paste = False
            try:
                chars = self.callback(chars)
            except Exception as err:
                # Must catch exception else IDLE closes
                print(' MultiLineRun Internal Error', file=sys.stderr)
                traceback.print_exc()

        self.delegate.insert(index, chars, tags)

    def delete(self, index1, index2=None):
        self.delegate.delete(index1, index2)


class MultiLineRun(object):
    # eol code from IOBinding.py
    eol = r"(\r\n)|\n|\r"  # \r\n (Windows), \n (UNIX), or \r (Mac)
    eol_re = re.compile(eol)

    def __init__(self, editwin):
        self.editwin = editwin      # reference to the editor window
        self.text = text = self.editwin.text

        self.mld = MultiLineDelegator(self.paste_intercept)
        self.editwin.per.insertfilter(self.mld)

        self.text.bind('<<Paste>>', self.paste, '+')

        wsys = text.tk.call('tk', 'windowingsystem')
        if wsys == 'x11':
            self.text.bind('<Button-2>', self.paste, '+')  # For X11 middle click

    def paste(self, event=None):
        self.mld.paste = True

    def paste_intercept(self, chars):
        if self.editwin.executing:
            # Do nothing
            return chars

        chars = self.eol_re.sub(r"\n", chars)

        lines = chars.splitlines()
        lines = self.dedent(lines)

        return "\n".join(lines)

    def dedent(self, lines):
        """
        remove maximal amount of indents/spaces shared by all lines
        to enable pasting an equally indented region
        """
        # exclude commented-out lines, empty lines for calculation of greatest common indent to strip

        indentation = self.find_max_indent(lines)
        indentation_len = len(indentation)
        lines = [line[indentation_len:] if line.startswith(indentation) else line
                 for line in lines]
        return lines

    def find_max_indent(self, lines):
        """
        Return the common indentation shared by all lines,
        not including empty and comment lines
        """
        Lcode = [line for line in lines
                 if line.rstrip() and not line.lstrip().startswith('#')]
        indentation = []
        idx = 0
        while True:
            cur_char = set(line[idx] for line in Lcode)
            if len(cur_char) != 1: break
            indent_char = list(cur_char)[0]
            if indent_char not in INDENT_CHARS: break
            indentation.append(indent_char)
            idx += 1
        return "".join(indentation)

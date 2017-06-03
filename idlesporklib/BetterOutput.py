"""
BetterOutput - an extension which replaces the write method of the PyShell,
so that \r will return to the beginning of line, and xterm escape sequences
won't be printed.
"""

import re

from OutputWindow import OutputWindow
import Links

def _get_base_text(editwin):
    "Return the base Text widget of an editwin, which can be changed before "\
    "the iomark."
    return editwin.per.bottom

def _combine_strings(strings):
    "If all strings were written with \\r between them, what will be printed?"
    lasts = ""
    for s in strings:
        lasts = s + lasts[len(s):]
    return lasts
    

class BetterOutput:
    
    escapeCodes = re.compile(r"\x1b\[[\d;]*m")

    def __init__(self, editwin):
        import PyShell
        if not isinstance(editwin, PyShell.PyShell):
            return
     
        self.use_subprocess = PyShell.use_subprocess
        self.editwin = editwin
        self.text = editwin.text
        self.basetext = _get_base_text(editwin)

        # last line length
        self.lllength = 0
        # In which column is the logical cursor in last line
        self.llinsert = 0
        # The iomark index last time mywrite was called
        self.lastiomark = ""
        # Do we have an added newline
        self.addedNewline = False
        # Do we need to add a newline (ie. some console text was written)
        self.addNewline = False
        # Was a console text written?
        self.wasConsole = False

        if "Squeezer" in editwin.extensions:
            editwin.extensions["Squeezer"].origwrite = self.mywrite
        else:
            editwin.write = self.mywrite

    def mywrite(self, s, tags=()):
        """
        while the iomark isn't changed by other functions, write in two regions:
        if tags == 'console', it will be written at the end, on the iomark.
        otherwise, it will be written before that, at the consolemark, and
        be \\r treated.
        If some console text was written, a newline will be added before the
        consolemark, unless a newline is already there.
        """
        # I'm not sure what the try and except exactly mean, but I copied them
        # from the original PyShell.write.
        try:
            # Remove escape codes
            s = self.escapeCodes.sub("", s)

            # Make it possible to write at the iomark
            self.text.mark_gravity("iomark", "right")

            # If position was changed, reset my data
            if self.text.index("iomark") != self.lastiomark:
                self.lllength = 0
                self.llinsert = 0
                self.addedNewline = False
                self.addNewline = False
                self.wasConsole = False
                self.text.mark_set("consolemark", "iomark")
                self.text.mark_gravity("consolemark", "left")

            # Remove the added newline, if there is one
            if self.addedNewline:
                self.basetext.delete("consolemark-1c", "consolemark")
                self.addedNewline = False

            # Write s
            if tags == "console":
                OutputWindow.write(self.editwin, s, tags, "iomark")
                if s:
                    if not self.wasConsole and s[0] != '\n':
                        self.addNewline = True
                    self.wasConsole = True

            else:
                self.text.mark_gravity("consolemark", "right")
                lines = s.split('\n')

                for i in range(len(lines)):
                    line = lines[i]
                    segments = line.split('\r')
                    
                    if i == 0:
                        insertindex = self.text.index("consolemark-%dc" %
                                                     (self.lllength -
                                                      self.llinsert))
                        self.basetext.delete(insertindex,
                                             insertindex + ("+%dc" % min(
                            len(segments[0]),
                            self.lllength-self.llinsert)))
                        self.basetext.insert(insertindex, segments[0], tags)
                        Links.parse(self.basetext, insertindex, \
                            '%s+%dc' % (insertindex, len(segments[0])))
                        self.llinsert = self.llinsert + len(segments[0])
                        self.lllength = max(self.lllength, self.llinsert)
                        
                        if len(segments) > 1:
                            nexts = _combine_strings(segments[1:])
                            insertindex = self.text.index("consolemark-%dc" %
                                                          self.lllength)
                            self.basetext.delete(insertindex,
                                                 insertindex +
                                                 ("+%dc" % min(len(nexts),
                                                               self.lllength)))
                            self.basetext.insert(insertindex, nexts, tags)
                            Links.parse(self.basetext, insertindex, \
                                '%s+%dc' % (insertindex, len(nexts)))
                            self.lllength = max(len(nexts), self.lllength)
                            self.llinsert = len(segments[-1])
                        
                    else:
                        # Line which is not the first
                        nexts = _combine_strings(segments)
                        insertindex = self.basetext.index("consolemark")
                        self.basetext.insert("consolemark", '\n'+nexts, tags)
                        Links.parse(self.basetext, insertindex, \
                            '%s+%dc' % (insertindex, 1 + len(nexts)))
                        self.lllength = len(nexts)
                        self.llinsert = len(segments[-1])

                self.text.mark_gravity("consolemark", "left")

            # Add a newline, if needed:
            if self.addNewline and self.lllength != 0:
                self.text.mark_gravity("consolemark", "right")
                self.basetext.insert("consolemark", "\n")
                self.text.mark_gravity("consolemark", "left")
                self.addedNewline = True

            # Remember current iomark position
            self.lastiomark = self.text.index("iomark")

            # Make it impossible to write at the iomark
            self.text.mark_gravity("iomark", "left")

            # Show what we've done
            self.text.see("insert")
            self.text.update()

        except:
            pass

        # Another part taken from the original PyShell.write
        if self.editwin.canceled:
            self.editwin.canceled = 0
            if not self.use_subprocess:
                raise KeyboardInterrupt
        

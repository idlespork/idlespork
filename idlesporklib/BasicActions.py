"""
An IDLEfork extension which implements some basic actions, so that the binding
could be overridden, or the behaviour made better.
"""

import string

# A list so that 'None in whitespaces' won't raise an exception.
wordchars = list(string.letters + string.digits)
whitespaces = list(string.whitespace)

varnames = wordchars + list('_')


# noinspection PyUnusedLocal,PyProtectedMember
class BasicActions:
    menudefs = []

    def __init__(self, editwin):
        self.editwin = editwin
        self.text = editwin.text
        # Since vertical movement tries to preserve the column, we save the
        # target column (which is changed on most actions, but not on vertical
        # movement), and the last index - to let us know if the column was
        # moved without out notice, in which case targetcol becomes meaningless.
        self.lastindex = ""
        self.targetcol = 0

    def updPos(self, updTargetcol=True):
        self.lastindex = self.text.index("insert")
        if updTargetcol:
            self.targetcol = int(self.lastindex.split('.')[1])
        
    def move_up_event(self, event):
        return self.pos_vertically(-1, False)

    def sel_up_event(self, event):
        return self.pos_vertically(-1, True)

    def move_down_event(self, event):
        return self.pos_vertically(+1, False)

    def sel_down_event(self, event):
        return self.pos_vertically(+1, True)

    def pos_vertically(self, direction, sel):
        """direction is -1 or +1"""
        curindex = self.text.index("insert")
        currow, curcol = map(int, curindex.split('.'))
        if self.lastindex != curindex:
            self.targetcol = curcol

        newrow = currow + direction
        if 1 <= newrow < int(self.text.index("end").split('.')[0]):
            self.editwin._move_cursor("%d.%d" % (newrow, self.targetcol), sel)
        self.updPos(False)
        return "break"

    def move_char_left_event(self, event):
        return self.pos_char_left(False)

    def sel_char_left_event(self, event):
        return self.pos_char_left(True)

    def pos_char_left(self, sel):
        self.editwin._move_cursor("insert-1c", sel)
        self.updPos()
        return "break"

    def move_char_right_event(self, event):
        return self.pos_char_right(False)

    def sel_char_right_event(self, event):
        return self.pos_char_right(True)

    def pos_char_right(self, sel):
        self.editwin._move_cursor("insert+1c", sel)
        self.updPos()
        return "break"

    def move_word_left_event(self, event):
        """Moves cursor a word left like SublimeText would"""
        # return self.pos_word_left(False)
        return self.sublime_pos_word_left(False, False)

    def sel_word_left_event(self, event):
        """Selects a word to the left like SublimeText would"""
        return self.sublime_pos_word_left(True, False)
        # return self.pos_word_left(True)

    def move_subword_left_event(self, event):
        """Moves cursor a subword left like SublimeText would"""
        # return self.pos_word_left(False)
        return self.sublime_pos_word_left(False, True)

    def sel_subword_left_event(self, event):
        """Selects a subword to the left like SublimeText would"""
        return self.sublime_pos_word_left(True, True)
        # return self.pos_word_left(True)

    def pos_word_left(self, sel):
        # First going left until we reach a letter, then going left
        # until we reach a non-letter
        index = "insert-1c"
        while True:
            newindex = self.text.index(index + "-1c")
            if newindex == index or self.text.get(newindex) in wordchars:
                break
            index = newindex
        while True:
            newindex = self.text.index(index + "-1c")
            if newindex == index or self.text.get(newindex) not in wordchars:
                break
            index = newindex

        self.editwin._move_cursor(index, sel)
        self.updPos()

        return "break"

    def sublime_pos_word_left(self, sel, subwords):
        index = "insert-1c"
        c = self.text.get(index)

        while True:
            newindex = self.text.index(index + "-1c")
            if newindex == index:
                break

            c2 = self.text.get(newindex)

            # Dror: I think this is what sublime has, up to some reduction.
            if (not subwords and (c in '\n([' or c2 in '\n([' or (c in varnames and c2 not in varnames) or
                (c not in whitespaces and c2 in whitespaces))) or \
                (subwords and (c in '\n([' or c2 in '\n[' or (c in wordchars and c2 not in wordchars) or (
                    c not in whitespaces and c2 in whitespaces) or (
                    c not in (varnames + whitespaces) and c2 in (wordchars + whitespaces)) or (
                    c == '_' and c2 not in varnames))):
                break

            index = newindex
            c = c2

        self.editwin._move_cursor(index, sel)
        self.updPos()

        return "break"

    def sublime_pos_word_right(self, sel, subwords):
        index = 'insert'
        c = self.text.get(index)
        if c is None:
            return "break"

        while True:
            newindex = self.text.index(index + '+1c')
            c2 = self.text.get(newindex)

            if c2 is None:
                break

            if (not subwords and (c in ')\n' or c2 in ')\n' or (c in varnames and c2 not in varnames) or (
                    c not in whitespaces and c2 in whitespaces))) or (subwords and (
                    c in '(\n' or c2 in '\n' or (c in wordchars and c2 not in wordchars) or (
                    c not in whitespaces and c2 in whitespaces) or (
                    c not in (varnames + whitespaces) and c2 in (wordchars + whitespaces)) or (
                    c not in (varnames + whitespaces) and c2 in (varnames + whitespaces)))):
                break

            index = newindex
            c = c2

        self.editwin._move_cursor(newindex, sel)
        self.updPos()

        return "break"

    def move_word_right_event(self, event):
        """Moves cursor a word to the right like SublimeText would"""
        return self.sublime_pos_word_right(False, False)
        # return self.pos_word_right(False)

    def sel_word_right_event(self, event):
        """Selects a word to the right like SublimeText would"""
        return self.sublime_pos_word_right(True, False)
        # return self.pos_word_right(True)

    def move_subword_right_event(self, event):
        """Moves cursor a subword to the right like SublimeText would"""
        return self.sublime_pos_word_right(False, True)
        # return self.pos_word_right(False)

    def sel_subword_right_event(self, event):
        """Selects a subword to the right like SublimeText would"""
        return self.sublime_pos_word_right(True, True)
        # return self.pos_word_right(True)

    def pos_word_right(self, sel):
        # first go right until we reach a non-letter,
        # then go right until we reach a letter
        index = "insert"
        while True:
            newindex = self.text.index(index + "+1c")
            if newindex == index or self.text.get(index) not in wordchars:
                break
            index = newindex
        while True:
            newindex = self.text.index(index + "+1c")
            if newindex == index or self.text.get(index) in wordchars:
                break
            index = newindex

        self.editwin._move_cursor(index, sel)
        self.updPos()

        return "break"

    def find_content_linestart(self, index):
        """
        Find where the content in the line of index index begins, that is -
        discard console text and whitespaces at the beginning of line.
        """
        con = self.text.tag_nextrange("console", index+" linestart")
        if con and self.text.compare(con[1], "<=", index+" lineend"):
            ind = con[1]
        else:
            ind = index+" linestart"
        # TODO This should be replaced by self.text.search with regexp=True
        while (self.text.get(ind) in whitespaces) and self.text.compare(ind, '!=', ind + ' lineend'):
            ind = self.text.index(ind+"+1c")
        return ind

    def move_linestart_event(self, event):
        return self.pos_linestart(False)

    def sel_linestart_event(self, event):
        return self.pos_linestart(True)

    def pos_linestart(self, sel):
        linestart = self.find_content_linestart("insert")
        if self.text.compare(linestart, "==", "insert"):
            index = "insert linestart"
        else:
            index = linestart

        self.editwin._move_cursor(index, sel)
        self.updPos()

        return "break"
    
    def del_to_linestart_event(self, event):
        self.text.delete(self.find_content_linestart("insert"), "insert")
        self.updPos()

    def move_lineend_event(self, event):
        return self.pos_lineend(False)

    def sel_lineend_event(self, event):
        return self.pos_lineend(True)

    def pos_lineend(self, sel):
        self.editwin._move_cursor("insert lineend", sel)
        self.updPos()
        return "break"

    def move_docstart_event(self, event):
        return self.pos_docstart(False)

    def sel_docstart_event(self, event):
        return self.pos_docstart(True)

    def pos_docstart(self, sel):
        self.editwin._move_cursor("1.0", sel)
        self.updPos()
        return "break"

    def move_docend_event(self, event):
        return self.pos_docend(False)

    def sel_docend_event(self, event):
        return self.pos_docend(True)

    def pos_docend(self, sel):
        self.editwin._move_cursor("end", sel)
        self.updPos()
        return "break"

    def middle_clicked_event(self, event):
        """Put the selection at the end of the text"""
        try:
            import Tkinter
        except ImportError:
            import tkinter as Tkinter
        try:
            t = self.text.selection_get()
        except Tkinter.TclError:
            t = ''
        self.text.insert('end', t)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.mark_set("insert", "end")
        self.text.see("insert")
        self.updPos()
        return "break"

    @staticmethod
    def middle_released_event(event):
        """Disable the default behaviour"""
        return "break"

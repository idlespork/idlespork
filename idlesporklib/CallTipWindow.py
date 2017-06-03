"""A CallTip window class for Tkinter/IDLE.

After ToolTip.py, which uses ideas gleaned from PySol
Used by the CallTips IDLE extension.
"""
from Tkinter import Toplevel, Label, LEFT, SOLID, TclError, Frame, BOTH

HIDE_VIRTUAL_EVENT_NAME = "<<calltipwindow-hide>>"
HIDE_SEQUENCES = ("<Key-Escape>", "<FocusOut>")
CHECKHIDE_VIRTUAL_EVENT_NAME = "<<calltipwindow-checkhide>>"
CHECKHIDE_SEQUENCES = ("<KeyRelease>", "<ButtonRelease>")
CHECKHIDE_TIME = 100  # miliseconds

MARK_RIGHT = "calltipwindowregion_right"


class CallTip(object):
    # Responsibility for ensuring single CallTip is CallTip's
    instance = None

    def __init__(self, widget, hideOnCursorBack=True):
        self.widget = widget
        self.tipwindow = self.label = None
        self.parenline = self.parencol = None
        self.lastline = None
        self.hideid = self.checkhideid = None
        self.checkhide_after_id = None

        # Flag to close window when cursor moves back
        self.hideOnCursorBack = hideOnCursorBack

    def position_window(self):
        """Check if needs to reposition the window, and if so - do it."""
        curline = int(self.widget.index("insert").split('.')[0])
        if curline == self.lastline:
            return
        self.lastline = curline
        self.widget.see("insert")
        if curline == self.parenline:
            box = self.widget.bbox("%d.%d" % (self.parenline,
                                              self.parencol))
        else:
            box = self.widget.bbox("%d.0" % curline)
        if not box:
            box = list(self.widget.bbox("insert"))
            # align to left of window
            box[0] = 0
            box[2] = 0
        x = box[0] + self.widget.winfo_rootx() + 2
        y = box[1] + box[3] + self.widget.winfo_rooty()
        self.tipwindow.wm_geometry("+%d+%d" % (x, y))

    def showtip(self, text, parenleft, parenright, *moretext):
        """
        Show the calltip, bind events which will close it and reposition it.

        If moretext is given, additional labels are shown.
        """
        if CallTip.instance is not None:
            CallTip.instance.hidetip()
            CallTip.instance = None

        self.text = text
        if self.tipwindow or not self.text:
            return

        self.widget.mark_set(MARK_RIGHT, parenright)
        self.parenline, self.parencol = map(
            int, self.widget.index(parenleft).split("."))

        self.tipwindow = tw = Toplevel(self.widget)
        self.position_window()
        # remove border on calltip window
        tw.wm_overrideredirect(1)
        # Need encompassing frame so extra labels are aligned to the left.
        frame = Frame(tw)
        frame.pack()
        try:
            # This command is only needed and available on Tk >= 8.4.0 for OSX
            # Without it, call tips intrude on the typing process by grabbing
            # the focus.
            tw.tk.call("::tk::unsupported::MacWindowStyle", "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        self.label = Label(frame, text=self.text, justify=LEFT,
                           background="#ffffe0", relief=SOLID, borderwidth=1,
                           font=self.widget['font'])
        self.label.pack(anchor='w', side=LEFT, fill=BOTH)

        # It's nice to have the option for more text.
        for text in moretext:
            label = Label(frame, text=text, justify=LEFT,
                               background="#ffffe0", relief=SOLID, borderwidth=1,
                               font=self.widget['font'])
            label.pack(anchor='w', side=LEFT, fill=BOTH)

        tw.lift()  # work around bug in Tk 8.5.18+ (issue #24570)

        self.checkhideid = self.widget.bind(CHECKHIDE_VIRTUAL_EVENT_NAME,
                                            self.checkhide_event)
        for seq in CHECKHIDE_SEQUENCES:
            self.widget.event_add(CHECKHIDE_VIRTUAL_EVENT_NAME, seq)
        self.widget.after(CHECKHIDE_TIME, self.checkhide_event)
        self.hideid = self.widget.bind(HIDE_VIRTUAL_EVENT_NAME,
                                       self.hide_event)
        for seq in HIDE_SEQUENCES:
            self.widget.event_add(HIDE_VIRTUAL_EVENT_NAME, seq)

        CallTip.instance = self

    def safecompare(self):
        # For unknown reasons sometimes this compare fails
        try:
            return self.widget.compare("insert", ">", MARK_RIGHT)
        except:
            return 1

    def checkhide_event(self, event=None):
        if not self.tipwindow:
            # If the event was triggered by the same event that unbinded
            # this function, the function will be called nevertheless,
            # so do nothing in this case.
            return
        curline, curcol = map(int, self.widget.index("insert").split('.'))
        if (curline != self.parenline or
                (self.hideOnCursorBack and ((curline == self.parenline and curcol <= self.parencol) or
                                                self.safecompare()))):
            self.hidetip()

        else:
            self.position_window()
            if self.checkhide_after_id is not None:
                self.widget.after_cancel(self.checkhide_after_id)
            self.checkhide_after_id = \
                self.widget.after(CHECKHIDE_TIME, self.checkhide_event)

    def hide_event(self, event):
        if not self.tipwindow:
            # See the explanation in checkhide_event.
            return
        self.hidetip()

    def hidetip(self):
        if not self.tipwindow:
            return

        for seq in CHECKHIDE_SEQUENCES:
            self.widget.event_delete(CHECKHIDE_VIRTUAL_EVENT_NAME, seq)
        self.widget.unbind(CHECKHIDE_VIRTUAL_EVENT_NAME, self.checkhideid)
        self.checkhideid = None
        for seq in HIDE_SEQUENCES:
            self.widget.event_delete(HIDE_VIRTUAL_EVENT_NAME, seq)
        self.widget.unbind(HIDE_VIRTUAL_EVENT_NAME, self.hideid)
        self.hideid = None

        self.label.destroy()
        self.label = None
        self.tipwindow.destroy()
        self.tipwindow = None

        self.widget.mark_unset(MARK_RIGHT)
        self.parenline = self.parencol = self.lastline = None
        CallTip.instance = None

    def is_active(self):
        return bool(self.tipwindow)


def _calltip_window(parent):  # htest #
    from Tkinter import Toplevel, Text, LEFT, BOTH

    top = Toplevel(parent)
    top.title("Test calltips")
    top.geometry("200x100+%d+%d" % (parent.winfo_rootx() + 200,
                                    parent.winfo_rooty() + 150))
    text = Text(top)
    text.pack(side=LEFT, fill=BOTH, expand=1)
    text.insert("insert", "string.split")
    top.update()
    calltip = CallTip(text)

    def calltip_show(event):
        calltip.showtip("(s=Hello world)", "insert", "end")

    def calltip_hide(event):
        calltip.hidetip()

    text.event_add("<<calltip-show>>", "(")
    text.event_add("<<calltip-hide>>", ")")
    text.bind("<<calltip-show>>", calltip_show)
    text.bind("<<calltip-hide>>", calltip_hide)
    text.focus_set()


if __name__ == '__main__':
    from idlesporklib.idle_test.htest import run

    run(_calltip_window)

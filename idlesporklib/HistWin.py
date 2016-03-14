from configHandler import idleConf
from Tkinter import Frame, Listbox, Scrollbar
from Tkinter import TOP, X, Y, END, RIGHT, EXTENDED

class HistWin(object):
    def __init__(self, top):
        currentTheme = idleConf.CurrentTheme()
        self.history_frame = Frame(top, height=1)
        self.top = top
        fg = idleConf.GetHighlight(currentTheme, 'normal',fgBg='fg')
        bg = idleConf.GetHighlight(currentTheme, 'normal',fgBg='bg')
        self.lst = Listbox(self.history_frame,
            foreground=fg, background=bg,
            height=5, selectmode=EXTENDED,
            exportselection=False)
        self.scroll = Scrollbar(self.history_frame,
            command = self.lst.yview)

        self.lst['yscrollcommand'] = self.scroll.set
        self.lst.bind('<ButtonRelease-1>', self.click)

        #self.search_box_text = Variable()
        #self.search_box_text.trace('w', self.search_text_changed)
        #self.search_box = Entry(self.history_frame,
        #    foreground=fg, background=bg,
        #    textvariable=self.search_box_text)
        self.history_frame.pack(side=TOP, fill=X)
        self.is_shown = False

    def attach_history(self, textwidget, hist):
        self.hist = hist
        self.hist.histwin = self
        for h in hist.history:
            self.store(h)
        self.lst.see('end')

        self.textwidget = textwidget
        self.textwidget.bind('<<history-window-toggle>>', self.history_window_toggle_event)

    def click(self, evt):
        selection = sorted(map(int, self.lst.curselection()))
        commands = [self.hist.history[x] for x in selection]
        commands = '\n'.join(commands)
        self.textwidget.delete("iomark", "end-1c")
        self.textwidget.insert("iomark", commands)

    def goto(self, pointer):
        self.lst.select_clear(0, END)
        self.lst.select_set(pointer)
        self.lst.see(0)
        self.lst.see(pointer)

    def hide(self):
        self.lst.pack_forget()
        self.scroll.pack_forget()
        self.history_frame['height'] = 1
        self.is_shown = False

    def show(self):
        self.scroll.pack(side=RIGHT, fill=Y)
        self.lst.pack(side=TOP, fill=X)
        self.is_shown = True

    def toggle(self):
        if self.is_shown:
            self.hide()
        else:
            self.show()

    def store(self, source):
        self.lst.insert(END, source[:60]
            .replace('\n', ' ').replace('\t', ' '))

    def remove(self, idx):
        self.lst.delete(idx)

    def history_window_toggle_event(self, evt):
        self.toggle()
        return "break"

    #def show_search_box(self):
    #    self.search_box.pack(side=BOTTOM, fill=X)
    #    self.search_box.focus()

    #def search_text_changed(self, *args):
    #    txt = self.search_box.get()


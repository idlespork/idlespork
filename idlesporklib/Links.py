import re
try:
    from Tkinter import SEL, INSERT
except ImportError:
    from tkinter import SEL, INSERT

PREFIX = '{{{IDLESPORK_LINK:'
SUFFIX = '}}}'

FILE_PATTERN = r"File \"([^\"]*)\", line ([0-9]*)"

class Link(object):
    def __str__(self):
        return self.txt
    def create(self):
        return create_link(self)

class FileLink(Link):
    def __init__(self, gui, txt, filename, lineno):
        self.txt = txt
        self.filename = filename
        self.lineno = lineno
        self.gui = gui

    def run(self, evt):
        win = self.gui.flist.open(self.filename)
        win.mark_line(self.lineno)

class GotoMarkLink(Link):
    def __init__(self, gui, txt, mark, line = 1):
        self.gui = gui
        self.txt = txt
        self.mark = mark
        self.line = line

    def run(self, evt):
        self.gui.text.after(50, self.after_sometime)

    def after_sometime(self):
        self.gui.text.selection_clear()

        # If squeezing code is allowed, we have to check if the mark is in a squeezer.
        sq = self.gui.extensions["Squeezer"]
        if sq is not None and sq._SQUEEZE_CODE:
            # Squeezed code is always one line under the mark.
            button = sq.find_button(self.gui.text.index(self.mark + ' + 1 line linestart'))
            if button is not None:
                button.expand(None)

        if self.line != 1:
            m = self.mark + " + %d lines linestart" % (self.line - 1)
        else:
            m = self.mark
        self.gui.text.tag_add(SEL, m, "%s lineend" % m)
        self.gui.text.mark_set(INSERT, m)
        self.gui.text.see(INSERT)

class ExecCodeLink(Link):
    def __init__(self, gui, txt, code):
        self.gui = gui
        if isinstance(code, (str, unicode)): code = [code]
        self.code = code
        self.txt = txt

    def run(self, evt):
        shell = self.gui
        if shell.executing:
            return
        for c in self.code:
            shell.text.delete('iomark', 'end-1c')
            shell.text.insert('iomark', c)
            shell.color.recolorize()
            shell.runit(True)
            shell.text.mark_set(INSERT, 'end-1c')
            # shell.beginexecuting()
            # cmd = Commands.create_code_command(shell.interp, c, False, False)
            # shell.interp.rpcclt.remotequeue( \
            #    "exec", "run_cmd", (cmd,), {})
            # shell.endexecuting()


links = []

def create_link_local(link):
    ID = len(links)
    links.append(link)
    return '%s%d%s' % (PREFIX, ID, SUFFIX)

def create_link(link):
    import sporktools
    return sporktools._World.interp.create_link(link)

def replace_addresses(gui, txt):
    """Replaces file addresses in txt by links"""
    ret = []
    m = re.search(FILE_PATTERN, txt)
    while m:
        ret.append(txt[:m.start()])
        filename, lineno = m.group(1), int(m.group(2))
        # We don't want to replace existing links
        if not filename.startswith(PREFIX) or not filename.endswith(SUFFIX):
            if filename.startswith("<pyshell#") and filename.endswith('>'):
                link = create_link_local(GotoMarkLink(gui, filename, filename[1:-1], lineno))
            else:
                link = create_link_local(FileLink(gui, filename, filename, lineno))
            ret.append('File "%s", line %d' % (link, lineno))
        else:
            ret.append(m.group(0))
        txt = txt[m.end():]
        m = re.search(FILE_PATTERN, txt)
    ret.append(txt)
    return ''.join(ret)


def replace_links(txt):
    # Replace links text with the real addresses.
    # This is utilised by Squeezer when asked to open "less" or copy squeezed text,
    # since we don't want to see "{{{IDLESPORK_LINK:0}}}" in our text.
    # Furthermore, if txt is the output of "??", w
    match = re.match(r"^File \"([^\"]*)\", line ([0-9]*):\n", txt)
    if match:
        txt = txt[match.end():]

    ret = []
    m = re.search('\"{}([0-9]*){}\"'.format(PREFIX, SUFFIX), txt)
    while m:
        ret.append(txt[:m.start()])
        ind = int(m.group(1))
        if 0 <= ind < len(links):
            ret.append('"{}"'.format(links[ind].txt))
        else:
            ret.append(m.group(0))
        txt = txt[m.end():]
        m = re.search('\"{}([0-9]*)\"'.format(PREFIX, SUFFIX), txt)
    ret.append(txt)
    return ''.join(ret)


def parse(text, begin, end):
    begin = text.index(begin)
    end = text.index(end)
    s1 = text.search(PREFIX, begin, end)
    while s1 != '':
        s2 = text.search(SUFFIX, s1)
        if s2 == '': return

        linkID = text.get(s1 + "+%dc" % len(PREFIX), s2)
        tag = 'IDLESPORK_LINK_%s' % linkID
        tags = text.tag_names(s1) + ('LINK', tag)

        try:
            lnk = links[int(linkID)]
            text.delete(s1, s2 + "+%dc" % len(SUFFIX))
            text.insert(s1, str(lnk), tags)
            news1 = s1 + ' + %d c' % len(str(lnk))
            text.tag_bind(tag, '<Button-1>', lnk.run)
        except:
            news1 = s1 + ' + 1c'

        s1 = text.search(PREFIX, news1, end, regexp=True)

def links_config(shell):
    text = shell.text
    default_cursor = text['cursor']
    def enter(evt):
        text['cursor'] = 'hand1'
    def leave(evt):
        text['cursor'] = default_cursor
    #text.tag_config('LINK', foreground='#77bbff')
    text.tag_config('LINK', underline=1)
    text.tag_bind('LINK', '<Enter>', enter)
    text.tag_bind('LINK', '<Leave>', leave)



def select_previous_link(shell):
    # find selected link
    j = None
    for i in xrange(len(links)):
        tagname = 'IDLESPORK_LINK_%d' % i
        m = tagname + '.last'
        if len(shell.text.tag_ranges(tagname)) != 0:
            if shell.text.compare(INSERT, '>', m):
                j = i
    if j is None: return "break"

    shell.text.selection_clear()
    shell.text.tag_add(SEL, 'IDLESPORK_LINK_%d.first' % j, \
        'IDLESPORK_LINK_%d.last' % j)
    shell.text.mark_set(INSERT, 'sel.first')
    shell.text.see(INSERT)
    return "break"

def select_next_link(shell):
    # find selected link
    j = None
    for i in xrange(len(links)-1, -1, -1):
        tagname = 'IDLESPORK_LINK_%d' % i
        m = tagname + '.first'
        if len(shell.text.tag_ranges(tagname)) != 0:
            if shell.text.compare(INSERT, '<', m):
                j = i
    if j is None: return "break"

    shell.text.selection_clear()
    shell.text.tag_add(SEL, 'IDLESPORK_LINK_%d.first' % j, \
        'IDLESPORK_LINK_%d.last' % j)
    shell.text.mark_set(INSERT, 'sel.first')
    shell.text.see(INSERT)
    return "break"

def enter_on_link(shell):
    for i in xrange(len(links)):
        tagname = 'IDLESPORK_LINK_%d' % i
        mf = tagname + '.first'
        ml = tagname + '.last'
        if len(shell.text.tag_ranges(tagname)) != 0:
            if shell.text.compare(INSERT, '>=', mf) and \
               shell.text.compare(INSERT, '<=', ml):
                shell.text.selection_clear()
                links[i].run(None)
                return True
    return False

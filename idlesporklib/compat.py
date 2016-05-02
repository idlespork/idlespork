import sys

if sys.version_info[0] >= 3:
    import tkinter
    import tkinter.font
    import tkinter.messagebox
    import tkinter.simpledialog
    import tkinter.colorchooser
    import tkinter.filedialog
    import configparser
    import html.parser
    import builtins
    sys.modules['Tkinter'] = tkinter
    sys.modules['tkFont'] = tkinter.font
    sys.modules['tkMessageBox'] = tkinter.messagebox
    sys.modules['tkSimpleDialog'] = tkinter.simpledialog
    sys.modules['tkColorChooser'] = tkinter.colorchooser
    sys.modules['tkFileDialog'] = tkinter.filedialog
    sys.modules['ConfigParser'] = configparser
    sys.modules['HTMLParser'] = html.parser
    sys.modules['__builtin__'] = builtins

    # Types
    long = int
    unicode = str

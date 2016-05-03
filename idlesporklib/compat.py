import sys

if sys.version_info[0] >= 3:
    import tkinter
    sys.modules['Tkinter'] = tkinter
    import tkinter.font
    sys.modules['tkFont'] = tkinter.font
    import tkinter.messagebox
    sys.modules['tkMessageBox'] = tkinter.messagebox
    import tkinter.simpledialog
    sys.modules['tkSimpleDialog'] = tkinter.simpledialog
    import tkinter.colorchooser
    sys.modules['tkColorChooser'] = tkinter.colorchooser
    import tkinter.filedialog
    sys.modules['tkFileDialog'] = tkinter.filedialog
    import tkinter.simpledialog
    sys.modules['SimpleDialog'] = tkinter.simpledialog
    import configparser
    sys.modules['ConfigParser'] = configparser
    import html.parser
    sys.modules['HTMLParser'] = html.parser
    import builtins
    sys.modules['__builtin__'] = builtins
    import socketserver
    sys.modules['SocketServer'] = socketserver
    import pickle
    sys.modules['cPickle'] = pickle
    import queue
    sys.modules['Queue'] = queue
    import copyreg
    sys.modules['copy_reg'] = copyreg
    import _thread
    sys.modules['thread'] = _thread
    import reprlib
    sys.modules['repr'] = reprlib


    # Types
    long = int
    unicode = str
    xrange = range

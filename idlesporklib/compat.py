import sys

if sys.version_info[0] >= 3:
    import tkinter
    import tkinter.font
    import tkinter.messagebox
    import configparser
    sys.modules['Tkinter'] = tkinter
    sys.modules['tkFont'] = tkinter.font
    sys.modules['tkMessageBox'] = tkinter.messagebox
    sys.modules['ConfigParser'] = configparser

import sys, os.path

__path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, __path)
from idlesporklib import Commands, Links
sys.path.remove(__path)
del __path

_World = None

def _initialize(rpc, world):
    global _World, _rpc
    _World = world
    _rpc = rpc

def run(line):
    cmd = Commands.parse(_World.interp, line)
    if cmd.GUI_COMMAND:
        _World.interp.runcmd(cmd)
    else:
        cmd.run(_World)

def hist_toggle():
    _World.interp.runcmd(Commands.HistoryToggleCommand('toggle'))

def hist_show():
    _World.interp.runcmd(Commands.HistoryToggleCommand('show'))

def hist_hide():
    _World.interp.runcmd(Commands.HistoryToggleCommand('hide'))

def call_main_thread(func):
    def tmp(*args, **kw):
        return _World.MainThreadCaller.call_main_thread(func, *args, **kw)
    tmp.func_name = func.__name__
    tmp.func_doc = func.__doc__
    return tmp

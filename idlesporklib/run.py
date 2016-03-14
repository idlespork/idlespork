import sys
import os
import linecache
import PatchLineCache # This patches linecache!!
PatchLineCache.patch_linecache()
import time
import socket
import traceback
import thread
import threading
import Queue
import cStringIO
try:
    import ctypes
except ImportError:
    ctypes = None

from idlesporklib import CallTips
from idlesporklib import AutoComplete

from idlesporklib import RemoteDebugger
from idlesporklib import RemoteObjectBrowser
from idlesporklib import StackViewer
from idlesporklib import rpc
from idlesporklib import PyShell
from idlesporklib import IOBinding
from idlesporklib import Links
from idlesporklib import sporktools
from idlesporklib import Suggest

import __main__

LOCALHOST = '127.0.0.1'

import warnings

def idle_showwarning_subproc(
        message, category, filename, lineno, file=None, line=None):
    """Show Idle-format warning after replacing warnings.showwarning.

    The only difference is the formatter called.
    """
    if file is None:
        file = sys.stderr
    try:
        file.write(PyShell.idle_formatwarning(
                message, category, filename, lineno, line))
    except IOError:
        pass # the file (probably stderr) is invalid - this warning gets lost.

_warnings_showwarning = None

def capture_warnings(capture):
    "Replace warning.showwarning with idle_showwarning_subproc, or reverse."

    global _warnings_showwarning
    if capture:
        if _warnings_showwarning is None:
            _warnings_showwarning = warnings.showwarning
            warnings.showwarning = idle_showwarning_subproc
    else:
        if _warnings_showwarning is not None:
            warnings.showwarning = _warnings_showwarning
            _warnings_showwarning = None

capture_warnings(True)

# Thread shared globals: Establish a queue between a subthread (which handles
# the socket) and the main thread (which runs user code), plus global
# completion, exit and interruptable (the main thread) flags:

exit_now = False
quitting = False
interruptable = False

class JobsException(Exception):
    pass

class Jobs(object):
    __all__ = ['alljobs','__repr__','getoutput']
    def __init__(self):
        self.__jobs = {}
        self.__rjobs = {}
        self.__death_hook = {}

    def get_ind(self):
        K = self.__jobs.keys()
        if len(K) == 0: return 0
        return min(set(range(max(K)+2)) - set(K))

    def subscribe(self,jthread,savednum=None):
        if savednum is None:
            jnum = self.get_ind()
        else:
            if not isinstance(self.__jobs[savednum],SavedSeat):
                raise JobsException('Trying to override non SavedSeat slot %d'%savednum)
            if self.__jobs[savednum].isAlive():
                jnum = savednum
            else:
                return None
        self.__jobs[jnum] = jthread
        if not self.__death_hook.has_key(jnum):
            self.__death_hook[jnum] = []
        return jnum

    def __repr__(self):
        descs = [repr(self.__jobs[j]) \
            for j in sorted(self.__jobs.keys()) \
            if self.__jobs[j].isAlive()]
        if len(descs) == 0:
            return 'No running jobs. Run "jobs -a" to see all jobs.'
        return '\n'.join(descs)

    def alljobs(self):
        x = ''
        for j in self.__jobs.values():
            x += repr(j) + '\n'
        return x

    def I_began(self, jthread):
        self.__rjobs[jthread.ident] = jthread

    def I_died(self,num, myident):
        del self.__rjobs[myident]
        remote_stdout.write('**** [%d] - Done ****\n' % num)
        for (f,args,kwargs) in self.__death_hook[num]:
            f(*args,**kwargs)

    def dismiss(self,num):
        del self.__jobs[num]

    def current_by_thread(self):
        return self.__rjobs[thread.get_ident()]

    def getoutput(self,jnum):
        return self.__jobs[jnum].getoutput()

    def __getitem__(self, idx):
        return self.__jobs[idx]

    def toggleoutput(self, idx):
        self.__jobs[idx].trueoutput = not self.__jobs[idx].trueoutput

    def subscribe_to_death(self, num, f,*args,**kwargs):
        try:
            if self.__jobs[num].isAlive():
                self.__death_hook[num].append((f,args,kwargs))
            else:
                print >>sys.stderr, 'Cannot queue after nonliving job.'
        except KeyError:
            print >>sys.stderr, 'Job %d does not exist'%num

    def save_id(self,descr):
        ind = self.get_ind()
        self.__jobs[ind] = SavedSeat(descr,ind)
        self.__death_hook[ind] = []
        return ind

    def has_job(self,jnum):
        return self.__jobs.has_key(jnum)

    def is_alive(self,jnum):
        return self.__jobs[jnum].isAlive()


class MainThreadCaller(object):
    def __init__(self):
        self.callEvent = threading.Event()
        self.returnEvent = threading.Event()
        self.callLock = threading.Lock()
        self.args = None
        self.kw = None
        self.func = None
        self.ret = None

    def call_main_thread(self, func, *args, **kw):
        """
Asks the main thread to call a given function.
Waits for the main thread to complete the computation and then returns.
"""
        with self.callLock:
            self.args = args
            self.kw = kw
            self.func = func
            self.callEvent.set()
            self.returnEvent.wait()
            self.returnEvent.clear()
            if self.exc is not None:
                raise self.exc
            return self.ret

    def wait_for_call(self, timeout):
        """
This function should be called by the main thread.
It waits for a function call (by MainThreadCaller.call_main_thread) and runs
the function.
"""
        if not self.callEvent.wait(timeout):
            return

        self.callEvent.clear()
        self.exc = None

        try:
            self.ret = self.func(*self.args, **self.kw)
        except Exception, e:
            self.exc = e
        finally:
            self.returnEvent.set()


MainThreadCaller = MainThreadCaller() # Singleton

class SavedSeat(object):
    def __init__(self,descr,ind):
        self.basedescr = ('[%d] '%ind)+descr
        self.descr = self.basedescr
        self.isalive = True
        self.trueoutput = False

    def isAlive(self):
        return self.isalive

    def kill(self):
        self.isalive = False
        self.descr = self.basedescr + ' (killed)'

    def revive(self):
        self.isalive = True
        self.descr = self.basedescr

    def getoutput(self):
        return ''

    def __repr__(self):
        return self.descr

class OutputManager(object):
    def __init__(self, real_stdout, jobs):
        self.jobs = jobs
        self.real_stdout = real_stdout

    def write(self, txt):
        try:
            self.jobs.current_by_thread().write(txt)
        except KeyError:
            self.real_stdout.write(txt)

    def flush(self):
        self.jobs.current_by_thread().flush()


class World(object):
    def __init__(self):
        global jobs, __main__
        self.main = __main__
        self.remote_stdout = None
        self.remote_stderr = None
        self.jobs = None
        self.interp = None
        self.current_thread = None
        self.executive = None

World = World()
World.jobs = jobs = Jobs()
World.MainThreadCaller = MainThreadCaller

sporktools._initialize(rpc, World)
sys.modules['sporktools'] = sporktools

# Patch signal module
import signal
signal.signal = sporktools.call_main_thread(signal.signal)

def main(del_exitfunc=False):
    """Start the Python execution server in a subprocess

    In the Python subprocess, RPCServer is instantiated with handlerclass
    MyHandler, which inherits register/unregister methods from RPCHandler via
    the mix-in class SocketIO.

    When the RPCServer 'server' is instantiated, the TCPServer initialization
    creates an instance of run.MyHandler and calls its handle() method.
    handle() instantiates a run.Executive object, passing it a reference to the
    MyHandler object.  That reference is saved as attribute rpchandler of the
    Executive instance.  The Executive methods have access to the reference and
    can pass it on to entities that they command
    (e.g. RemoteDebugger.Debugger.start_debugger()).  The latter, in turn, can
    call MyHandler(SocketIO) register/unregister methods via the reference to
    register and unregister themselves.

    """
    global no_exitfunc
    no_exitfunc = del_exitfunc

    global jobs
    global remote_stdout
    global original_displayhook
    World.current_thread=RunThread()
    World.current_thread.make_current()
    World.remote_stdout = remote_stdout = sys.stdout

    original_displayhook = sys.displayhook
    sys.displayhook = displayhook

    #time.sleep(15) # test subprocess not responding
    try:
        assert(len(sys.argv) > 1)
        port = int(sys.argv[-1])
    except:
        print>>sys.stderr, "IDLE Subprocess: no IP port passed in sys.argv."
        return

    capture_warnings(True)
    sys.argv[:] = [""]
    sockthread = threading.Thread(target=manage_socket,
                                  name='SockThread',
                                  args=((LOCALHOST, port),))
    sockthread.setDaemon(True)
    sockthread.start()

    World.current_thread.start()

    __main__.Jobs = jobs

    while not quitting:
        try:
            while not quitting: # Replace by something
                MainThreadCaller.wait_for_call(1)
        except KeyboardInterrupt:
            if quitting:
                exit()
            World.current_thread.keyboard_interrupt()

class RunThread(threading.Thread):
    def __init__(self, rfunc=None, rargs=(), rkwargs={}):
        global jobs
        self.jobs = jobs
        threading.Thread.__init__(self)
        self.daemon = True
        self.response_queue = Queue.Queue(0)
        self.request_queue = Queue.Queue(0)
        self.__keepalive=True
        self.ctrlC = False
        self.description = 'No description'
        self.output = cStringIO.StringIO()
        self.trueoutput = False
        self.ret = None
        self.start_time = self.end_time = None
        self.rfunc = rfunc
        self.rargs = rargs
        self.rkwargs = rkwargs

    def subscribe_me(self,savednum=None):
        self.num = self.jobs.subscribe(self,savednum)
        return self.num

    def make_current(self):
        rpc.request_queue = self.request_queue
        rpc.response_queue = self.response_queue

    def endlife(self):
        self.__keepalive=False

    def keyboard_interrupt(self):
        ctypes.pythonapi.PyThreadState_SetAsyncExc.argtypes=[ctypes.c_long, ctypes.py_object]
        ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, \
            ctypes.py_object(KeyboardInterrupt))

    def kill(self):
        self.keyboard_interrupt()

    def displayhook(self, val):
        if self == World.current_thread:
            original_displayhook(val)
        else:
            self.ret = val
            if val is not None:
                print val

    def run(self):
        global exit_now
        global quitting
        import sys
        import traceback

        if hasattr(self,'num') and self.num is None:
            return

        if not hasattr(self,'ident'):
            self.ident = thread.get_ident()
        self.jobs.I_began(self)

        if self.rfunc is not None:
            self.rfunc(*self.rargs, **self.rkwargs)
            self.__keepalive = False

        while self.__keepalive:
            try:
                if exit_now:
                    try:
                        exit()
                    except KeyboardInterrupt:
                        # exiting but got an extra KBI? Try again!
                        continue
                try:
                    seq, request = self.request_queue.get(block=True, timeout=0.05)
                except Queue.Empty:
                    continue
                method, args, kwargs = request
                ret = method(*args, **kwargs)
                self.response_queue.put((seq, ret))
            except KeyboardInterrupt:
                if quitting:
                    exit_now = True
                continue
            except SystemExit:
                capture_warnings(False)
                raise
            except:
                type, value, tb = sys.exc_info()
                try:
                    print_exception()
                    self.response_queue.put((seq, None))
                except:
                    # Link didn't work, print same exception to __stderr__
                    traceback.print_exception(type, value, tb, file=sys.__stderr__)
                    exit()
                else:
                    continue

        self.end_time = time.time()
        self.jobs.I_died(self.num,self.ident)

    def write(self, output):
        if (self != World.current_thread) and not self.trueoutput:
            self.output.write(output)
        else:
            sys.stdout.real_stdout.write(output)

    def flush(self):
        sys.stdout.real_stdout.flush()

    def getoutput(self):
        OP = self.output.getvalue()
        if len(OP) > 0 and OP[-1] == '\r':
            OP = OP[:-1]
        OP = OP.split('\n')
        OP = [a[a.rfind('\r')+1:] for a in OP]
        OP = '\n'.join(OP)
        return OP


    def __repr__(self):
        tm = ''
        status = 'Running'
        if not self.isAlive():
            status = 'Done'

        desc = self.description.splitlines()[0][:60]
        if desc != self.description:
            desc += "..."

        if self.start_time:
            et = time.time()
            if self.end_time:
                et = self.end_time
            run_time = et - self.start_time
            tm = '<%02d:%05.2f>' % (int(run_time / 60), run_time % 60)

        return '%-6s %-8s %-12s %s' % ('[%d]' % self.num, status, tm, desc)

def manage_socket(address):
    for i in range(3):
        time.sleep(i)
        try:
            server = MyRPCServer(address, MyHandler)
            break
        except socket.error as err:
            print>>sys.__stderr__,"IDLE Subprocess: socket error: "\
                                        + err.args[1] + ", retrying...."
    else:
        print>>sys.__stderr__, "IDLE Subprocess: Connection to "\
                               "IDLE GUI failed, exiting."
        show_socket_error(err, address)
        global exit_now
        exit_now = True
        return
    server.handle_request() # A single request only

def show_socket_error(err, address):
    import Tkinter
    import tkMessageBox
    root = Tkinter.Tk()
    root.withdraw()
    if err.args[0] == 61: # connection refused
        msg = "IDLE's subprocess can't connect to %s:%d.  This may be due "\
              "to your personal firewall configuration.  It is safe to "\
              "allow this internal connection because no data is visible on "\
              "external ports." % address
        tkMessageBox.showerror("IDLE Subprocess Error", msg, parent=root)
    else:
        tkMessageBox.showerror("IDLE Subprocess Error",
                               "Socket Error: %s" % err.args[1], parent=root)
    root.destroy()

def print_exception(source = None, filename = None):
    import linecache
    linecache.checkcache()
    flush_stdout()
    efile = sys.stderr
    typ, val, tb = excinfo = sys.exc_info()
    sys.last_type, sys.last_value, sys.last_traceback = excinfo
    tbe = traceback.extract_tb(tb)
    print>>efile, '\nTraceback (most recent call last):'
    exclude = ("run.py", "rpc.py", "threading.py", "Queue.py",
               "RemoteDebugger.py", "bdb.py", "Commands.py")
    cleanup_traceback(tbe, exclude)
    add_exception_link(tbe)
    traceback.print_list(tbe, file=efile)
    lines = traceback.format_exception_only(typ, val)
    for line in lines:
        print>>efile, line,
    if source is not None and filename is not None:
       Suggest.exception_suggest(typ, val, tb, source, filename)

def add_exception_link(tb):
    for i in xrange(len(tb)):
        filename, lineno, meth, line = tb[i]
        if filename.startswith("<pyshell#") and filename.endswith('>'):
            link = Links.create_link( \
                Links.GotoMarkLink(None, filename, \
                    filename[1:-1], lineno))
            tb[i] = (link, lineno, meth, line)
        elif os.path.exists(filename):
            txt, abspath = filename, os.path.abspath(filename)
            link = Links.FileLink(None, txt, \
                    abspath, lineno).create()
            tb[i] = (link, lineno, meth, line)

def cleanup_traceback(tb, exclude):
    "Remove excluded traces from beginning/end of tb; get cached lines"
    orig_tb = tb[:]
    while tb:
        for rpcfile in exclude:
            if tb[0][0].count(rpcfile):
                break    # found an exclude, break for: and delete tb[0]
        else:
            break        # no excludes, have left RPC code, break while:
        del tb[0]
    while tb:
        for rpcfile in exclude:
            if tb[-1][0].count(rpcfile):
                break
        else:
            break
        del tb[-1]
    if len(tb) == 0:
        # exception was in IDLE internals, don't prune!
        tb[:] = orig_tb[:]
        print>>sys.stderr, "** IDLE Internal Exception: "
    rpchandler = rpc.objecttable['exec'].rpchandler
    for i in range(len(tb)):
        fn, ln, nm, line = tb[i]
        if nm == '?':
            nm = "-toplevel-"
        if fn.startswith("<pyshell#") and IOBinding.encoding != 'utf-8':
            ln -= 1  # correction for coding cookie
        if not line and fn.startswith("<pyshell#"):
            line = rpchandler.remotecall('linecache', 'getline',
                                              (fn, ln), {})
        tb[i] = fn, ln, nm, line

def flush_stdout():
    try:
        if sys.stdout.softspace:
            sys.stdout.softspace = 0
            sys.stdout.write("\n")
    except (AttributeError, EOFError):
        pass

def exit():
    """Exit subprocess, possibly after first deleting sys.exitfunc

    If config-main.cfg/.def 'General' 'delete-exitfunc' is True, then any
    sys.exitfunc will be removed before exiting.  (VPython support)

    """
    if no_exitfunc:
        try:
            del sys.exitfunc
        except AttributeError:
            pass
    capture_warnings(False)
    sys.exit(0)

class MyRPCServer(rpc.RPCServer):

    def handle_error(self, request, client_address):
        """Override RPCServer method for IDLE

        Interrupt the MainThread and exit server if link is dropped.

        """
        global quitting
        try:
            raise
        except SystemExit:
            raise
        except EOFError:
            global exit_now
            exit_now = True
            thread.interrupt_main()
        except:
            erf = sys.__stderr__
            print>>erf, '\n' + '-'*40
            print>>erf, 'Unhandled server exception!'
            print>>erf, 'Thread: %s' % threading.currentThread().getName()
            print>>erf, 'Client Address: ', client_address
            print>>erf, 'Request: ', repr(request)
            traceback.print_exc(file=erf)
            print>>erf, '\n*** Unrecoverable, server exiting!'
            print>>erf, '-'*40
            quitting = True
            thread.interrupt_main()

class MyHandler(rpc.RPCHandler):

    def handle(self):
        """Override base method"""

        global remote_stdout
        World.executive = executive = Executive(self)
        self.register("exec", executive)
        self.console = self.get_remote_proxy("console")
        sys.stdin = PyShell.PseudoInputFile(self.console, "stdin",
                IOBinding.encoding)
        World.remote_stdout = remote_stdout = \
            PyShell.PseudoOutputFile(self.console,
            "stdout", IOBinding.encoding)
        sys.stdout = OutputManager(remote_stdout, jobs)
        World.remote_stderr = sys.stderr = \
            PyShell.PseudoOutputFile(self.console, "stderr",
            IOBinding.encoding)
        sys.stdcolor = self.get_remote_proxy("stdcolor")

        # Keep a reference to stdin so that it won't try to exit IDLE if
        # sys.stdin gets changed from within IDLE's shell. See issue17838.
        self._keep_stdin = sys.stdin

        World.interp = self.interp = self.get_remote_proxy("interp")

        cwd = World.interp.get_subprocess_cwd()
        if cwd is not None:
            os.chdir(cwd)

        rpc.RPCHandler.getresponse(self, myseq=None, wait=0.05)

    def exithook(self):
        "override SocketIO method - wait for MainThread to shut us down"
        time.sleep(10)

    def EOFhook(self):
        "Override SocketIO method - terminate wait on callback and exit thread"
        global quitting
        quitting = True
        thread.interrupt_main()

    def decode_interrupthook(self):
        "interrupt awakened thread"
        global quitting
        quitting = True
        thread.interrupt_main()


class Executive(object):

    def __init__(self, rpchandler):
        self.rpchandler = rpchandler
        self.locals = __main__.__dict__
        self.calltip = CallTips.CallTips()
        self.autocomplete = AutoComplete.AutoComplete()

    def runcode(self, code, source = None, filename = None):
        global interruptable
        try:
            self.usr_exc_info = None
            interruptable = True
            try:
                exec code in self.locals
            finally:
                interruptable = False
        except SystemExit:
            # Scripts that raise SystemExit should just
            # return to the interactive prompt
            pass
        except:
            self.usr_exc_info = sys.exc_info()
            if quitting:
                exit()
            print_exception(source, filename)
            jit = self.rpchandler.console.getvar("<<toggle-jit-stack-viewer>>")
            if jit:
                self.rpchandler.interp.open_remote_stack_viewer()
        else:
            flush_stdout()

    def runcode_bg(self, code, source, savednum=None):
        global interruptable
        newthread = RunThread(self.runcode, (code,))
        if newthread.subscribe_me(savednum) is not None:
            newthread.description = source + ' '*(len(source)==0)
            newthread.start_time = time.time()
            remote_stdout.write('**** [%d] - Background ****\n' % newthread.num)
            newthread.start()
            if savednum is not None:
                World.jobs.toggleoutput(savednum)

    def runcode_after(self, code, source, jobid):
        if not World.jobs.has_job(jobid):
            print >>sys.stderr, 'Job %d does not exist'%jobid
            return
        if not World.jobs.is_alive(jobid):
            print >>sys.stderr, 'Cannot queue after nonliving job.'
            return
        jnum = World.jobs.save_id('Queued after [%d]'%jobid)
        World.jobs.subscribe_to_death(jobid, self.runcode_bg, code, source, jnum)
        return jnum

    def run_cmd(self, cmd):
        cmd.run(World)

    def update_desc(self,desc):
        """Changes the description of the current thread.
        This function will be called every time the user runs some code"""
        World.current_thread.description = desc
        World.current_thread.start_time = time.time()

    def eval(self, expr):
        """Eval expr in __main__."""
        return eval(expr, self.locals)

    def interrupt_the_server(self):
        if interruptable:
            thread.interrupt_main()

    def start_the_debugger(self, gui_adap_oid):
        return RemoteDebugger.start_debugger(self.rpchandler, gui_adap_oid)

    def stop_the_debugger(self, idb_adap_oid):
        "Unregister the Idb Adapter.  Link objects and Idb then subject to GC"
        self.rpchandler.unregister(idb_adap_oid)

    def get_the_calltip(self, name):
        return self.calltip.fetch_tip(name)

    def get_the_completion_list(self, what, mode):
        return self.autocomplete.fetch_completions(what, mode)

    def get_the_prompt(self):
        try:
            return str(getattr(sys, 'ps1', '>>> '))
        except:
            print >>sys.stderr, "** Exception in str(sys.ps1):"
            print_exception()
            return '>>> '

    def background_callback(self):
        World.current_thread.subscribe_me()
        remote_stdout.write('**** [%d] - Background ****' % World.current_thread.num)
        World.current_thread.endlife()
        World.current_thread = RunThread()
        World.current_thread.make_current()
        World.current_thread.start()

    def update_linecache(self,filename,params):
        linecache.cache[filename] = params[0], params[1], params[2], params[3]

    def stackviewer(self, flist_oid=None):
        if self.usr_exc_info:
            typ, val, tb = self.usr_exc_info
        else:
            return None
        flist = None
        if flist_oid is not None:
            flist = self.rpchandler.get_remote_proxy(flist_oid)
        while tb and tb.tb_frame.f_globals["__name__"] in ["rpc", "run"]:
            tb = tb.tb_next
        sys.last_type = typ
        sys.last_value = val
        item = StackViewer.StackTreeItem(flist, tb)
        return RemoteObjectBrowser.remote_object_tree_item(item)

    def getcwd(self):
        return os.getcwd()

def displayhook(val):
    global jobs
    jobs.current_by_thread().displayhook(val)

capture_warnings(False)  # Make sure turned off; see issue 18081

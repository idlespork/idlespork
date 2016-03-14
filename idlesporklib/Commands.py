"""
    Parsing and handling of shell commands
"""

import re
import cStringIO
import os
import compiler
import CompilerPatch
CompilerPatch.patch_compiler()
import time
import parser
import symbol

class CommandError(Exception):
    pass

class Command(object):
    GUI_COMMAND = False
    def __init__(self):
        self.show_help = False
    def parse(self, line):
        pass
    def flag_h(self, line):
        self.show_help = True

class JobsCommand(Command):
    CMD = 'jobs'

    def __init__(self):
        Command.__init__(self)
        self.a = False
        self.o = self.g = self.t = None

    def descr(self):
        D = """\
jobs [-a | -o <num> | -g <varname> | -t <num> | -h]
    -a: show all jobs
    -o <num>: show the output of the <num>th job
    -g <varname>: get the jobs object into <varname>
    -t <num>: toggle output redirection for the <num>th job
    -h: show this help"""
        return D

    def flag_a(self, line): self.a = True
    def flag_o(self, line): self.o = line.next_int()
    def flag_g(self, line): self.g = line.next_str()
    def flag_t(self, line): self.t = line.next_int()

    def run(self, world):
        if self.show_help:
            print >>world.remote_stdout, self.descr()
        elif self.a:
            print >>world.remote_stdout, world.jobs.alljobs(),
        elif self.o is not None:
            try:
                print >>world.remote_stdout, world.jobs[self.o].getoutput(),
            except KeyError:
                print >>world.remote_stderr, \
                    "Job [%d] does not exist" % self.o
        elif self.g is not None:
            setattr(world.main, self.g, world.jobs)
        elif self.t is not None:
            world.jobs.toggleoutput(self.t)
        else:
            print >>world.remote_stdout, world.jobs

class KillCommand(Command):
    CMD = 'kill'

    def descr(self):
        D = """\
kill [n | -h]
    n: kill the n-th job
    -h: show this help"""
        return D

    def parse(self, line):
        if not self.show_help:
            self.jobid = line.next_int()

    def run(self, world):
        if self.show_help:
            print >>world.remote_stdout, self.descr()
            return
        try:
            j = world.jobs[self.jobid]
        except KeyError:
            print >>world.remote_stderr, 'Jobs [%d] does not exist' % self.jobid
            return
        j.kill()

class CdCommand(Command):
    CMD = 'cd'

    def descr(self):
        D = """\
cd path
    path may be absolute or relative"""
        return D

    def parse(self, line):
        if self.show_help:
            return
        try:
            self.dir = line.next_str()
        except EndOfLineException:
            self.dir = '~'

    def run(self, world):
        if self.show_help:
            print >>world.remote_stdout, self.descr()
            return
        try:
            os.chdir(os.path.expanduser(self.dir))
        except Exception, e:
            print >>world.remote_stderr, e
            return
        world.interp.update_subprocess_cwd(os.getcwd())
        print >>world.remote_stdout, "--> %s" % os.getcwd()


class ShellCommand(Command):
    def __init__(self, line, varname):
        Command.__init__(self)
        self.line = line
        self.varname = varname

    def run(self, world):
        import subprocess
        p = subprocess.Popen(self.line, shell=True, \
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        s = p.stdout.read(100)
        if self.varname:
            output = cStringIO.StringIO() 
        else:
            output = world.remote_stdout 

        while s != '':
            output.write(s)
            s = p.stdout.read(100)
        if self.varname:
            setattr(world.main, self.varname, output.getvalue())

class OpenFileCommand(Command):
    CMD = 'open'
    GUI_COMMAND = True

    def descr(self):
        D = """ open
Opens a file to edit"""
        return D

    def parse(self, line):
        if self.show_help:
            self.GUI_COMMAND = False
            return
        self.file = line.next_str()

    def run(self,world):
        assert self.show_help
        print >>world.remote_stdout, self.descr()
        

    def run_gui(self, gui):
        if self.file=='':
            raise CommandError('Open error: Specify filename')
        cwd = gui.interp.rpcclt.remotecall("exec", 
            "getcwd", (), {})
        path = os.path.join(cwd, os.path.expanduser(self.file))
        gui.flist.open(path)

import types
import inspect
def helper(x):
    REPR = repr(x)
    if len(REPR)>20*2:
        REPR = REPR[:20] + ' <...> ' + REPR[-20:]
    D  = 'SporkHelp for %s\n'%REPR
    D += '--------------%s\n'%('-'*len(REPR))
    D += 'Type:\t\t%s\n'%str(type(x).__name__)
    D += 'Base Class:\t%s\n'%str(object.__getattribute__(x, '__class__'))
    STR = str(x)
    if len(STR)>97*2:
        STR = STR[:97] + ' <...> ' + STR[-97:]
    D += 'String Form:\t%s\n'%STR
    if hasattr(x,'__len__'):
        # This is problematic for classes/types
        try:
            D += 'Length:\t\t%d\n'%len(x)
        except:
            pass
    if isinstance(x,types.FunctionType) or isinstance(x,types.MethodType):
        D += 'Filename:\t%s\n'%x.func_code.co_filename
        AS = inspect.getargspec(x)
        ARGS,VARARGS,KEYWORDS,DEFS = AS
        if DEFS is None:
            DEFS = []
        for i in xrange(1,len(DEFS)+1):
            ARGS[-i] = ARGS[-i]+'='+repr(DEFS[-i])
        if VARARGS is not None:
            ARGS.append('*%s'%VARARGS)
        if KEYWORDS is not None:
            ARGS.append('**%s'%KEYWORDS)
        ARGS = ', '.join(ARGS)
        D += 'Definition:\t%s\n'%(x.func_name+'('+ARGS+')')

    # Docstring
    try:
        doc = x.__doc__
    except:
        doc = None
    if isinstance(doc, str):
        D += 'Docstring:\n'
        D += '\t' + x.__doc__.replace('\n','\n\t')
    
    D += '\n'
    return D

def get_code(x):
    if isinstance(x,types.FunctionType) or isinstance(x,types.TypeType) \
       or isinstance(x,types.MethodType):
        try:
            return inspect.getsource(x)
        except IOError:
            pass
        except TypeError,e:
            if 'built-in' in e.message:
                return 'built-in'
    else:
        return 'Object is not getcodable'
            

class CodeException(Exception):
    pass

class CodeCommand(Command):
    def __init__(self, source, code, filename):
        """filename should be something of the form <pyshell#10>"""
        Command.__init__(self)
        self.code = code
        self.source = source
        self.filename = filename

    def run(self, world):

        if self.show_help:
            if self.show_help=='get_code':
                print get_code(eval(self.code, world.main.__dict__))
            else:
                print helper(eval(self.code, world.main.__dict__))
        elif self.bg_run:
            if isinstance(self.bg_run,tuple) and self.bg_run[0]=='after':
                jnum = world.executive.runcode_after(self.code, self.source, self.bg_run[1])
                if jnum is not None:
                    print '**** [%d] - Queued after [%d] ****'%(jnum,self.bg_run[1])
            else:
                world.executive.runcode_bg(self.code, self.source)
        else:
            world.current_thread.description = self.source
            world.current_thread.start_time = time.time()
            world.executive.runcode(self.code, self.source, self.filename)

def create_code_command(interp, source, show_help, bg_run):
    try:
        filename = interp.stuffsource(source)
        symb = 'single'
        if show_help: symb = 'eval'
        
        code = _maybe_compile(compiler.compile, source, filename, symb)
    except (OverflowError, SyntaxError, ValueError):
        interp.showsyntaxerror(filename)
        return None

    if code is None:
        return None

    p = parser.suite(source).tolist()
    stmts = [x[1][0] for x in p if isinstance(x, list) and \
        x[0] == symbol.stmt]
    if symbol.compound_stmt in stmts and not source.endswith('\n'):
        return None
        
    cmd = CodeCommand(source, code, filename)
    cmd.show_help = show_help
    cmd.bg_run = bg_run
    return cmd

def _maybe_compile(compiler, source, filename, symbol):
    # Check for source consisting of only blank lines and comments
    for line in source.split("\n"):
        line = line.strip()
        if line and line[0] != '#':
            break               # Leave it alone
    else:
        if symbol != "eval":
            source = "pass"     # Replace it with a 'pass' statement

    err1 = err2 = None
    code = code1 = None
    e1 = e2 = None

    try:
        code = compiler(source, filename, symbol)
    except SyntaxError:
        pass

    try:
        code1 = compiler(source + "\n", filename, symbol)
    except SyntaxError, err1:
        e1 = err1.args

    try:
        compiler(source + "\n\n", filename, symbol)
    except SyntaxError, err2:
        e2 = err2.args

    if code:
        return code

    if not code1 and e1 == e2:
        raise SyntaxError, err1

    #if not code1 and repr(err1) == repr(err2):
    #    raise SyntaxError, err1


#  Spork commands:
 
class SporkTitleCommand(Command):
    CMD = 'title'
    short_descr = "change the title of the idlespork window"
    
    def __init__(self):
        Command.__init__(self)
        self.GUI_COMMAND = True

    def parse(self,line):
        if self.show_help: return 
        self.newname = line.next_str()

    def run_gui(self,gui):
        gui.shell_title = self.newname
        gui.top.wm_title(gui.short_title())
    
    def descr(self):
        D = """Usage: spork title "new title"
change the title of the idlespork window."""
        return D

class HistoryToggleCommand(Command):
    CMD = 'history'
    short_descr = "Show/hide/toggle the history box"

    def __init__(self, cmd = None):
        "new_status can be 'show', 'hide' or 'toggle'"
        Command.__init__(self)
        self.cmd = cmd
        self.GUI_COMMAND = True
        if cmd not in [None, 'show', 'hide', 'toggle']:
            raise ValueError("Invalid cmd (must be either 'show', "
                  "'hide' or 'toggle')")

    def parse(self, line):
        if self.show_help: return 
        self.cmd = line.next_str()
        if self.cmd not in [None, 'show', 'hide', 'toggle']:
            raise ValueError("Invalid cmd (must be either 'show', "
                  "'hide' or 'toggle')")

    def descr(self):
        return """Usage: spork history [show/hide/toggle]
Show/hide/toggle the history box"""

    def run_gui(self, gui):
        if self.cmd == 'show':
            gui.histwin.show()
        elif self.cmd == 'hide':
            gui.histwin.hide()
        elif self.cmd == 'toggle':
            gui.histwin.toggle()

class SporkRestartCommand(Command):
    CMD = 'restart'
    short_descr = "Restart shell"
    
    def __init__(self):
        Command.__init__(self)
        self.GUI_COMMAND = True

    def parse(self,line):
        if self.show_help: return 

    def run_gui(self,gui):
        gui.restart_shell()
    
    def descr(self):
        D = """Usage: spork restart
restart shell."""
        return D

class SporkCommand(Command):
    CMD = 'spork'
    COMMANDS = [SporkTitleCommand, HistoryToggleCommand, SporkRestartCommand]
    COMMANDS_DICT = dict([(x.CMD, x) for x in COMMANDS])
    SUBS = COMMANDS_DICT.keys()

    def descr(self):
        cmds = [(x.CMD, x.short_descr) for x in SporkCommand.COMMANDS]
        width = max(len(x[0]) for x in cmds)
        D = """spork <command>
possible commands:
"""     + '\n'.join(['   %s - %s' % (x[0].ljust(width), x[1]) for x in cmds])
        return D
 
    def parse(self, line):
        try:
            # TODO check if subcommand is valid
            self.command = SporkCommand.COMMANDS_DICT[line.next_str()]()
        except EndOfLineException:
            if self.show_help:
                return
            else:
                raise EndOfLineException("Possible commands: %s" %
                                ', '.join([x.CMD for x in self.COMMANDS]))
        except KeyError, e:
            raise UnkCmdError("Unknown command '%s'" % str(e.message)) 

        if not self.show_help:
            self.command.parse(line)

        if not self.show_help:
            self.GUI_COMMAND = self.command.GUI_COMMAND

    def run(self,world):
        if self.show_help:
            if hasattr(self,'command'):
                print >>world.remote_stdout, self.command.descr()
            else:
                print >>world.remote_stdout, self.descr()
        else:
            self.command.run(world)
    
    def run_gui(self,gui):
        self.command.run_gui(gui)


commands = [JobsCommand, KillCommand, CdCommand, OpenFileCommand, SporkCommand]
command_names = [x.CMD for x in commands]
command_kws = ['spork %s'%S for S in SporkCommand.SUBS] + [x.CMD for x in commands]
cmd = dict([(c.CMD,c) for c in commands])

class ParserException(Exception):
    pass

class ParserFlagException(ParserException):
    pass

class ParserTooManyParamsError(ParserException):
    pass

class ParserUnGetcodableEntityError(ParserException):
    pass

class ParserIllegalRequestError(ParserException):
    pass

def parse(interp, txt):
    # Handle shell command (x = !ls)
    M = re.match(r'^\s*((\w+)\s*=\s*)?!', txt)
    if M:
        varname = M.group(2)
        return ShellCommand(txt[M.end():], varname)

    # Handle ?,??
    show_help = False
    M = re.search('\?\?\s*$', txt)
    if M:
        show_help = 'get_code'
        txt = txt[:M.start()]
    else:
        M = re.search('\?\s*$', txt)
        if M:
            show_help = True
            txt = txt[:M.start()]

    # Handle shell command
    
    C, txt = get_command(txt)
     
    if C:
        if show_help == 'get_code':
            raise ParserUnGetcodableEntityError('Commands are not getcodable')
        cmd = C()
        line = Line(txt)
        flag = line.get_flag()
        while flag:
            if flag[1]=='h':
                show_help = True
            line.virtualize(flag[0])
            line.set_exclusive(True)

            try:
                getattr(cmd, 'flag_' + flag[1])(line)
            except AttributeError:
                raise ParserFlagException('%s does not support the flag "%s"'%(cmd.CMD, flag[1]))
                

            line.set_exclusive(False)
            line.devirtualize()
            flag = line.get_flag()
        cmd.show_help = show_help
        cmd.parse(line)
        if not line.ended():
            raise ParserTooManyParamsError('Too many arguments for %s'%cmd.CMD)
        cmd.show_help = show_help
    else:
        # parse '&'
        bg_run = False
        M = re.search(r'\&(\s*>\s*(\d+))?(\s*)$',txt)
        if M:
            if show_help:
                raise ParserIllegalRequestError('Cannot run help in background')
            jobid = M.group(2)
            if jobid is None:
                bg_run = True
            else:
                jobid = int(jobid)
                bg_run = ('after',jobid)
            txt = txt[:M.start()] + M.group(3)
            
        cmd = create_code_command(interp, txt, show_help, bg_run)
    return cmd

def get_command(txt):
    M = re.match(r"^(\w+)(\s|$)", txt)
    if not M: return None, txt
    cmdname = M.group(1)
    if cmdname not in cmd: return None, txt
    return cmd[cmdname], txt[M.end():]

class LineException(Exception):
    pass

class LineQuoteException(LineException):
    pass

class LineTypeError(LineException):
    pass

class LineFlagError(LineException):
    pass

class EndOfLineException(LineException):
    pass

class UnkCmdError(LineException):
    pass

class Line(object):
    def __init__(self,s):
        s = s.split()
        L = []
        inquotes = False
        for a in s:
            if not inquotes:
                if a[0] == '"':
                    inquotes = True
                    a = a[1:]
                    if a[-1]=='"':
                        inquotes = False
                        a = a[:-1]
                L.append([a])
            else:
                if a[-1] == '"':
                    inquotes = False
                    a = a[:-1]
                L[-1].append(a)
        if inquotes:
            raise LineQuoteException("Unmatched '\"'")
        self.LINE = [' '.join(c) for c in L]
        self.lptr = 0
        self.__saved_lptr = 0
        self.exclusive = False

    def __len__(self):
        return len(self.LINE)

    def ended(self):
        return self.lptr>=len(self)

    def next(self):
        if self.lptr >= len(self.LINE):
            raise EndOfLineException()
        if self.exclusive:
            self.LINE.pop(self.lptr)
        else:
            self.lptr += 1

    def peek(self):
        if self.lptr >= len(self.LINE):
            raise EndOfLineException()
        return self.LINE[self.lptr]

    def next_str(self):
        res = self.peek()
        self.next()
        return res

    def next_int(self):
        res = self.peek()
        try:
            res = int(res)
            self.next()
            return res
        except ValueError:
            raise LineTypeError('Field \'%s\' could not be '
            'converted to int.' % res)
    
    def set_exclusive(self,b=True):
        self.exclusive = b

    def virtualize(self, new_pos):
        self.__saved_lptr = self.lptr
        self.lptr = new_pos

    def devirtualize(self):
        self.lptr = self.__saved_lptr

    # Might want to change the way flags are identified:
    # this is the place.
    def get_flag(self):
        for (i,l) in enumerate(self.LINE):
            if l[0]=='-':
                if (len(l)==2) and (l[1].isalpha()):
                    return (i,self.LINE.pop(i)[1])
                elif (len(l)>2) and l[1]=='-':
                    return (i,self.LINE.pop(i)[2:])
                else:
                    raise LineFlagError('Invalid Flag Syntax')
        return False 


"""CallTips.py - An IDLE Extension to Jog Your Memory

Call Tips are floating windows which display function, class, and method
parameter and docstring information when you type an opening parenthesis, and
which disappear when you type a closing parenthesis.

"""
import __main__
import re
import sys
import textwrap
import types

from idlesporklib import CallTipWindow
from idlesporklib.HyperParser import HyperParser


class CallTips:
    """
    Extension that shows tips for function calls

    Configure the force-open-calltip key binding.
    """

    menudefs = [
        ('edit', [
            ("Show call tip", "<<force-open-calltip>>"),
        ])
    ]

    def __init__(self, editwin=None):
        if editwin is None:  # subprocess and test
            self.editwin = None
            return
        self.editwin = editwin
        self.text = editwin.text
        self._make_calltip_window = self._make_tk_calltip_window
        self.calltip = None

    def close(self):
        self._make_calltip_window = None

    def _make_tk_calltip_window(self):
        # See __init__ for usage
        return CallTipWindow.CallTip(self.text)

    def force_open_calltip_event(self, event):
        """
        Happens when the user really wants to open a CallTip, even if a
        function call is needed.
        """
        self.open_calltip(True)

    def try_open_calltip_event(self, event):
        """
        Happens when it would be nice to open a CallTip, but not really
        necessary, for example after an opening bracket, so function calls
        won't be made.
        """
        self.open_calltip(False)

    def refresh_calltip_event(self, event):
        """
        If there is already a calltip window, check if it is still needed,
        and if so, reload it.
        """
        if self.calltip and self.calltip.is_active():
            self.open_calltip(False)

    def open_calltip(self, evalfuncs):
        hp = HyperParser(self.editwin, "insert")
        sur_paren = hp.get_surrounding_brackets('(')
        if not sur_paren:
            self.calltip.hidetip()
            return
        hp.set_index(sur_paren[0])
        expression = hp.get_expression()
        if self.calltip and not expression or (not evalfuncs and expression.find('(') != -1):
            self.calltip.hidetip()
            return
        arg_text = self.fetch_tip(expression)
        if self.calltip and not arg_text:
            self.calltip.hidetip()
            return

        self.calltip = self._make_calltip_window()
        self.calltip.showtip(arg_text, sur_paren[0], sur_paren[1])

    def arg_names(self, evalfuncs):
        hp = HyperParser(self.editwin, "insert")
        sur_paren = hp.get_surrounding_brackets('(')
        if not sur_paren:
            return
        hp.set_index(sur_paren[0])
        expression = hp.get_expression()
        if not expression or (not evalfuncs and expression.find('(') != -1):
            return
        return self.fetch_tip(('args', expression))

    def fetch_tip(self, expression):
        """Return the argument list and docstring of a function or class

        If there is a Python subprocess, get the calltip there.  Otherwise,
        either fetch_tip() is running in the subprocess itself or it was called
        in an IDLE EditorWindow before any script had been run.

        The subprocess environment is that of the most recently run script.  If
        two unrelated modules are being edited some calltips in the current
        module may be inoperative if the module was not the last to run.

        To find methods, fetch_tip must be fed a fully qualified name.

        """
        try:
            rpcclt = self.editwin.flist.pyshell.interp.rpcclt
        except AttributeError:
            rpcclt = None
        if rpcclt:
            # print(rpcclt.run_extension_function('CallTips', 'fetch_tip', (expression,), {}))
            return rpcclt.remotecall("exec", "get_the_calltip",
                                     (expression,), {})
        else:
            if isinstance(expression, tuple) and expression[0] == 'args':
                entity = self.get_entity(expression[1])
                return get_arg_names(entity)

            entity = self.get_entity(expression)
            return get_arg_text(entity)

    def get_entity(self, expression):
        """Return the object corresponding to expression evaluated
        in a namespace spanning sys.modules and __main.dict__.
        """
        if expression:
            namespace = sys.modules.copy()
            namespace.update(__main__.__dict__)
            try:
                return eval(expression, namespace)
            except BaseException:
                # An uncaught exception closes idle, and eval can raise any
                # exception, especially if user classes are involved.
                return None

def _find_constructor(class_ob):
    # Given a class object, return a function object used for the
    # constructor (ie, __init__() ) or None if we can't find one.
    try:
        return class_ob.__init__.im_func
    except AttributeError:
        for base in class_ob.__bases__:
            rc = _find_constructor(base)
            if rc is not None: return rc
    return None

# The following are used in get_arg_text
_MAX_COLS = 85
_MAX_LINES = 5  # enough for bytes
_INDENT = ' '*4  # for wrapped signatures

def delist(a):
    """Return a nice representation of nested tuples

    This is a utility function for get_arg_text, used in case a function's definition includes tuples.
    Example input and output:
        >>> delist([['bar', 'shimi']])
        ... '((bar, shimi),)'
    """
    items = []
    for x in a:
        if isinstance(x, str):
            items.append(x)
        else:
            items.append(delist(x))
    if len(items) > 1:
        return '({})'.format(', '.join(items))
    else:
        return '({},)'.format(items[0])

def get_fob(ob):
    """Return tuple containing the following:
        1. actual function underlying ob.
        2. function arguments offset in fob.func_code.c_varnames.
        3. original callable function - if ob is a class instance, this is the bound function __call__.

    This is a utility function for get_arg_names and get_arg_text.
    """

    try:
        ob_call = ob.__call__
    except BaseException:
        if type(ob) is types.ClassType:  # old-style
            ob_call = ob
        else:
            return None, None, None

    arg_offset = 0
    if type(ob) in (types.ClassType, types.TypeType):
        # Look for the first __init__ in the class chain with .im_func.
        # Slot wrappers (builtins, classes defined in funcs) do not.
        fob = _find_constructor(ob)
        if fob is None:
            fob = lambda: None
        else:
            arg_offset = 1
    elif type(ob) == types.MethodType:
        # bit of a hack for methods - turn it into a function
        # and drop the "self" param for bound methods
        fob = ob.im_func
        if ob.im_self is not None:
            arg_offset = 1
    elif type(ob_call) == types.MethodType:
        # a callable class instance
        fob = ob_call.im_func
        arg_offset = 1
    else:
        fob = ob

    return fob, arg_offset, ob_call

def get_arg_names(ob):
    """Return the list of argument names to a callable object (that are not in a tuple).

    This function is used when AutoComplete is called in a function call. We would like to
    see the function's argument names. get_ob above already does half the work, we just need
    to get the actual names and filter out tuples (since it's not clear what we would do with them)."""
    fob, arg_offset, _ = get_fob(ob)
    try:
        argcount = fob.func_code.co_argcount
        ret = list(fob.func_code.co_varnames[arg_offset:argcount])
        ret = [arg for arg in ret if re.match("(?<!\d)\.\d+", arg) is None]
        return ret
    except:
        return

def get_arg_text(ob):
    '''Return a string describing the signature of a callable object, or ''.

    For Python-coded functions and methods, the first line is introspected.
    Delete 'self' parameter for classes (.__init__) and bound methods.
    The next lines are the first lines of the doc string up to the first
    empty line or _MAX_LINES.    For builtins, this typically includes
    the arguments in addition to the return value.
    '''
    fob, arg_offset, ob_call = get_fob(ob)

    if fob is None:
        return ''

    # Try to build one for Python defined functions
    if type(fob) in [types.FunctionType, types.LambdaType]:
        argcount = fob.func_code.co_argcount
        real_args = list(fob.func_code.co_varnames[arg_offset:argcount])
        defaults = fob.func_defaults or []
        defaults = list(map(lambda name: "=%s" % repr(name), defaults))
        defaults = [""] * (len(real_args) - len(defaults)) + defaults

        try:
            import inspect
            argspec = inspect.getargspec(fob)
            for i, arg in enumerate(real_args, arg_offset):
                if re.match("(?<!\d)\.\d+", arg) is not None:
                    real_args[i] = delist(argspec.args[i])
        except:
            pass

        items = map(lambda arg, dflt: arg + dflt, real_args, defaults)

        arg_offset = argcount
        for flag, pre in ((0x4, '*'), (0x8, '**')):
            if fob.func_code.co_flags & flag:
                items.append(pre + fob.func_code.co_varnames[arg_offset])
                arg_offset += 1

        argspec = ", ".join(items)
        argspec = "(%s)" % re.sub("(?<!\d)\.\d+", "<tuple>", argspec)

        lines = (textwrap.wrap(argspec, _MAX_COLS, subsequent_indent=_INDENT)
                if len(argspec) > _MAX_COLS else [argspec] if argspec else [])
    else:
        lines = []

    if isinstance(ob_call, types.MethodType):
        doc = ob_call.__doc__
    else:
        doc = getattr(ob, "__doc__", "")
    if doc:
        for line in doc.split('\n', _MAX_LINES)[:_MAX_LINES]:
            line = line.strip()
            if not line:
                break
            if len(line) > _MAX_COLS:
                line = line[: _MAX_COLS - 3] + '...'
            lines.append(line)
    argspec = '\n'.join(lines)
    return argspec

if __name__ == '__main__':
    from unittest import main
    main('idlesporklib.idle_test.test_calltips', verbosity=2)

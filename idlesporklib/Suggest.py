from __future__ import print_function

import exceptions
import re
import sporktools
import sys
import imp
import traceback
import PyParse
from HyperParser import HyperParser

__main__ = sys.modules['__main__']
__builtin__ = sys.modules['__builtin__']
softnewline = False

def exception_suggest(typ, val, tb, source, filename):
    global softnewline
    softnewline = True
    last_trace = traceback.extract_tb(tb)[-1]
    if typ == exceptions.NameError:
        m = re.match("^(?:global )?name '(.*)' is not defined$", str(val))
        if m:
            undefname = m.group(1)
            _import_suggest(undefname, source)
            _spelling_suggest(undefname, source, last_trace, filename)
    if typ == exceptions.AttributeError:
        m = re.search("object has no attribute '(.*)'$", str(val))
        if m:
            undefname = m.group(1)
            _spelling_suggest_attr_error(undefname, source, \
                last_trace, filename)
            
def _import_suggest(name, source):
    try:
        fl, path, desc = imp.find_module(name)
        if fl is not None: fl.close()
    except ImportError:
        return
    link1 = sporktools.Links.ExecCodeLink(None, "import %s" % name, \
        "import %s" % name).create()
    #link2 = sporktools.Links.ExecCodeLink(None, "import and rerun", ["import %s" % name, source]).create()
    _newline()
    print("Do you want to %s?" % (link1), file=sys.stderr)
    #print("Do you want to %s? %s?" % (link1, link2), file=sys.stderr)

def _spelling_suggest_attr_error(name, source, last_trace, filename):
    if last_trace[0] != filename: return
    idx = source.find("." + name)
    if idx == -1: return

    #make sure ".name" appears only once
    idx2 = source.find("." + name, idx + 1)
    if idx2 != -1: return

    src_start = source[:idx]
    objstr = _get_last_object(src_start)
    try:
        obj = get_entity(objstr)
        _spelling_suggest(name, source, last_trace, filename, dir(obj))
    except:
        return

def _spelling_suggest(name, source, last_trace, filename, lst = None):
    if last_trace[0] != filename:
        return

    if lst is None:
        lst = dir(__main__) + dir(__builtin__)

    cl = close_words(name, lst, 3)
    if len(cl) > 0:
        links = []
        for word in cl:
            links.append(sporktools.Links.ExecCodeLink(None, \
                word, source.replace(name, word)).create())
        _newline()
        print("Did you mean %s?" % " / ".join(links), file=sys.stderr)

def _newline():
    global softnewline
    if softnewline:
        print(file=sys.stderr)
    softnewline = False

def iter_close_words(word, all_words):
    # Deletion
    for i in xrange(len(word)):
        w = word[:i] + word[i+1:]
        if w in all_words: yield w

    # Swap
    for i in xrange(len(word) - 1):
        w = word[:i] + word[i+1] + word[i] + word[i+2:]
        if w in all_words: yield w

    # Insertions & substitutions
    for w in all_words:
        for i in xrange(len(w)):
            w1 = w[:i] + w[i+1:]
            if w1 == word: yield w
            if w1 == word[:i] + word[i+1:]: yield w

def close_words(word, all_words, max_words = None):
    if len(word) <= 1: return []
    r = []
    for x in iter_close_words(word, all_words):
        if x != word and x not in r:
            r.append(x)
            if len(r) == max_words:
                break
    return r

def _get_last_object(source):
    """source may be a partial python command.
    The last object of the command is returned.
    For example, if source is "1 + f(x.y", the function will return "x.y"
    If the object cannot be found, returns ""
    """

    hp = MiniHyperParser(source)
    if not hp.is_in_code():
        return
    return hp.get_expression()

# HyperParser requires a Text widget which we don't have
# This is a workaround
class MiniHyperParser(HyperParser):
    def __init__(self, source):
        self.rawtext = source
        parser = PyParse.Parser(1, 1)
        parser.set_str(source + ' \n')
        bracketing = parser.get_last_stmt_bracketing()
        bracketing = [x for x in bracketing if x[0] <= len(source)]
        self.bracketing = bracketing
        self.isopener = [i>0 and bracketing[i][1] > bracketing[i-1][1]
            for i in range(len(bracketing))]
        self.indexbracket = len(self.bracketing) - 1
        self.indexinrawtext = len(source)

# Same function from AutoComplete.py
def get_entity(name):
    "Lookup name in a namespace spanning sys.modules and __main.dict__"
    namespace = sys.modules.copy()
    namespace.update(__main__.__dict__)
    return eval(name, namespace)

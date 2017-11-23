from __future__ import print_function
import sys

from idlesporklib import Suggest
from idlesporklib.EnablableExtension import EnablableExtension, remoteboundmethod
import re

import os
import re
from collections import defaultdict
from inspect import isclass

from idlesporklib import sporktools
from idlesporklib.spell import candidates
from idlesporklib import Links


_old_import_suggest = Suggest.import_suggest


class SmartSuggest(EnablableExtension):
    """
    Extension for more automatic suggestions. Currently allows to scan
    all pythons files and cache symbol names. When you enter a name that isn't in
    the namespace but is cached - you get a suggestion.

    For example, on typing `walk` before `os` is imported, SmartSuggest offers you a link
    to import the `os` module.
    """
    allobjs = None
    executing_patch = False
    patched = False

    old_import_suggest = None

    def __init__(self, editwin=None):
        if editwin is not None and hasattr(editwin, 'interp'):
            self.editwin = editwin
            editwin.interp.register_onrestart(self._loop_init)
            self.editwin.text.after_idle(self._loop_init)

    def _loop_init(self):
        """Wait until rpc is up and running."""
        try:
            if hasattr(self.editwin.flist.pyshell.interp, "rpcclt"):
                self._patch_suggestions()
        except AttributeError:
            self.editwin.text.after_idle(self._loop_init)

    def close(self):
        try:
            self.editwin.interp.unregister_onrestart(self._loop_init)
        except AttributeError:
            pass
        self._close()

    @remoteboundmethod
    def _close(self):
        SmartSuggest.allobjs = None
        SmartSuggest.executing_patch = False
        SmartSuggest.patched = False
        Suggest.import_suggest = _old_import_suggest

    @remoteboundmethod
    def _patch_suggestions(self):
        from threading import Thread
        Thread(target=SmartSuggest.patch_suggestions).start()

    @staticmethod
    def patch_suggestions():
        if SmartSuggest.patched:
            print('Suggestions already patched. ')
            return
        elif SmartSuggest.executing_patch:
            print('Patching already taking place... ')
            return

        print('Preparing suggestions... ')

        SmartSuggest.executing_patch = True
        SmartSuggest.inspect_all_objs()

        def new_import_suggest(name, source):
            _old_import_suggest(name, source)

            cl = candidates(name, SmartSuggest.allobjs)
            suggestions = []

            if len(cl) > 0:
                for word in cl:
                    for (t, modulepath), (filepath, linenum) in SmartSuggest.allobjs[word].items():
                        if t == 'module':
                            if filepath not in ['builtin', '']:
                                tag = 'M'
                                filelink = Links.FileLink(None, 'M', filepath, linenum + 1).create()
                            else:
                                tag = 'BM'
                                filelink = 'BM'

                            if modulepath == '' or filepath == 'builtin':
                                link1 = Links.ExecCodeLink(None, "%s" % word,
                                                                      "import %s" % word).create()
                                suggestions.append(("(%s) import %s" % (filelink, link1),
                                                    "(%s) import %s" % (tag, word)))
                            else:
                                link1 = Links.ExecCodeLink(None, "%s" % word,
                                                                      "from %s import %s" % (modulepath, word)).create()
                                suggestions.append(("(%s) from %s import %s" % (filelink, modulepath, link1),
                                                    "(%s) from %s import %s" % (tag, modulepath, word)))
                        else:
                            if t == 'class':
                                tag = 'C'
                            elif t == 'def':
                                tag = 'F'
                            else:  # t == 'var'
                                tag = 'V'

                            if filepath not in ['builtin', '']:
                                filelink = Links.FileLink(None, tag, filepath, linenum + 1).create()
                            else:
                                filelink = 'B' + tag
                            link1 = Links.ExecCodeLink(None, "%s" % word,
                                                                  "from %s import %s" % (modulepath, word)).create()
                            suggestions.append(("(%s) from %s import %s" % (filelink, modulepath, link1),
                                                "(%s) from %s import %s" % (tag, modulepath, word)))

            if suggestions:
                Suggest.newline()
                print("Here are some import suggestions:", file=sys.stderr)
                for suggestion, realtxt in sorted(suggestions, key=lambda x: x[1]):
                    Suggest.newline()
                    print(suggestion, file=sys.stderr)

        Suggest.import_suggest = new_import_suggest
        SmartSuggest.executing_patch = False
        SmartSuggest.patched = True
        print('Done preparing suggestions. ')

    @staticmethod
    def inspect_all_objs():
        if SmartSuggest.allobjs is not None:
            return

        visited = set()
        defclass = re.compile('(class|def) ([_A-z][_A-z0-9]*)[\(:]')
        variable = re.compile('([A-z][_A-z0-9]+)\s=')
        objs = defaultdict(dict)

        rootmodules = list(sys.builtin_module_names)
        for name in rootmodules:
            objs[name][('module', name)] = ('builtin', 0)
            m = __import__(name)
            for attr in dir(m):
                a = getattr(m, attr)
                if isclass(a):
                    objs[attr][('class', name)] = ('builtin', 0)
                elif callable(a):
                    objs[attr][('def', name)] = ('builtin', 0)

        for path in sys.path:
            if path == '':
                path = '.'

            if os.path.isdir(path):
                for root, dirs, nondirs in os.walk(path, followlinks=False):
                    if '-' in root[len(path) + 1:] or root in visited:
                        dirs[:] = []
                        continue

                    visited.add(root)

                    for name in nondirs:
                        if name.endswith('.py'):
                            filepath = os.path.join(root, name)

                            if name == '__init__.py':
                                name = root[len(path) + 1:].split('/')[-1]
                                modulepath = '.'.join(root[len(path) + 1:].split('/')[:-1])
                            else:
                                name = name[:-3]
                                modulepath = root[len(path) + 1:].replace('/', '.')

                            if modulepath.endswith('.'):
                                modulepath = modulepath[:-1]

                            if ('module', modulepath) not in objs[name]:
                                objs[name][('module', modulepath)] = (filepath, 0)

                                try:
                                    with open(filepath, 'r') as f:
                                        for i, line in enumerate(f):
                                            fullmodpath = '%s.%s' % (modulepath, name) if modulepath else name
    
                                            m = defclass.match(line)
                                            if m:
                                                t, sym = m.groups()
                                                objs[sym][(t, fullmodpath)] = (filepath, i)
                                            else:
                                                m = variable.match(line)
                                                if m:
                                                    objs[m.group(1)][('var', fullmodpath)] = (
                                                        filepath, i)
                                except IOError:
                                    pass

        SmartSuggest.allobjs = objs

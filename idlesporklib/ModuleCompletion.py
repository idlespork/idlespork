# -----------------------------------------------------------------------------
#  Copyright (c) IPython Development Team.
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file IPython_COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------
#
# The class below was constructed from code copied from the file `completerlib.py` in the IPython project.

from __future__ import print_function
import inspect
import os
import re
import sys
import imp
from collections import defaultdict
from inspect import isclass
from time import time
from zipimport import zipimporter

from idlesporklib.configHandler import idleConf
from idlesporklib import sporktools
from idlesporklib import Suggest
from idlesporklib.spell import candidates
from idlesporklib import Links

try:
    # Python >= 3.3
    # noinspection PyCompatibility
    from importlib.machinery import all_suffixes
    _suffixes = all_suffixes()
except ImportError:
    from imp import get_suffixes
    _suffixes = [s[0] for s in get_suffixes()]


class ModuleCompletion(object):
    """

    """
    # Time in seconds after which to return
    TIMEOUT_GIVEUP = idleConf.GetOption("extensions", "AutoComplete",
                                        "imports-timeout", type="int", default=2)

    # Regular expression for the python import statement
    import_re = re.compile(r'(?P<name>[a-zA-Z_][a-zA-Z0-9_]*?)'
                           r'(?P<package>[/\\]__init__)?'
                           r'(?P<suffix>%s)$' %
                           r'|'.join(re.escape(s) for s in _suffixes))

    rootmodules_cache = {}

    allobjs = None
    executing_patch = False
    patched = False

    @staticmethod
    def module_list(path):
        """
        Return the list containing the names of the modules available in the given
        folder.
        """
        # sys.path has the cwd as an empty string, but isdir/listdir need it as '.'
        if path == '':
            path = '.'

        # A few local constants to be used in loops below
        pjoin = os.path.join

        if os.path.isdir(path):
            # Build a list of all files in the directory and all files
            # in its subdirectories. For performance reasons, do not
            # recurse more than one level into subdirectories.
            files = []
            for root, dirs, nondirs in os.walk(path, followlinks=True):
                subdir = root[len(path) + 1:]
                if subdir:
                    files.extend(pjoin(subdir, f) for f in nondirs)
                    dirs[:] = []  # Do not recurse into additional subdirectories.
                else:
                    files.extend(nondirs)

        else:
            try:
                files = list(zipimporter(path)._files.keys())
            except:
                files = []

        # Build a list of modules which match the import_re regex.
        modules = []
        for f in files:
            m = ModuleCompletion.import_re.match(f)
            if m:
                modules.append(m.group('name'))
        return list(set(modules))

    @staticmethod
    def get_root_modules():
        """
        Returns a list containing the names of all the modules available in the
        folders of the pythonpath.
        """
        rootmodules_cache = ModuleCompletion.rootmodules_cache
        rootmodules = list(sys.builtin_module_names)
        start_time = time()
        store = False
        for path in sys.path:
            try:
                modules = rootmodules_cache[path]
            except KeyError:
                modules = ModuleCompletion.module_list(path)
                try:
                    modules.remove('__init__')
                except ValueError:
                    pass
                if path not in ('', '.'):  # cwd modules should not be cached
                    rootmodules_cache[path] = modules
            rootmodules.extend(modules)
            if time() - start_time > ModuleCompletion.TIMEOUT_GIVEUP:
                store = True
                break
        if store:
            ModuleCompletion.rootmodules_cache = rootmodules_cache
        rootmodules = list(set(rootmodules))
        return rootmodules

    @staticmethod
    def is_importable(module, attr, only_modules):
        if only_modules:
            return inspect.ismodule(getattr(module, attr))
        else:
            return not (attr[:2] == '__' and attr[-2:] == '__')

    @staticmethod
    def try_import(mod, only_modules=False):
        mod = mod.rstrip('.')
        try:
            m = __import__(mod)
        except:
            return []
        mods = mod.split('.')
        for module in mods[1:]:
            m = getattr(m, module)

        m_is_init = hasattr(m, '__file__') and '__init__' in m.__file__

        completions = []
        if (not hasattr(m, '__file__')) or (not only_modules) or m_is_init:
            completions.extend([attr for attr in dir(m) if
                                ModuleCompletion.is_importable(m, attr, only_modules)])

        completions.extend(getattr(m, '__all__', []))
        if m_is_init:
            completions.extend(ModuleCompletion.module_list(os.path.dirname(m.__file__)))
        completions = {c for c in completions if isinstance(c, (str, unicode))}
        completions.discard('__init__')
        return list(completions)

    @staticmethod
    def module_completion(line):
        """
        Returns a list containing the completion possibilities for an import line.

        The line looks like this :
        'import xml.d'
        'from xml.dom import'
        """

        words = line.split(' ')
        nwords = len(words)
        mods = []
        lastword = ''

        # from whatever <tab> -> 'import '
        if nwords >= 3 and words[-3] == 'from':
            return None
        # 'from xyz import abc<tab>'
        elif nwords >= 4 and words[-4] == 'from':
            mod = words[-3]
            mods = ModuleCompletion.try_import(mod)
            lastword = words[-1]
        # 'from xy<tab>' or 'import xy<tab>'
        elif nwords >= 2 and words[-2] in {'import', 'from'}:
            if words[-1] == '':
                mods = ModuleCompletion.get_root_modules()
            else:
                mod = words[-1].split('.')
                if len(mod) < 2:
                    mods = ModuleCompletion.get_root_modules()
                else:
                    mods = ModuleCompletion.try_import('.'.join(mod[:-1]), True)
                    lastword = mod[-1]

        if mods:
            if lastword:
                withcase = [mod for mod in mods if mod.startswith(lastword)]
                if withcase:
                    mods = withcase
                # if none, then case insensitive ones are ok too
                else:
                    text_low = lastword.lower()
                    mods = [mod for mod in mods if mod.lower().startswith(text_low)]
            mods = sorted(mods)
            if lastword.startswith('_'):
                return mods, mods
            else:
                return [mod for mod in mods if not mod.startswith('_')], mods

    @staticmethod
    def inspect_all_objs():
        if ModuleCompletion.allobjs is not None:
            return

        visited = set()
        defclass = re.compile('(class|def) ([_A-z][_A-z0-9]*)\(')
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
                for root, dirs, nondirs in os.walk(path, followlinks=True):
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

                                with open(filepath, 'r') as f:
                                    for i, line in enumerate(f):
                                        m = defclass.match(line)
                                        if m:
                                            t, sym = m.groups()
                                            objs[sym][(t, '%s.%s' % (modulepath, name))] = (filepath, i)
        ModuleCompletion.allobjs = objs

    @staticmethod
    def patch_suggestions():
        if ModuleCompletion.patched or ModuleCompletion.executing_patch:
            return

        ModuleCompletion.executing_patch = True
        ModuleCompletion.inspect_all_objs()

        old_import_suggest = Suggest.import_suggest

        def new_import_suggest(name, source):
            old_import_suggest(name, source)

            cl = candidates(name, ModuleCompletion.allobjs)
            suggestions = []

            if len(cl) > 0:
                for word in cl:
                    for (t, modulepath), (filepath, linenum) in ModuleCompletion.allobjs[word].items():
                        if t == 'module':
                            if filepath not in ['builtin', '']:
                                filelink = Links.FileLink(None, 'M', filepath, linenum + 1).create()
                            else:
                                filelink = 'BM'

                            if modulepath == '' or filepath == 'builtin':
                                link1 = sporktools.Links.ExecCodeLink(None, "%s" % word,
                                                                      "import %s" % word).create()
                                suggestions.append("(%s) import %s" % (filelink, link1))
                            else:
                                link1 = sporktools.Links.ExecCodeLink(None, "%s" % word,
                                                                      "from %s import %s" % (modulepath, word)).create()
                                suggestions.append("(%s) from %s import %s" % (filelink, modulepath, link1))
                        else:
                            tag = 'C' if t == 'class' else 'F'
                            if filepath not in ['builtin', '']:
                                filelink = Links.FileLink(None, tag, filepath, linenum + 1).create()
                            else:
                                filelink = 'B' + tag
                            link1 = sporktools.Links.ExecCodeLink(None, "%s" % word,
                                                                  "from %s import %s" % (modulepath, word)).create()
                            suggestions.append("(%s) from %s import %s" % (filelink, modulepath, link1))

            if suggestions:
                Suggest.newline()
                print("Here are some import suggestions:", file=sys.stderr)
                suggestions = sorted(suggestions, key=lambda x: x[3:])
                for suggestion in suggestions:
                    Suggest.newline()
                    print(suggestion, file=sys.stderr)

        Suggest.import_suggest = new_import_suggest
        ModuleCompletion.executing_patch = False
        ModuleCompletion.patched = True
        print('done preparing suggestions.')

#-----------------------------------------------------------------------------
#  Copyright (c) IPython Development Team.
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file IPython_COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# The class below was constructed from code copied from the file `completerlib.py` in the IPython project.


import inspect
import os
import re
import sys
from time import time
from zipimport import zipimporter

from configHandler import idleConf

try:
    # Python >= 3.3
    from importlib.machinery import all_suffixes
    _suffixes = all_suffixes()
except ImportError:
    from imp import get_suffixes
    _suffixes = [ s[0] for s in get_suffixes() ]


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
                    mods =  withcase
                # if none, then case insensitive ones are ok too
                else:
                    text_low = lastword.lower()
                    mods = [mod for mod in mods if mod.lower().startswith(text_low)]
            mods = sorted(mods)
            if lastword.startswith('_'):
                return mods, mods
            else:
                return [mod for mod in mods if not mod.startswith('_')], mods

"""
Module copied from Antony Lee's excellent IPython AutoImport module.
See
    https://github.com/anntzer/ipython-autoimport
and included AutoImport_LICENSE.txt in licenses folder.
"""
import __builtin__
import sys
import ast
import importlib
from types import ModuleType

from EnablableExtension import remoteboundmethod


_original_dict = None


def _report(txt):
    sys.stderr.write('AutoImport: {}\n'.format(txt))


def _get_import_cache(history):
    """Load a mapping of names to import statements from the IPython history.
    """

    import_cache = {}

    def _format_alias(alias):
        return ("import {0.name} as {0.asname}" if alias.asname
                else "import {0.name}").format(alias)

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                (import_cache.setdefault(alias.asname or alias.name, set())
                 .add(_format_alias(alias)))

        def visit_ImportFrom(self, node):
            if node.level:  # Skip relative imports.
                return
            for alias in node.names:
                (import_cache.setdefault(alias.asname or alias.name, set())
                 .add("from {} {}".format(node.module, _format_alias(alias))))

    for entry in history:
        try:
            parsed = ast.parse(entry)
        except SyntaxError:
            continue
        Visitor().visit(parsed)

    return import_cache


def _make_submodule_autoimporter_module(module):
    """Return a module sub-instance that automatically imports submodules.

    Implemented as a factory function to close over the real module.
    """

    if not hasattr(module, "__path__"):  # We only need to wrap packages.
        return module

    class SubmoduleAutoImporterModule(ModuleType):
        @property
        def __dict__(self):
            return module.__dict__

        # Overriding __setattr__ is needed even when __dict__ is overridden.
        def __setattr__(self, name, value):
            setattr(module, name, value)

        def __getattr__(self, name):
            try:
                value = getattr(module, name)
                if isinstance(value, ModuleType):
                    value = _make_submodule_autoimporter_module(value)
                return value
            except AttributeError:
                import_target = "{}.{}".format(self.__name__, name)
                try:
                    submodule = importlib.import_module(import_target)
                except Exception:
                    pass
                else:
                    _report("import {}".format(import_target))
                    return _make_submodule_autoimporter_module(submodule)
                raise  # Raise AttributeError without chaining ImportError.

    sai_module = SubmoduleAutoImporterModule(module.__name__)
    # Apparently, `module?` does not trigger descriptors, so we need to
    # set the docstring explicitly (on the instance, not on the class).
    # Then then only difference in the output of `module?` becomes the type
    # (`SubmoduleAutoImportModule` instead of `module`), which we should keep
    # for clarity.
    ModuleType.__setattr__(sai_module, "__doc__", module.__doc__)
    return sai_module


class AutoImporterMap(dict):
    """Mapping that attempts to resolve missing keys through imports.
    """

    def __init__(self, user_ns, history):
        super(AutoImporterMap, self).__init__(user_ns)
        self._import_cache = _get_import_cache(history)

    def __getitem__(self, name):
        try:
            value = super(AutoImporterMap, self).__getitem__(name)
        except KeyError as key_error:
            try:
                return getattr(__builtin__, name)
            except AttributeError:
                pass
            # Find single matching import, if any.
            imports = self._import_cache.get(name, {"import {}".format(name)})
            if len(imports) != 1:
                if len(imports) > 1:
                    _report("multiple imports available for {!r}".format(name))
                raise key_error
            import_source, = imports
            try:
                exec(import_source, self)  # exec recasts self as a dict.
            except Exception:  # Normally, ImportError.
                raise key_error
            else:
                _report(import_source)
                value = super(AutoImporterMap, self).__getitem__(name)
        if isinstance(value, ModuleType):
            return _make_submodule_autoimporter_module(value)
        else:
            return value


class AutoImport(object):
    """
    Automatically import symbols that haven't been imported in this session, but have
    been in previous ones.
    """

    def __init__(self, editwin=None):
        """
        @type editwin: PyShell.PyShell
        """
        import PyShell
        if not isinstance(editwin, PyShell.PyShell):
            return

        self.editwin = editwin
        editwin.interp.register_onrestart(self._loop_init)
        self._loop_init()

    def _loop_init(self):
        try:
            rpc = self.editwin.flist.pyshell.interp.rpcclt
            notyet = False
        except AttributeError:
            notyet = True

        if notyet or not self._remote_init(self.editwin.history.history):
            self.editwin.text.after_idle(self._loop_init)

    @remoteboundmethod
    def _remote_init(self, history):
        global _original_dict
        import run
        _original_dict = run.World.executive.locals
        run.World.executive.locals = AutoImporterMap(_original_dict, history)
        return True

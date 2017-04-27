from configHandler import idleConf


class EnablableExtension(object):
    """
    Base class for extensions that can be enabled/disabled without restart

    The setenabled method is called when the value is changed.
    When enabling, the default implementation loads the extension to every open window in the normal way.
    When disabled, it tries to call .close() on all instances.
    So it is recommended to override close, but not setenabled.
    """
    _enable = enable = True

    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            newcls = type.__new__(cls, name, bases, dct)
            if name != 'EnablableExtension':
                idleConf.GetOption("extensions", name, "enable", type="bool", default=True, member_name='enable')
            return newcls

        @property
        def enable(cls):
            return cls._enable

        @enable.setter
        def enable(cls, value):
            cls._enable = value
            cls.setenabled(value)

    @classmethod
    def setenabled(cls, value):
        name = cls.__name__
        import WindowList
        for win in WindowList.registry.dict.values()[0].instance_dict:
            if value:
                win.load_extension(name)
            elif name in win.extensions:
                try:
                    win.extensions[name].close()
                except AttributeError:
                    pass

                del win.extensions[name]


def boundremotefunc(func):
    """
    Decorator for class methods that should be called in the subprocess

    For example:

        class InlineMatplotlib:
            ...
            def turnon_event(self):
                success = self.turnon()
                if not success:
                    print("bummer")

            @boundremotefunc
            def turnon(self):
                success = matplotlib.swap_backend(self)
                return success

    This class could be an extension that when the event `turnon_event` is called
    the method `turnon` is called in the subprocess, and swaps the backend of matplotlib.

    Note that the decorated function (e.g. turnon above) returns to the main process.
    """
    def new_func(self, *args, **kwargs):
        try:
            rpcclt = self.editwin.flist.pyshell.interp.rpcclt
        except AttributeError:
            rpcclt = None

        if rpcclt:
            return rpcclt.run_extension_function(self.__class__.__name__, func.__name__, args, kwargs)
        else:
            return func(self, *args, **kwargs)
    return new_func

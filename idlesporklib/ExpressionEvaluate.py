import __main__
import sys

import CallTipWindow


def boundremotefunc(func):
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


class ExpressionEvaluate(object):
    """
    Extension for evaluating expressions in mid text
    """
    def __init__(self, editwin=None):
        if editwin is not None:
            self.text = text = editwin.text
            self.editwin = editwin
            self.calltip = None
            self.editwin.rmenu_specs.append(("_Evaluate expression", "<<evaluate-expression>>", 'rmenu_check_copy'))
            self.text.bind("<<evaluate-expression>>", self.evaluate_expression)

    def _make_tk_calltip_window(self):
        # See __init__ for usage
        return CallTipWindow.CallTip(self.text, hideOnCursorBack=False)

    def _remove_calltip_window(self, event=None):
        if self.calltip:
            self.calltip.hidetip()
            self.calltip = None

    def evaluate_expression(self, event=None):
        self.text.after_idle(self._evaluate_expression)

    def _evaluate_expression(self):
        self._remove_calltip_window()
        start, end = self.text.tag_ranges("sel")
        expression = self.text.get(start, end)  # type: str
        text = self.fetch_tip(expression)
        if not text:
            return
        self.calltip = self._make_tk_calltip_window()
        self.calltip.showtip(text, start, end)

    @boundremotefunc
    def fetch_tip(self, expression):
        if expression:
            namespace = sys.modules.copy()
            namespace.update(__main__.__dict__)
            try:
                entity = eval(expression, namespace)
                typ = '{}'.format(type(entity))
                if typ == "<type 'type'>":
                    typ = '{}'.format(entity)
                if typ.startswith("<type '") and typ.endswith("'>"):
                    typ = typ[len("<type '"):-2]
                entity = '{}'.format(entity)
                if len(typ) > 20 :
                    typ = ''
                if typ and typ not in entity:
                    ret = "{%s}: %s" % (typ, entity)
                else:
                    ret = entity
                if len(ret) > 85:
                    ret = ret[:82] + '...'
                return ret[:85]
            except BaseException as e:
                return repr(e)

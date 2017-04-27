from __future__ import print_function
import __main__
import sys

import textwrap


import CallTipWindow
from configHandler import idleConf
from idlesporklib.EnablableExtension import EnablableExtension, boundremotefunc

_MAX_TYPE_STRING_LEN = 20
_MAX_COLS = 85
_MAX_LINES = 5  # enough for bytes
_INDENT = ' '  # for wrapped signatures


class ExpressionEvaluate(EnablableExtension):
    """
    Extension for evaluating expressions in mid text
    """

    enableupdating = idleConf.GetOption("extensions", "ExpressionEvaluate",
                                        "enableupdating", type="bool", default=False, member_name='enableupdating')

    updatedelay = idleConf.GetOption("extensions", "ExpressionEvaluate",
                                     "updatedelay", type="int", default=1000, member_name='updatedelay')

    rmenu_spec = ("_Evaluate expression", "<<evaluate-expression>>", 'rmenu_check_copy')

    def __init__(self, editwin=None):
        if editwin is not None:
            self.text = text = editwin.text
            self.editwin = editwin
            self.calltip = None
            # If we're not in the right click menu, invalidate it so it gets built again.
            if ExpressionEvaluate.rmenu_spec not in self.editwin.rmenu_specs:
                self.editwin.rmenu_specs.append(ExpressionEvaluate.rmenu_spec)
                self.editwin.rmenu = None

            self.eval_bindid = self.text.bind("<<evaluate-expression>>", self.evaluate_expression)

    def close(self):
        if self.editwin is not None:
            try:
                # Remove right click menu item and invalidate menu.
                self.editwin.rmenu_specs.remove(("_Evaluate expression", "<<evaluate-expression>>", 'rmenu_check_copy'))
                self.editwin.rmenu = None
            except ValueError:
                pass
            try:
                self.text.unbind("<<evaluate-expression>>", self.eval_bindid)
            except:
                pass

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
        # Show tip and start loop.
        self.text.after(max(100, self.updatedelay), self.updatetip, self._evaluate_expression2())

    def _evaluate_expression2(self, content=None):
        self._remove_calltip_window()
        # If it's a new tooltip get the selection range.
        if content is None:
            start, end = self.text.tag_ranges("sel")
            expression = self.text.get(start, end)  # type: str
        else:
            expression, start, end = content
        text = self.fetch_tip(expression)
        if not text:
            return
        self.calltip = self._make_tk_calltip_window()
        self.calltip.showtip(text[0], start, end, *text[1:])

        return expression, start, end, self.calltip

    def updatetip(self, (expression, start, end, calltip)):
        # Check if enabled and if our calltip wasn't closed/hijacked.
        if ExpressionEvaluate.enableupdating and calltip == self.calltip == CallTipWindow.CallTip.instance:
            calltip = self._evaluate_expression2((expression, start, end))[-1]
            self.text.after(max(100, self.updatedelay), self.updatetip, (expression, start, end, calltip))

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
                entity = repr(entity)
                if len(typ) > _MAX_TYPE_STRING_LEN or typ in entity:
                    typ = None
                if len(entity) > _MAX_COLS:
                    tmp_entity = '\n'.join(textwrap.wrap(entity[:_MAX_COLS * _MAX_LINES], _MAX_COLS,
                                                         subsequent_indent=_INDENT)[:_MAX_LINES])
                    if tmp_entity.replace('\n' + _INDENT, '') != entity:
                        entity = tmp_entity[:-4] + ' ...'
                    else:
                        entity = tmp_entity
                if typ:
                    return '{%s}:' % typ, entity
                else:
                    return entity,
            except BaseException as e:
                return repr(e),

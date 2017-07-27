#! /usr/bin/env python

import time
from types import MethodType

from idlesporklib.configHandler import idleConf


class CustomizePrompt(object):
    """
    Extension to customize prompt line. Whatever you enter is given to `time.strftime`.
    """

    _PROMPT_FORMAT = idleConf.GetOption("extensions", "CustomizePrompt", "prompt-format", type="str", default='>>> ',
                                        member_name="_PROMPT_FORMAT")

    def __init__(self, editwin):
        def showprompt(self_):
            self_.resetoutput()
            s = time.strftime(CustomizePrompt._PROMPT_FORMAT.strip() + ' ')
            self_.console.write(s)
            self_.text.mark_set("insert", "end-1c")
            self_.set_line_and_column()
            self_.io.reset_undo()

        editwin.showprompt = MethodType(showprompt, editwin)

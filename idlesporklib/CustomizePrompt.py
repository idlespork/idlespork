#! /usr/bin/env python

import time
from types import MethodType

from idlesporklib.configHandler import idleConf


class CustomizePrompt(object):
    """
    Extension to customize prompt line. Whatever you enter is given to `time.strftime`,
    with the following three new directives:
        %dM - minutes since last execution

        %dS - seconds since last execution

        %df - deci-seconds since last execution
    """

    _PROMPT_FORMAT = idleConf.GetOption("extensions", "CustomizePrompt", "prompt-format", type="str", default='>>> ',
                                        member_name="_PROMPT_FORMAT")

    last_prompt = None

    def __init__(self, editwin):
        def showprompt(self_):
            if CustomizePrompt.last_prompt:
                time_diff = time.time() - CustomizePrompt.last_prompt
                mins, secs = divmod(time_diff, 60)
                mins, wsecs = int(mins), int(secs)
                ms = int((secs - wsecs) * 100)
            else:
                mins, wsecs, ms = 0, 0, 0

            s = CustomizePrompt._PROMPT_FORMAT.strip()
            s = s.replace('%dM', '%02d' % mins)
            s = s.replace('%dS', '%02d' % wsecs)
            s = s.replace('%df', '%02d' % ms)

            self_.resetoutput()
            s = time.strftime(s + ' ')
            self_.console.write(s)
            self_.text.mark_set("insert", "end-1c")
            self_.set_line_and_column()
            self_.io.reset_undo()

        try:
            old_runcmd_from_source = editwin.interp.runcmd_from_source
        # In case it's a file editor window.
        except AttributeError:
            return

        def runcmd_from_source(self_, line):
            CustomizePrompt.last_prompt = time.time()
            return old_runcmd_from_source(line)

        editwin.showprompt = MethodType(showprompt, editwin)
        editwin.interp.runcmd_from_source = MethodType(runcmd_from_source, editwin.interp)

import types
import symbol
import parser
import compiler.transformer as tr
import compiler.pycodegen as pycg
import token

def _visitConst(self, node):
    self.set_lineno(node)
    self.emit('LOAD_CONST', node.value)

pycg.CodeGenerator.visitConst = \
    types.MethodType(_visitConst, None, pycg.CodeGenerator)

def __parse(buf, mode="exec"):
    if mode == "exec":
        return tr.Transformer().parsesuite(buf)
    elif mode == "single":
        return tr.Transformer().parsesingle(buf)
    elif mode == "eval":
        return tr.Transformer().parseexpr(buf)
    else:
        raise ValueError("compile() arg 3 must be"
                         " 'exec' or 'eval' or 'single'")

def __parsesingle(self, text):
    """Return a modified parse tree for the given suite text."""
    node = parser.st2tuple(parser.suite(text), line_info = 1)
    n = node[0]
    if n == symbol.encoding_decl:
        self.encoding = node[2]
        node = node[1]
        n = node[0]
    return self.file_input(node[1:], False)

def __file_input(self, nodelist, doc_allowed = True):
    if doc_allowed:
        doc = self.get_docstring(nodelist, symbol.file_input)
    else:
        doc = None
    if doc is not None:
        i = 1
    else:
        i = 0
    stmts = []
    for node in nodelist[i:]:
        if node[0] != token.ENDMARKER and node[0] != token.NEWLINE:
            self.com_append_stmt(stmts, node)
    return tr.Module(doc, tr.Stmt(stmts))

def patch_compiler():
    global pycg
    global tr
    pycg.parse = __parse
    tr.Transformer.parsesingle = types.MethodType(__parsesingle, None, tr.Transformer)
    tr.Transformer.file_input = types.MethodType(__file_input, None, tr.Transformer)

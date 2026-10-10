"""
compiler.py  —  Analizador Léxico y Sintáctico con PLY
AST real: operador como raíz, sin nodos intermedios de jerarquía.
Protocolo IDE: argv[1]=fase  argv[2]=archivo  →  stdout=JSON
"""

import sys
import json
import logging

try:
    import ply.lex  as ply_lex
    import ply.yacc as ply_yacc
except ImportError:
    import subprocess as _sp
    try:
        _sp.check_call(
            [sys.executable, "-m", "pip", "install", "ply", "--quiet"],
            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL
        )
        import ply.lex  as ply_lex
        import ply.yacc as ply_yacc
    except Exception as _e:
        print(json.dumps({"errors": [{"tipo": "Sistema", "linea": 0, "col": 0,
            "mensaje": f"PLY no instalado: {_e}", "fatal": True}]}))
        sys.exit(1)

logging.getLogger('ply').setLevel(logging.CRITICAL)
import tempfile

# ══════════════════════════════════════════════════════════════════════════════
#  NODO DEL AST
# ══════════════════════════════════════════════════════════════════════════════
class Node:
    def __init__(self, label, value=None, children=None):
        self.label    = label
        self.value    = value
        self.children = children or []

    def add(self, child):
        if child is not None:
            self.children.append(child)
        return child

    def to_dict(self):
        d = {"label": self.label}
        if self.value is not None:
            d["value"] = str(self.value)
        if self.children:
            d["children"] = [c.to_dict() for c in self.children if c]
        return d

# ── Helpers para construir AST compacto ───────────────────────────────────────
def leaf(label, value):
    """Nodo hoja: solo etiqueta + valor, sin hijos."""
    return Node(label, str(value))

def binop(op, left, right):
    """Nodo binario: operador como raíz, hijos izq/der."""
    n = Node("op", op)
    n.add(left)
    n.add(right)
    return n

def unop(op, operand):
    """Nodo unario: operador como raíz, un hijo."""
    n = Node("op", op)
    n.add(operand)
    return n

# ══════════════════════════════════════════════════════════════════════════════
#  ERROR ESTRUCTURADO
# ══════════════════════════════════════════════════════════════════════════════
def make_error(tipo, linea, col, mensaje, fatal=False):
    return {"tipo": tipo, "linea": linea, "col": col, "mensaje": mensaje, "fatal": fatal}

# ══════════════════════════════════════════════════════════════════════════════
#  ANALIZADOR LÉXICO
# ══════════════════════════════════════════════════════════════════════════════
reserved = {
    'if': 'IF', 'else': 'ELSE', 'then': 'THEN', 'end': 'END',
    'do': 'DO', 'while': 'WHILE', 'until': 'UNTIL',
    'switch': 'SWITCH', 'case': 'CASE',
    'int': 'INT', 'float': 'FLOAT', 'real': 'REAL',
    'main': 'MAIN', 'cin': 'CIN', 'cout': 'COUT',
}

tokens = list(reserved.values()) + [
    'FLOAT_LIT', 'INT_LIT', 'STRING', 'CHAR',
    'ID',
    'INCREMENT', 'DECREMENT', 'AND', 'OR',
    'LEQ', 'GEQ', 'NEQ', 'EQ',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'POW',
    'LT', 'GT', 'NOT', 'ASSIGN',
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    'COMMA', 'SEMICOLON', 'COLON',
]

_lex_errors = []

def make_lexer():
    global _lex_errors
    _lex_errors = []
    t_ignore = ' \t\r'

    def t_newline(t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_COMMENT_MULTI(t):
        r'/\*[\s\S]*?\*/'
        t.lexer.lineno += t.value.count('\n')

    def t_COMMENT_LINE(t):
        r'//[^\n]*'
        pass

    def t_STRING(t):
        r'"[^"\n]*"'
        return t

    def t_CHAR(t):
        r"'[^'\n]'"
        return t

    def t_ERR_NUMBER(t):
        r'\d+\.(?!\d)'
        col = _col(t)
        _lex_errors.append(make_error("LéxicoNumérico", t.lexer.lineno, col,
            f"Número mal formado '{t.value}' — falta parte decimal"))

    def t_FLOAT_LIT(t):
        r'\d+\.\d+'
        t.value = float(t.value)
        return t

    def t_INT_LIT(t):
        r'\d+'
        t.value = int(t.value)
        return t

    def t_INCREMENT(t):
        r'\+\+'
        return t

    def t_DECREMENT(t):
        r'--'
        return t

    def t_AND(t):
        r'&&'
        return t

    def t_OR(t):
        r'\|\|'
        return t

    def t_LEQ(t):
        r'<='
        return t

    def t_GEQ(t):
        r'>='
        return t

    def t_NEQ(t):
        r'!='
        return t

    def t_EQ(t):
        r'=='
        return t

    t_PLUS      = r'\+'
    t_MINUS     = r'-'
    t_TIMES     = r'\*'
    t_DIVIDE    = r'/'
    t_MOD       = r'%'
    t_POW       = r'\^'
    t_LT        = r'<'
    t_GT        = r'>'
    t_NOT       = r'!'
    t_ASSIGN    = r'='
    t_LPAREN    = r'\('
    t_RPAREN    = r'\)'
    t_LBRACE    = r'\{'
    t_RBRACE    = r'\}'
    t_COMMA     = r','
    t_SEMICOLON = r';'
    t_COLON     = r':'

    def t_ID(t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        t.type = reserved.get(t.value, 'ID')
        return t

    def t_error(t):
        col = _col(t)
        _lex_errors.append(make_error("LéxicoCarácter", t.lexer.lineno, col,
            f"Carácter inválido '{t.value[0]}'"))
        t.lexer.skip(1)

    def _col(t):
        last_nl = t.lexer.lexdata.rfind('\n', 0, t.lexpos)
        return t.lexpos - last_nl

    return ply_lex.lex(errorlog=ply_lex.NullLogger(), optimize=False)


def lex_source(source):
    global _lex_errors
    _lex_errors = []
    lexer = make_lexer()
    lexer.input(source)
    tokens_out = []
    for tok in lexer:
        ttype = tok.type
        if ttype in reserved.values(): cat = "KEYWORD"
        elif ttype in ('FLOAT_LIT', 'INT_LIT'): cat = "NUMBER"
        elif ttype in ('INCREMENT','DECREMENT','PLUS','MINUS','TIMES','DIVIDE','MOD','POW'): cat = "ARITH_OP"
        elif ttype in ('LEQ','GEQ','NEQ','EQ','LT','GT'): cat = "RELAT_OP"
        elif ttype in ('AND','OR','NOT'): cat = "LOGIC_OP"
        elif ttype == 'ASSIGN': cat = "ASSIGN"
        elif ttype in ('STRING','CHAR'): cat = "STRING"
        else: cat = "SYMBOL"
        last_nl = lexer.lexdata.rfind('\n', 0, tok.lexpos)
        col = tok.lexpos - last_nl
        tokens_out.append({"token": str(tok.value), "type": ttype, "category": cat,
                           "line": tok.lineno, "col": col})
    return tokens_out, list(_lex_errors)


# ══════════════════════════════════════════════════════════════════════════════
#  ANALIZADOR SINTÁCTICO — AST COMPACTO
#  Principio: operador como raíz, hojas como literales/ID,
#             nodos de control (if/while/do) con hijos directos semánticos.
#  NO hay nodos: expresion_simple, termino, factor, componente, postfijo.
# ══════════════════════════════════════════════════════════════════════════════
_syn_errors      = []
_src_lines       = []
_last_error_node = None


def _syn_col(p, idx=1):
    try:
        pos = p.lexpos(idx)
        last_nl = p.lexer.lexdata.rfind('\n', 0, pos)
        return pos - last_nl
    except Exception:
        return 0


def make_ast_error(tipo, linea, col, mensaje):
    codigo = ""
    try:
        if 0 < linea <= len(_src_lines):
            codigo = _src_lines[linea - 1]
    except Exception:
        pass
    return Node("ERROR", f"{tipo} | L{linea},C{col} | {mensaje}",
                [Node("código", codigo)] if codigo else [])


def _add_syn_error(tipo, linea, col, mensaje, fatal=False):
    global _last_error_node
    _syn_errors.append(make_error(tipo, linea, col, mensaje, fatal))
    _last_error_node = make_ast_error(tipo, linea, col, mensaje)


def make_parser(source_lines):
    global _syn_errors, _src_lines, _last_error_node
    _syn_errors      = []
    _src_lines       = source_lines
    _last_error_node = None

    precedence = (
        ('left',  'OR'),
        ('left',  'AND'),
        ('left',  'EQ', 'NEQ'),
        ('left',  'LT', 'GT', 'LEQ', 'GEQ'),
        ('left',  'PLUS', 'MINUS'),
        ('left',  'TIMES', 'DIVIDE', 'MOD'),
        ('right', 'POW'),
        ('right', 'UMINUS', 'NOT'),
        ('left',  'INCREMENT', 'DECREMENT'),
    )

    # ── programa ──────────────────────────────────────────────────────────
    def p_programa(p):
        '''programa : MAIN LBRACE stmt_list RBRACE'''
        n = Node("programa", "main")
        n.add(p[3])
        p[0] = n

    def p_programa_error(p):
        '''programa : error'''
        _add_syn_error("SintácticoEstructura", p.lineno(1), 0,
            "Estructura incorrecta — se esperaba: main { ... }", fatal=True)
        p[0] = Node("programa", "ERROR")

    # ── stmt_list ─────────────────────────────────────────────────────────
    def p_stmt_list_many(p):
        '''stmt_list : stmt_list stmt'''
        p[1].add(p[2])
        p[0] = p[1]

    def p_stmt_list_empty(p):
        '''stmt_list : empty'''
        p[0] = Node("bloque")

    # ── stmt dispatch ─────────────────────────────────────────────────────
    def p_stmt_decl(p):
        '''stmt : decl_stmt'''
        p[0] = p[1]

    def p_stmt_assign(p):
        '''stmt : assign_stmt'''
        p[0] = p[1]

    def p_stmt_if(p):
        '''stmt : if_stmt'''
        p[0] = p[1]

    def p_stmt_while(p):
        '''stmt : while_stmt'''
        p[0] = p[1]

    def p_stmt_do_while(p):
        '''stmt : do_while_stmt'''
        p[0] = p[1]

    def p_stmt_switch(p):
        '''stmt : switch_stmt'''
        p[0] = p[1]

    def p_stmt_cin(p):
        '''stmt : cin_stmt'''
        p[0] = p[1]

    def p_stmt_cout(p):
        '''stmt : cout_stmt'''
        p[0] = p[1]

    def p_stmt_expr(p):
        '''stmt : expresion SEMICOLON
                | sent_expresion'''
        p[0] = p[1]

    def p_stmt_block(p):
        '''stmt : block'''
        p[0] = p[1]

    def p_stmt_error(p):
        '''stmt : error SEMICOLON'''
        _add_syn_error("SintácticoToken", p.lineno(1), 0,
            "Instrucción mal formada — omitido hasta ';'")
        p[0] = Node("ERROR", "instrucción inválida")

    # ── bloque ────────────────────────────────────────────────────────────
    def p_block(p):
        '''block : LBRACE stmt_list RBRACE'''
        p[0] = p[2]

    def p_block_semi(p):
        '''block : LBRACE stmt_list RBRACE SEMICOLON'''
        p[0] = p[2]

    # ── declaración ───────────────────────────────────────────────────────
    def p_decl_stmt_int(p):
        '''decl_stmt : INT id_list SEMICOLON'''
        n = Node("declarar", "int")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_decl_stmt_float(p):
        '''decl_stmt : FLOAT id_list SEMICOLON'''
        n = Node("declarar", "float")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_decl_stmt_real(p):
        '''decl_stmt : REAL id_list SEMICOLON'''
        n = Node("declarar", "real")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_decl_stmt_error(p):
        '''decl_stmt : INT error SEMICOLON
                     | FLOAT error SEMICOLON
                     | REAL error SEMICOLON'''
        _add_syn_error("SintácticoSímbolo", p.lineno(1), 0,
            f"Declaración '{p[1]}' mal formada")
        p[0] = Node("ERROR", f"declarar {p[1]}")

    def p_id_list_one(p):
        '''id_list : ID'''
        p[0] = [leaf("ID", p[1])]

    def p_id_list_many(p):
        '''id_list : id_list COMMA ID'''
        p[0] = p[1] + [leaf("ID", p[3])]

    # ── asignación: raíz = operador '=' ──────────────────────────────────
    def p_assign_stmt(p):
        '''assign_stmt : ID ASSIGN expresion SEMICOLON'''
        # AST: "=" como raíz, ID izquierda, expresión derecha
        p[0] = binop("=", leaf("ID", p[1]), p[3])

    def p_assign_stmt_nosemi(p):
        '''assign_stmt : ID ASSIGN expresion error'''
        linea = p.lineno(1); col = _syn_col(p, 1)
        msg = f"Falta ';' en asignación a '{p[1]}'"
        _add_syn_error("SintácticoSímbolo", linea, col, msg)
        n = binop("=", leaf("ID", p[1]), p[3])
        n.add(make_ast_error("SintácticoSímbolo", linea, col, msg))
        p[0] = n

    def p_assign_stmt_noexpr(p):
        '''assign_stmt : ID ASSIGN error SEMICOLON'''
        linea = p.lineno(1); col = _syn_col(p, 1)
        msg = f"Expresión inválida en asignación a '{p[1]}'"
        _add_syn_error("SintácticoToken", linea, col, msg)
        p[0] = binop("=", leaf("ID", p[1]), make_ast_error("SintácticoToken", linea, col, msg))

    # ── if ────────────────────────────────────────────────────────────────
    def p_if_simple(p):
        '''if_stmt : IF LPAREN expresion RPAREN block'''
        n = Node("if")
        n.add(Node("condición", children=[p[3]]))
        n.add(Node("entonces",  children=[p[5]]))
        p[0] = n

    def p_if_else(p):
        '''if_stmt : IF LPAREN expresion RPAREN block ELSE block'''
        n = Node("if")
        n.add(Node("condición", children=[p[3]]))
        n.add(Node("entonces",  children=[p[5]]))
        n.add(Node("sino",      children=[p[7]]))
        p[0] = n

    def p_if_then_end(p):
        '''if_stmt : IF LPAREN expresion RPAREN THEN stmt_list END SEMICOLON'''
        n = Node("if")
        n.add(Node("condición", children=[p[3]]))
        n.add(Node("entonces",  children=[p[6]]))
        p[0] = n

    def p_if_then_else_end(p):
        '''if_stmt : IF LPAREN expresion RPAREN THEN stmt_list ELSE stmt_list END SEMICOLON'''
        n = Node("if")
        n.add(Node("condición", children=[p[3]]))
        n.add(Node("entonces",  children=[p[6]]))
        n.add(Node("sino",      children=[p[8]]))
        p[0] = n

    def p_if_error_cond(p):
        '''if_stmt : IF LPAREN error RPAREN block'''
        linea = p.lineno(1); col = _syn_col(p, 1)
        msg = "Condición inválida en 'if'"
        _add_syn_error("SintácticoToken", linea, col, msg)
        n = Node("if")
        n.add(Node("condición", children=[make_ast_error("SintácticoToken", linea, col, msg)]))
        n.add(Node("entonces",  children=[p[5]]))
        p[0] = n

    def p_if_error_body(p):
        '''if_stmt : IF LPAREN expresion RPAREN error'''
        linea = p.lineno(1)
        msg = "Cuerpo de 'if' mal formado — se esperaba '{'"
        _add_syn_error("SintácticoEstructura", linea, 0, msg)
        n = Node("if")
        n.add(Node("condición", children=[p[3]]))
        n.add(make_ast_error("SintácticoEstructura", linea, 0, msg))
        p[0] = n

    # ── while ─────────────────────────────────────────────────────────────
    def p_while_stmt(p):
        '''while_stmt : WHILE LPAREN expresion RPAREN block'''
        n = Node("while")
        n.add(Node("condición", children=[p[3]]))
        n.add(Node("cuerpo",    children=[p[5]]))
        p[0] = n

    def p_while_error_cond(p):
        '''while_stmt : WHILE LPAREN error RPAREN block'''
        linea = p.lineno(1); col = _syn_col(p, 1)
        msg = "Condición inválida en 'while'"
        _add_syn_error("SintácticoToken", linea, col, msg)
        n = Node("while")
        n.add(Node("condición", children=[make_ast_error("SintácticoToken", linea, col, msg)]))
        n.add(Node("cuerpo",    children=[p[5]]))
        p[0] = n

    def p_while_error_rparen(p):
        '''while_stmt : WHILE LPAREN expresion error block'''
        _add_syn_error("SintácticoSímbolo", p.lineno(1), 0, "Falta ')' en 'while'")
        n = Node("while")
        n.add(Node("condición", children=[p[3]]))
        n.add(Node("cuerpo",    children=[p[5]]))
        p[0] = n

    # ── do-while ──────────────────────────────────────────────────────────
    def p_do_while(p):
        '''do_while_stmt : DO block WHILE LPAREN expresion RPAREN SEMICOLON'''
        n = Node("do-while")
        n.add(Node("cuerpo",    children=[p[2]]))
        n.add(Node("condición", children=[p[5]]))
        p[0] = n

    def p_do_while_stmts(p):
        '''do_while_stmt : DO stmt_list WHILE LPAREN expresion RPAREN SEMICOLON'''
        n = Node("do-while")
        n.add(Node("cuerpo",    children=[p[2]]))
        n.add(Node("condición", children=[p[5]]))
        p[0] = n

    def p_do_until(p):
        '''do_while_stmt : DO block UNTIL LPAREN expresion RPAREN SEMICOLON'''
        n = Node("do-until")
        n.add(Node("cuerpo",    children=[p[2]]))
        n.add(Node("condición", children=[p[5]]))
        p[0] = n

    def p_do_until_stmts(p):
        '''do_while_stmt : DO stmt_list UNTIL LPAREN expresion RPAREN SEMICOLON'''
        n = Node("do-until")
        n.add(Node("cuerpo",    children=[p[2]]))
        n.add(Node("condición", children=[p[5]]))
        p[0] = n

    def p_do_error_closing(p):
        '''do_while_stmt : DO block error SEMICOLON'''
        _add_syn_error("SintácticoEstructura", p.lineno(3), 0,
            "Falta 'while(...)' o 'until(...)' para cerrar 'do'")
        n = Node("do-while")
        n.add(Node("cuerpo", children=[p[2]]))
        p[0] = n

    # ── switch ────────────────────────────────────────────────────────────
    def p_switch_stmt(p):
        '''switch_stmt : SWITCH LPAREN expresion RPAREN LBRACE case_list RBRACE'''
        n = Node("switch")
        n.add(Node("expr",  children=[p[3]]))
        n.add(p[6])
        p[0] = n

    def p_case_list_many(p):
        '''case_list : case_list case_clause'''
        p[1].add(p[2]); p[0] = p[1]

    def p_case_list_empty(p):
        '''case_list : empty'''
        p[0] = Node("casos")

    def p_case_clause_int(p):
        '''case_clause : CASE INT_LIT COLON stmt_list'''
        n = Node("case", str(p[2])); n.add(p[4]); p[0] = n

    def p_case_clause_float(p):
        '''case_clause : CASE FLOAT_LIT COLON stmt_list'''
        n = Node("case", str(p[2])); n.add(p[4]); p[0] = n

    def p_case_clause_id(p):
        '''case_clause : CASE ID COLON stmt_list'''
        n = Node("case", p[2]); n.add(p[4]); p[0] = n

    def p_case_clause_error(p):
        '''case_clause : CASE error COLON stmt_list'''
        _add_syn_error("SintácticoToken", p.lineno(1), 0,
            "Valor inválido en 'case'")
        n = Node("case", "ERROR"); n.add(p[4]); p[0] = n

    # ── cin / cout ────────────────────────────────────────────────────────
    def p_cin_stmt(p):
        '''cin_stmt : CIN id_list SEMICOLON'''
        n = Node("cin")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_cout_stmt(p):
        '''cout_stmt : COUT expr_list SEMICOLON'''
        n = Node("cout")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_cin_error_semi(p):
        '''cin_stmt : CIN id_list error'''
        _add_syn_error("SintácticoSímbolo", p.lineno(1), 0, "Falta ';' en 'cin'")
        n = Node("cin")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_cout_error_semi(p):
        '''cout_stmt : COUT expr_list error'''
        _add_syn_error("SintácticoSímbolo", p.lineno(1), 0, "Falta ';' en 'cout'")
        n = Node("cout")
        for c in p[2]: n.add(c)
        p[0] = n

    def p_expr_list_one(p):
        '''expr_list : expresion'''
        p[0] = [p[1]]

    def p_expr_list_many(p):
        '''expr_list : expr_list COMMA expresion'''
        p[0] = p[1] + [p[3]]

    # ══════════════════════════════════════════════════════════════════════
    #  EXPRESIONES — AST COMPACTO
    #  Cada operador binario/unario ES el nodo raíz directamente.
    #  No hay nodos intermedios de jerarquía.
    # ══════════════════════════════════════════════════════════════════════

    # sent_expresion (expr standalone con ;)
    def p_sent_expresion(p):
        '''sent_expresion : expresion SEMICOLON'''
        p[0] = p[1]

    # ── Lógicos ───────────────────────────────────────────────────────────
    def p_expr_or(p):
        '''expresion : expresion OR expresion'''
        p[0] = binop("||", p[1], p[3])

    def p_expr_and(p):
        '''expresion : expresion AND expresion'''
        p[0] = binop("&&", p[1], p[3])

    # ── Relacionales ──────────────────────────────────────────────────────
    def p_expr_eq(p):
        '''expresion : expresion EQ expresion'''
        p[0] = binop("==", p[1], p[3])

    def p_expr_neq(p):
        '''expresion : expresion NEQ expresion'''
        p[0] = binop("!=", p[1], p[3])

    def p_expr_lt(p):
        '''expresion : expresion LT expresion'''
        p[0] = binop("<", p[1], p[3])

    def p_expr_gt(p):
        '''expresion : expresion GT expresion'''
        p[0] = binop(">", p[1], p[3])

    def p_expr_leq(p):
        '''expresion : expresion LEQ expresion'''
        p[0] = binop("<=", p[1], p[3])

    def p_expr_geq(p):
        '''expresion : expresion GEQ expresion'''
        p[0] = binop(">=", p[1], p[3])

    # ── Aritméticos ───────────────────────────────────────────────────────
    def p_expr_plus(p):
        '''expresion : expresion PLUS expresion'''
        p[0] = binop("+", p[1], p[3])

    def p_expr_minus(p):
        '''expresion : expresion MINUS expresion'''
        p[0] = binop("-", p[1], p[3])

    def p_expr_times(p):
        '''expresion : expresion TIMES expresion'''
        p[0] = binop("*", p[1], p[3])

    def p_expr_divide(p):
        '''expresion : expresion DIVIDE expresion'''
        p[0] = binop("/", p[1], p[3])

    def p_expr_mod(p):
        '''expresion : expresion MOD expresion'''
        p[0] = binop("%", p[1], p[3])

    def p_expr_pow(p):
        '''expresion : expresion POW expresion'''
        p[0] = binop("^", p[1], p[3])

    # ── Unarios ───────────────────────────────────────────────────────────
    def p_expr_uminus(p):
        '''expresion : MINUS expresion %prec UMINUS'''
        p[0] = unop("-u", p[2])

    def p_expr_not(p):
        '''expresion : NOT expresion'''
        p[0] = unop("!", p[2])

    # ── Postfijos ─────────────────────────────────────────────────────────
    def p_expr_incr(p):
        '''expresion : expresion INCREMENT'''
        p[0] = unop("++", p[1])

    def p_expr_decr(p):
        '''expresion : expresion DECREMENT'''
        p[0] = unop("--", p[1])

    # ── Primarios ─────────────────────────────────────────────────────────
    def p_expr_int(p):
        '''expresion : INT_LIT'''
        p[0] = leaf("INT", str(p[1]))

    def p_expr_float(p):
        '''expresion : FLOAT_LIT'''
        p[0] = leaf("REAL", str(p[1]))

    def p_expr_string(p):
        '''expresion : STRING'''
        p[0] = leaf("STR", p[1])

    def p_expr_char(p):
        '''expresion : CHAR'''
        p[0] = leaf("CHAR", p[1])

    def p_expr_id(p):
        '''expresion : ID'''
        p[0] = leaf("ID", p[1])

    def p_expr_grupo(p):
        '''expresion : LPAREN expresion RPAREN'''
        p[0] = p[2]  # transparente: el grupo no agrega nodo

    # Recuperación: paréntesis sin cerrar
    def p_expr_grupo_error(p):
        '''expresion : LPAREN expresion error'''
        linea = p.lineno(1); col = _syn_col(p, 1)
        msg = "Falta ')' para cerrar expresión"
        _add_syn_error("SintácticoSímbolo", linea, col, msg)
        p[0] = p[2]

    # Recuperación: operador sin operando derecho
    def p_expr_binop_error(p):
        '''expresion : expresion PLUS error
                     | expresion MINUS error
                     | expresion TIMES error
                     | expresion DIVIDE error
                     | expresion MOD error'''
        linea = p.lineno(2); col = _syn_col(p, 2); op = p[2]
        _add_syn_error("SintácticoToken", linea, col,
            f"Operador '{op}' sin operando derecho")
        p[0] = unop(op + "?", p[1])

    # ── vacío ─────────────────────────────────────────────────────────────
    def p_empty(p):
        '''empty :'''
        p[0] = None

    # ── error genérico ────────────────────────────────────────────────────
    TOKEN_HUMAN = {
        'SEMICOLON':'\';\'' ,'COLON'   :'\':\'' ,'COMMA'    :'\'\'',
        'LPAREN'   :'\'(\'' ,'RPAREN'  :'\')\'' ,'LBRACE'   :'\'{\'' ,
        'RBRACE'   :'\'}\'' ,'ASSIGN'  :'\'=\'' ,'EQ'       :'\'==\'',
        'NEQ'      :'\'!=\'','LT'      :'\'<\'' ,'GT'       :'\'>\'',
        'LEQ'      :'\'<=\'','GEQ'     :'\'>= \'','PLUS'    :'\'+\'',
        'MINUS'    :'\'-\'' ,'TIMES'   :'\'*\'' ,'DIVIDE'   :'\'/\'',
        'MOD'      :'\'%\'' ,'POW'     :'\'^\'' ,'AND'      :'\'&&\'',
        'OR'       :'\'||\'','NOT'     :'\'!\'' ,'INCREMENT':'\'++\'',
        'DECREMENT':'\'--\'','ID'      :'identificador',
        'INT_LIT'  :'número entero','FLOAT_LIT':'número decimal',
        'STRING'   :'cadena','CHAR':'carácter',
        'INT':'\'int\'','FLOAT':'\'float\'','REAL':'\'real\'','MAIN':'\'main\'',
        'IF':'\'if\'','ELSE':'\'else\'','THEN':'\'then\'','END':'\'end\'',
        'WHILE':'\'while\'','DO':'\'do\'','UNTIL':'\'until\'',
        'SWITCH':'\'switch\'','CASE':'\'case\'','CIN':'\'cin\'','COUT':'\'cout\'',
        '$end':'fin de archivo',
    }

    _EXPR_STARTERS = {'ID','INT_LIT','FLOAT_LIT','STRING','CHAR',
                      'LPAREN','MINUS','NOT','INCREMENT','DECREMENT'}

    def _expected_tokens(state):
        try:
            return set(parser.action[state].keys())
        except Exception:
            return set()

    def _build_error_msg(found_tok, found_val, expected):
        expected = {t for t in expected if t != 'error'}
        found_human = TOKEN_HUMAN.get(found_tok, f"'{found_val}'")
        ctx_exact = {
            frozenset(['SEMICOLON'])         : "falta ';' al final de la instrucción",
            frozenset(['RPAREN'])            : "falta ')' para cerrar el paréntesis",
            frozenset(['RBRACE'])            : "falta '}' para cerrar el bloque",
            frozenset(['RPAREN','SEMICOLON']): "falta ')' o ';'",
            frozenset(['LBRACE'])            : "falta '{' para abrir el bloque",
            frozenset(['THEN','LBRACE'])     : "falta 'then' o '{' tras la condición",
            frozenset(['WHILE','UNTIL'])     : "falta 'while(...)' o 'until(...)' para cerrar 'do'",
            frozenset(['LPAREN'])            : "falta '(' para abrir la condición",
            frozenset(['COLON'])             : "falta ':' en 'case'",
            frozenset(['ASSIGN'])            : "falta '=' en la asignación",
            frozenset(['END'])               : "falta 'end' para cerrar 'if/then'",
            frozenset(['END','ELSE'])        : "falta 'else' o 'end' para cerrar 'if/then'",
        }
        hint = ctx_exact.get(frozenset(expected))
        if hint:
            return f"{hint} — se encontró {found_human}"
        if _EXPR_STARTERS.issubset(expected) or len(_EXPR_STARTERS & expected) >= 4:
            if found_tok in ('SEMICOLON', 'RPAREN', 'RBRACE'):
                return f"falta expresión antes de {found_human}"
            return f"se esperaba expresión, se encontró {found_human}"
        if found_tok in ('SEMICOLON','RBRACE') and expected & {'RPAREN'}:
            return "instrucción incompleta — falta cerrar paréntesis"
        if expected:
            filtered = {t for t in expected if t != '$end'}
            exp_human = sorted(TOKEN_HUMAN.get(t, f"'{t}'") for t in filtered)[:5]
            return f"se encontró {found_human} pero se esperaba: {', '.join(exp_human)}"
        return f"token inesperado {found_human}"

    def p_error(p):
        global _last_error_node
        if p:
            last_nl = p.lexer.lexdata.rfind('\n', 0, p.lexpos)
            col = p.lexpos - last_nl
            try:
                cur_state = parser.statestack[-1]
                expected  = _expected_tokens(cur_state)
            except Exception:
                cur_state = -1; expected = set()
            msg = _build_error_msg(p.type, p.value, expected)
            _add_syn_error("SintácticoToken", p.lineno, col, msg)
            parser.errok()
        else:
            _add_syn_error("SintácticoEOF", 0, 0,
                "Fin de archivo inesperado — programa incompleto", fatal=True)

    parser = ply_yacc.yacc(
        debug=False, write_tables=False,
        outputdir=tempfile.gettempdir(),
        errorlog=ply_yacc.NullLogger(),
    )
    return parser


def parse_source(source):
    global _syn_errors
    _syn_errors = []
    lines  = source.splitlines()
    lexer  = make_lexer()
    parser = make_parser(lines)
    tree   = parser.parse(source, lexer=lexer, tracking=True)
    return tree, list(_syn_errors)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    phase, srcfile = sys.argv[1], sys.argv[2]
    try:
        with open(srcfile, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(json.dumps({"errors": [make_error("Sistema", 0, 0,
            f"Archivo no encontrado: {srcfile}", fatal=True)]}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"errors": [make_error("Sistema", 0, 0, str(e), fatal=True)]}))
        sys.exit(1)

    try:
        if phase == "lexical":
            tokens, errors = lex_source(source)
            print(json.dumps({"tokens": tokens, "errors": errors}, ensure_ascii=False))
            sys.exit(0 if not errors else 1)

        elif phase == "syntactic":
            _, lex_errors = lex_source(source)
            import re as _re
            clean = source
            clean = _re.sub(r'(\d+)\.(?!\d)', r'\1', clean)
            bad_chars = set()
            for e in lex_errors:
                if e["tipo"] == "LéxicoCarácter":
                    m = _re.search(r"'(.)'", e["mensaje"])
                    if m: bad_chars.add(m.group(1))
            for ch in bad_chars:
                clean = clean.replace(ch, ' ')
            lex_prev = [make_error("LéxicoPrevio", e["linea"], e["col"],
                f"{e['mensaje']} — ignorado para continuar") for e in lex_errors]
            tree, syn_errors = parse_source(clean)
            all_errors = lex_prev + syn_errors
            print(json.dumps({
                "tree":       tree.to_dict() if tree else None,
                "errors":     all_errors,
                "lex_errors": lex_prev,
                "syn_errors": syn_errors,
            }, ensure_ascii=False))
            sys.exit(0 if not all_errors else 1)

        else:
            print(json.dumps({"errors": [
                make_error("Sistema", 0, 0, f"Fase '{phase}' no implementada", fatal=True)
            ]}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"errors": [
            make_error("Sistema", 0, 0, f"Error interno: {e}", fatal=True)
        ]}))
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Analisador Sintático (Parser) para a linguagem JSS.

Gramática (descendente recursivo — EBNF):
  program         → top_decl* EOF
  top_decl        → function_decl | class_decl | var_decl | const_decl
  function_decl   → "function" type IDENT "(" params? ")" block
  class_decl      → "class" IDENT "{" class_member* "}"
  class_member    → constructor_decl | method_decl | attr_decl
  constructor_decl→ IDENT "constructor" "(" params? ")" block
  method_decl     → type IDENT "(" params? ")" block
  attr_decl       → type IDENT ";"
  params          → param ("," param)*
  param           → type IDENT
  type            → "int" | "real" | "str" | "bool" | "void"
  block           → "{" statement* "}"
  statement       → var_decl | const_decl | return_stmt | if_stmt
                  | while_stmt | for_stmt | break_stmt | expr_stmt
  var_decl        → "let" type ("[" INT_LIT "]")? declarator ("," declarator)* ";"
  declarator      → IDENT ("=" expr)?
  const_decl      → "const" type IDENT "=" expr ";"
  return_stmt     → "return" expr? ";"
  if_stmt         → "if" "(" expr ")" block ("else" (if_stmt | block))?
  while_stmt      → "while" "(" expr ")" block
  for_stmt        → "for" "(" expr? ";" expr? ";" expr? ")" block
  break_stmt      → "break" ";"
  expr_stmt       → expr ";"

  Precedência (1 = mais alta, conforme especificação):
  1  unary:   ! + - ++ --        (prefixo)
  2  power:   **                 (right-assoc)
  3  mult:    * / %
  4  add:     + -
  5  cmp:     > >= < <= == !=
  6  and:     &&
  7  or:      ||
  8  assign:  = += -= *= /= %=   (right-assoc, mais baixa)

  postfix (maior que qualquer op): [ ] ( ) .
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from lexer import TT, Token


# ---------------------------------------------------------------------------
# Nós da AST
# ---------------------------------------------------------------------------

@dataclass
class Param:
    type: str
    name: str


# --- Declarações de topo ---

@dataclass
class Program:
    decls: list   # list[FunctionDecl | ClassDecl | VarDecl | ConstDecl]


@dataclass
class FunctionDecl:
    return_type: str
    name: str
    params: list[Param]
    body: "Block"
    line: int


@dataclass
class ClassDecl:
    name: str
    attrs: list          # list[VarDecl]
    constructor: object  # Optional[ConstructorDecl]
    methods: list        # list[MethodDecl]
    line: int


@dataclass
class ConstructorDecl:
    class_name: str
    params: list[Param]
    body: "Block"
    line: int


@dataclass
class MethodDecl:
    return_type: str
    name: str
    params: list[Param]
    body: "Block"
    line: int


# --- Statements ---

@dataclass
class Block:
    stmts: list


@dataclass
class VarDecl:
    type: str
    array_size: Optional[int]
    name: str
    init: object   # Optional[Expr]
    line: int


@dataclass
class ConstDecl:
    type: str
    name: str
    init: object   # Expr
    line: int


@dataclass
class ReturnStmt:
    value: object  # Optional[Expr]
    line: int


@dataclass
class IfStmt:
    condition: object
    then_block: "Block"
    else_clause: object  # Block | IfStmt | None
    line: int


@dataclass
class WhileStmt:
    condition: object
    body: "Block"
    line: int


@dataclass
class ForStmt:
    init: object       # Optional[Expr]
    condition: object  # Optional[Expr]
    update: object     # Optional[Expr]
    body: "Block"
    line: int


@dataclass
class BreakStmt:
    line: int


@dataclass
class ExprStmt:
    expr: object
    line: int


# --- Expressões ---

@dataclass
class Assign:
    target: object  # Ident | Subscript | Attr
    op: str
    value: object
    line: int


@dataclass
class BinOp:
    op: str
    left: object
    right: object
    line: int


@dataclass
class UnaryOp:
    op: str       # !, -, +, ++, -- (todos prefixo)
    operand: object
    line: int


@dataclass
class Call:
    callee: object
    args: list
    line: int


@dataclass
class Subscript:
    obj: object
    index: object
    line: int


@dataclass
class Attr:
    obj: object
    name: str
    line: int


@dataclass
class ArrayLit:
    elements: list
    line: int


@dataclass
class Cast:
    type: str
    expr: object
    line: int


@dataclass
class NewExpr:
    class_name: str
    args: list
    line: int


@dataclass
class Ident:
    name: str
    line: int


@dataclass
class IntLit:
    value: int
    line: int


@dataclass
class RealLit:
    value: float
    line: int


@dataclass
class StrLit:
    value: str
    line: int


@dataclass
class BoolLit:
    value: bool
    line: int


@dataclass
class NullLit:
    line: int


# ---------------------------------------------------------------------------
# Erro sintático
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f"Erro sintático na linha {line}: {msg}")
        self.line = line


# ---------------------------------------------------------------------------
# Conjuntos auxiliares
# ---------------------------------------------------------------------------

_TYPE_TOKENS = frozenset({TT.INT, TT.REAL, TT.STR, TT.BOOL, TT.VOID})

_ASSIGN_OPS = frozenset({
    TT.ASSIGN, TT.PLUS_ASSIGN, TT.MINUS_ASSIGN,
    TT.STAR_ASSIGN, TT.SLASH_ASSIGN, TT.PERCENT_ASSIGN,
})

_CMP_OPS = frozenset({TT.LT, TT.LTE, TT.GT, TT.GTE, TT.EQ, TT.NEQ})


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """
    Analisador sintático descendente recursivo para JSS.

    Uso:
        ast = Parser(tokens).parse()   # tokens de Lexer.tokenize()
    """

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    # ── helpers ─────────────────────────────────────────────────────────────

    def _peek(self, offset: int = 0) -> Token:
        idx = min(self._pos + offset, len(self._tokens) - 1)
        return self._tokens[idx]

    def _peek_type(self, offset: int = 0) -> TT:
        return self._peek(offset).type

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != TT.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TT) -> bool:
        return self._peek_type() in types

    def _match(self, *types: TT) -> Optional[Token]:
        if self._peek_type() in types:
            return self._advance()
        return None

    def _expect(self, tt: TT, label: str = "") -> Token:
        if self._peek_type() == tt:
            return self._advance()
        tok = self._peek()
        want = label or tt.name
        raise ParseError(f"esperado '{want}', encontrado {tok.value!r}", tok.line)

    # ── programa ─────────────────────────────────────────────────────────────

    def parse(self) -> Program:
        decls = []
        while not self._check(TT.EOF):
            decls.extend(self._top_decl())
        self._expect(TT.EOF, "EOF")
        return Program(decls)

    def _top_decl(self) -> list:
        tt = self._peek_type()
        if tt == TT.FUNCTION:
            return [self._function_decl()]
        if tt == TT.CLASS:
            return [self._class_decl()]
        if tt == TT.LET:
            return self._var_decl()
        if tt == TT.CONST:
            return [self._const_decl()]
        tok = self._peek()
        raise ParseError(f"declaração inesperada: {tok.value!r}", tok.line)

    # ── funções ───────────────────────────────────────────────────────────────

    def _function_decl(self) -> FunctionDecl:
        tok = self._advance()   # consume 'function'
        ret_type = self._type()
        name_tok = self._expect(TT.IDENT, "nome da função")
        self._expect(TT.LPAREN, "(")
        params = self._params()
        self._expect(TT.RPAREN, ")")
        body = self._block()
        return FunctionDecl(ret_type, name_tok.value, params, body, tok.line)

    def _type(self) -> str:
        tok = self._peek()
        if tok.type in _TYPE_TOKENS:
            self._advance()
            return tok.value
        raise ParseError(
            f"esperado tipo (int, real, str, bool, void), encontrado {tok.value!r}",
            tok.line,
        )

    def _params(self) -> list[Param]:
        if self._check(TT.RPAREN):
            return []
        params = [self._param()]
        while self._match(TT.COMMA):
            params.append(self._param())
        return params

    def _param(self) -> Param:
        type_ = self._type()
        name_tok = self._expect(TT.IDENT, "nome do parâmetro")
        return Param(type_, name_tok.value)

    # ── classes ───────────────────────────────────────────────────────────────

    def _class_decl(self) -> ClassDecl:
        tok = self._advance()   # consume 'class'
        name_tok = self._expect(TT.IDENT, "nome da classe")
        self._expect(TT.LBRACE, "{")

        attrs: list[VarDecl] = []
        constructor = None
        methods: list[MethodDecl] = []

        while not self._check(TT.RBRACE, TT.EOF):
            p0 = self._peek(0)
            p1 = self._peek(1)

            # Constructor: ClassName constructor(params) block
            if (p0.type == TT.IDENT
                    and p1.type == TT.IDENT
                    and p1.value == "constructor"):
                constructor = self._constructor_decl()

            # Attribute ou Method: type IDENT ; | type IDENT (
            elif p0.type in _TYPE_TOKENS:
                type_ = self._type()
                member_name_tok = self._expect(TT.IDENT, "nome do membro")
                if self._check(TT.LPAREN):
                    # Método
                    self._expect(TT.LPAREN, "(")
                    mparams = self._params()
                    self._expect(TT.RPAREN, ")")
                    body = self._block()
                    methods.append(MethodDecl(type_, member_name_tok.value, mparams, body, member_name_tok.line))
                else:
                    # Atributo
                    self._expect(TT.SEMICOLON, ";")
                    attrs.append(VarDecl(type_, None, member_name_tok.value, None, member_name_tok.line))

            else:
                raise ParseError(f"membro de classe inesperado: {p0.value!r}", p0.line)

        self._expect(TT.RBRACE, "}")
        return ClassDecl(name_tok.value, attrs, constructor, methods, tok.line)

    def _constructor_decl(self) -> ConstructorDecl:
        class_name_tok = self._advance()  # IDENT (nome da classe)
        self._advance()                   # IDENT "constructor"
        self._expect(TT.LPAREN, "(")
        params = self._params()
        self._expect(TT.RPAREN, ")")
        body = self._block()
        return ConstructorDecl(class_name_tok.value, params, body, class_name_tok.line)

    # ── bloco e statements ───────────────────────────────────────────────────

    def _block(self) -> Block:
        self._expect(TT.LBRACE, "{")
        stmts = []
        while not self._check(TT.RBRACE, TT.EOF):
            for s in self._statement():
                stmts.append(s)
        self._expect(TT.RBRACE, "}")
        return Block(stmts)

    def _statement(self) -> list:
        tt = self._peek_type()
        if tt == TT.LET:    return self._var_decl()
        if tt == TT.CONST:  return [self._const_decl()]
        if tt == TT.RETURN: return [self._return_stmt()]
        if tt == TT.IF:     return [self._if_stmt()]
        if tt == TT.WHILE:  return [self._while_stmt()]
        if tt == TT.FOR:    return [self._for_stmt()]
        if tt == TT.BREAK:
            tok = self._advance()
            self._expect(TT.SEMICOLON, ";")
            return [BreakStmt(tok.line)]
        return [self._expr_stmt()]

    def _var_decl(self) -> list[VarDecl]:
        tok = self._advance()   # consume 'let'
        type_ = self._type()

        # Dimensão de array: let int[3] arr
        array_size = None
        if self._match(TT.LBRACKET):
            size_tok = self._expect(TT.INT_LIT, "tamanho do array")
            array_size = size_tok.value
            self._expect(TT.RBRACKET, "]")

        # Primeiro declarador
        decls = [self._declarator(type_, array_size, tok.line)]

        # Declaradores adicionais: let int a, b, c;
        while self._match(TT.COMMA):
            decls.append(self._declarator(type_, array_size, self._peek().line))

        self._expect(TT.SEMICOLON, ";")
        return decls

    def _declarator(self, type_: str, array_size: Optional[int], line: int) -> VarDecl:
        name_tok = self._expect(TT.IDENT, "nome da variável")
        init = None
        if self._match(TT.ASSIGN):
            init = self._expr()
        return VarDecl(type_, array_size, name_tok.value, init, line)

    def _const_decl(self) -> ConstDecl:
        tok = self._advance()   # consume 'const'
        type_ = self._type()
        name_tok = self._expect(TT.IDENT, "nome da constante")
        self._expect(TT.ASSIGN, "=")
        init = self._expr()
        self._expect(TT.SEMICOLON, ";")
        return ConstDecl(type_, name_tok.value, init, tok.line)

    def _return_stmt(self) -> ReturnStmt:
        tok = self._advance()   # consume 'return'
        value = None
        if not self._check(TT.SEMICOLON):
            value = self._expr()
        self._expect(TT.SEMICOLON, ";")
        return ReturnStmt(value, tok.line)

    def _if_stmt(self) -> IfStmt:
        tok = self._advance()   # consume 'if'
        self._expect(TT.LPAREN, "(")
        cond = self._expr()
        self._expect(TT.RPAREN, ")")
        then_b = self._block()
        else_clause = None
        if self._match(TT.ELSE):
            # else if: encadeia direto sem bloco extra
            if self._check(TT.IF):
                else_clause = self._if_stmt()
            else:
                else_clause = self._block()
        return IfStmt(cond, then_b, else_clause, tok.line)

    def _while_stmt(self) -> WhileStmt:
        tok = self._advance()   # consume 'while'
        self._expect(TT.LPAREN, "(")
        cond = self._expr()
        self._expect(TT.RPAREN, ")")
        body = self._block()
        return WhileStmt(cond, body, tok.line)

    def _for_stmt(self) -> ForStmt:
        tok = self._advance()   # consume 'for'
        self._expect(TT.LPAREN, "(")

        init = None if self._check(TT.SEMICOLON) else self._expr()
        self._expect(TT.SEMICOLON, ";")

        condition = None if self._check(TT.SEMICOLON) else self._expr()
        self._expect(TT.SEMICOLON, ";")

        update = None if self._check(TT.RPAREN) else self._expr()
        self._expect(TT.RPAREN, ")")

        body = self._block()
        return ForStmt(init, condition, update, body, tok.line)

    def _expr_stmt(self) -> ExprStmt:
        tok = self._peek()
        expr = self._expr()
        self._expect(TT.SEMICOLON, ";")
        return ExprStmt(expr, tok.line)

    # ── expressões (precedência crescente de baixo para cima) ───────────────

    def _expr(self):
        return self._assignment()

    def _assignment(self):
        left = self._or()
        tok = self._peek()
        if tok.type in _ASSIGN_OPS:
            if not isinstance(left, (Ident, Subscript, Attr)):
                raise ParseError("alvo de atribuição inválido", tok.line)
            op = self._advance().value
            right = self._assignment()   # right-assoc
            return Assign(left, op, right, tok.line)
        return left

    def _or(self):
        left = self._and()
        while self._check(TT.OR):
            op_tok = self._advance()
            left = BinOp("||", left, self._and(), op_tok.line)
        return left

    def _and(self):
        left = self._comparison()
        while self._check(TT.AND):
            op_tok = self._advance()
            left = BinOp("&&", left, self._comparison(), op_tok.line)
        return left

    def _comparison(self):
        # Nível 5: >, >=, <, <=, ==, != — mesma precedência (left-assoc)
        left = self._additive()
        while self._peek_type() in _CMP_OPS:
            op_tok = self._advance()
            left = BinOp(op_tok.value, left, self._additive(), op_tok.line)
        return left

    def _additive(self):
        left = self._multiplicative()
        while self._check(TT.PLUS, TT.MINUS):
            op_tok = self._advance()
            left = BinOp(op_tok.value, left, self._multiplicative(), op_tok.line)
        return left

    def _multiplicative(self):
        left = self._power()
        while self._check(TT.STAR, TT.SLASH, TT.PERCENT):
            op_tok = self._advance()
            left = BinOp(op_tok.value, left, self._power(), op_tok.line)
        return left

    def _power(self):
        base = self._unary()
        if self._check(TT.POWER):
            op_tok = self._advance()
            return BinOp("**", base, self._power(), op_tok.line)   # right-assoc
        return base

    def _unary(self):
        # Nível 1: !, +, -, ++, -- (todos PREFIXO conforme especificação)
        tok = self._peek()
        if tok.type in (TT.BANG, TT.MINUS, TT.PLUS, TT.INC, TT.DEC):
            self._advance()
            return UnaryOp(tok.value, self._unary(), tok.line)
        return self._postfix()

    def _postfix(self):
        expr = self._primary()
        while True:
            tok = self._peek()
            if tok.type == TT.LBRACKET:
                self._advance()
                idx = self._expr()
                self._expect(TT.RBRACKET, "]")
                expr = Subscript(expr, idx, tok.line)
            elif tok.type == TT.LPAREN:
                self._advance()
                args = self._args()
                self._expect(TT.RPAREN, ")")
                expr = Call(expr, args, tok.line)
            elif tok.type == TT.DOT:
                self._advance()
                attr_tok = self._expect(TT.IDENT, "nome do membro")
                expr = Attr(expr, attr_tok.value, tok.line)
            else:
                break
        return expr

    def _args(self) -> list:
        if self._check(TT.RPAREN):
            return []
        args = [self._expr()]
        while self._match(TT.COMMA):
            args.append(self._expr())
        return args

    def _primary(self):
        tok = self._peek()

        if tok.type == TT.INT_LIT:
            return IntLit(self._advance().value, tok.line)
        if tok.type == TT.REAL_LIT:
            return RealLit(self._advance().value, tok.line)
        if tok.type == TT.STR_LIT:
            return StrLit(self._advance().value, tok.line)
        if tok.type == TT.BOOL_LIT:
            return BoolLit(self._advance().value, tok.line)
        if tok.type == TT.NULL:
            self._advance()
            return NullLit(tok.line)
        if tok.type in (TT.IDENT, TT.THIS):
            return Ident(self._advance().value, tok.line)

        # new ClassName(args)
        if tok.type == TT.NEW:
            self._advance()
            name_tok = self._expect(TT.IDENT, "nome da classe")
            self._expect(TT.LPAREN, "(")
            args = self._args()
            self._expect(TT.RPAREN, ")")
            return NewExpr(name_tok.value, args, tok.line)

        # cast: int(expr), real(expr), str(expr), bool(expr)
        if tok.type in (TT.INT, TT.REAL, TT.STR, TT.BOOL):
            type_name = self._advance().value
            self._expect(TT.LPAREN, "(")
            inner = self._expr()
            self._expect(TT.RPAREN, ")")
            return Cast(type_name, inner, tok.line)

        # agrupamento: (expr)
        if tok.type == TT.LPAREN:
            self._advance()
            inner = self._expr()
            self._expect(TT.RPAREN, ")")
            return inner

        # array literal: [expr, ...]
        if tok.type == TT.LBRACKET:
            self._advance()
            elements = []
            if not self._check(TT.RBRACKET):
                elements.append(self._expr())
                while self._match(TT.COMMA):
                    elements.append(self._expr())
            self._expect(TT.RBRACKET, "]")
            return ArrayLit(elements, tok.line)

        raise ParseError(f"expressão inesperada: {tok.value!r}", tok.line)


# ---------------------------------------------------------------------------
# Impressora de AST (usa match de Python 3.10+)
# ---------------------------------------------------------------------------

class AstPrinter:
    """Imprime a AST em formato indentado legível."""

    def __init__(self):
        self._depth = 0

    def _w(self, text: str):
        print("  " * self._depth + text)

    def _dn(self):
        self._depth += 1

    def _up(self):
        self._depth -= 1

    def print(self, node):  # noqa: A003
        match node:

            case Program(decls=ds):
                self._w("Program")
                self._dn()
                for d in ds:
                    self.print(d)
                self._up()

            case FunctionDecl(return_type=rt, name=n, params=ps, body=b, line=l):
                params_s = ", ".join(f"{p.type} {p.name}" for p in ps)
                self._w(f"FunctionDecl {rt} {n}({params_s})  [L{l}]")
                self._dn(); self.print(b); self._up()

            case ClassDecl(name=n, attrs=attrs, constructor=ctor, methods=methods, line=l):
                self._w(f"ClassDecl {n}  [L{l}]")
                self._dn()
                for a in attrs:
                    self._w(f"Attr {a.type} {a.name}  [L{a.line}]")
                if ctor is not None:
                    self.print(ctor)
                for m in methods:
                    self.print(m)
                self._up()

            case ConstructorDecl(class_name=cn, params=ps, body=b, line=l):
                params_s = ", ".join(f"{p.type} {p.name}" for p in ps)
                self._w(f"ConstructorDecl {cn}({params_s})  [L{l}]")
                self._dn(); self.print(b); self._up()

            case MethodDecl(return_type=rt, name=n, params=ps, body=b, line=l):
                params_s = ", ".join(f"{p.type} {p.name}" for p in ps)
                self._w(f"MethodDecl {rt} {n}({params_s})  [L{l}]")
                self._dn(); self.print(b); self._up()

            case Block(stmts=ss):
                self._w("Block")
                self._dn()
                for s in ss:
                    self.print(s)
                self._up()

            case VarDecl(type=t, array_size=sz, name=n, init=init, line=l):
                arr = f"[{sz}]" if sz is not None else ""
                self._w(f"VarDecl {t}{arr} {n}  [L{l}]")
                if init is not None:
                    self._dn(); self.print(init); self._up()

            case ConstDecl(type=t, name=n, init=init, line=l):
                self._w(f"ConstDecl {t} {n}  [L{l}]")
                self._dn(); self.print(init); self._up()

            case ReturnStmt(value=v, line=l):
                self._w(f"ReturnStmt  [L{l}]")
                if v is not None:
                    self._dn(); self.print(v); self._up()

            case IfStmt(condition=c, then_block=tb, else_clause=ec, line=l):
                self._w(f"IfStmt  [L{l}]")
                self._dn()
                self._w("condition:"); self._dn(); self.print(c); self._up()
                self._w("then:"); self._dn(); self.print(tb); self._up()
                if ec is not None:
                    self._w("else:"); self._dn(); self.print(ec); self._up()
                self._up()

            case WhileStmt(condition=c, body=b, line=l):
                self._w(f"WhileStmt  [L{l}]")
                self._dn()
                self._w("condition:"); self._dn(); self.print(c); self._up()
                self._w("body:"); self._dn(); self.print(b); self._up()
                self._up()

            case ForStmt(init=i, condition=c, update=u, body=b, line=l):
                self._w(f"ForStmt  [L{l}]")
                self._dn()
                if i is not None:
                    self._w("init:"); self._dn(); self.print(i); self._up()
                if c is not None:
                    self._w("condition:"); self._dn(); self.print(c); self._up()
                if u is not None:
                    self._w("update:"); self._dn(); self.print(u); self._up()
                self._w("body:"); self._dn(); self.print(b); self._up()
                self._up()

            case BreakStmt(line=l):
                self._w(f"BreakStmt  [L{l}]")

            case ExprStmt(expr=e, line=l):
                self._w(f"ExprStmt  [L{l}]")
                self._dn(); self.print(e); self._up()

            case Assign(target=t, op=op, value=v, line=l):
                self._w(f"Assign '{op}'  [L{l}]")
                self._dn()
                self._w("target:"); self._dn(); self.print(t); self._up()
                self._w("value:");  self._dn(); self.print(v); self._up()
                self._up()

            case BinOp(op=op, left=lf, right=rt, line=l):
                self._w(f"BinOp '{op}'  [L{l}]")
                self._dn(); self.print(lf); self.print(rt); self._up()

            case UnaryOp(op=op, operand=operand, line=l):
                self._w(f"UnaryOp '{op}'  [L{l}]")
                self._dn(); self.print(operand); self._up()

            case Call(callee=callee, args=args, line=l):
                self._w(f"Call  [L{l}]")
                self._dn()
                self._w("callee:"); self._dn(); self.print(callee); self._up()
                if args:
                    self._w("args:")
                    self._dn()
                    for a in args:
                        self.print(a)
                    self._up()
                self._up()

            case Subscript(obj=obj, index=idx, line=l):
                self._w(f"Subscript  [L{l}]")
                self._dn()
                self.print(obj)
                self._w("index:"); self._dn(); self.print(idx); self._up()
                self._up()

            case Attr(obj=obj, name=n, line=l):
                self._w(f"Attr .{n}  [L{l}]")
                self._dn(); self.print(obj); self._up()

            case ArrayLit(elements=elems, line=l):
                self._w(f"ArrayLit  [L{l}]")
                self._dn()
                for e in elems:
                    self.print(e)
                self._up()

            case Cast(type=t, expr=e, line=l):
                self._w(f"Cast({t})  [L{l}]")
                self._dn(); self.print(e); self._up()

            case NewExpr(class_name=cn, args=args, line=l):
                self._w(f"NewExpr {cn}  [L{l}]")
                if args:
                    self._dn()
                    for a in args:
                        self.print(a)
                    self._up()

            case Ident(name=n, line=l):
                self._w(f"Ident '{n}'  [L{l}]")

            case IntLit(value=v, line=l):
                self._w(f"IntLit {v}  [L{l}]")

            case RealLit(value=v, line=l):
                self._w(f"RealLit {v}  [L{l}]")

            case StrLit(value=v, line=l):
                self._w(f"StrLit {v!r}  [L{l}]")

            case BoolLit(value=v, line=l):
                self._w(f"BoolLit {v}  [L{l}]")

            case NullLit(line=l):
                self._w(f"NullLit  [L{l}]")

            case _:
                self._w(f"<nó desconhecido: {node!r}>")

"""
Analisador Sintático (Parser) para a linguagem JSS usando ANTLR4.

Este módulo define:
  - Os nós de AST (dataclasses)
  - JSSASTVisitor: percorre a árvore ANTLR e constrói os nós de AST
  - AstPrinter: impressão indentada da AST
  - ParseError / LexError: exceções de erro
  - parse(source): função de entrada pública
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from antlr4 import CommonTokenStream, InputStream, Token
from antlr4.error.ErrorListener import ErrorListener

from JSSLexer import JSSLexer
from JSSParser import JSSParser
from JSSVisitor import JSSVisitor


# ---------------------------------------------------------------------------
# Nós da AST
# ---------------------------------------------------------------------------

@dataclass
class Param:
    type: str
    name: str


@dataclass
class Program:
    decls: list


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
    attrs: list
    constructor: object
    methods: list
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


@dataclass
class Block:
    stmts: list


@dataclass
class VarDecl:
    type: str
    array_size: Optional[int]
    name: str
    init: object
    line: int


@dataclass
class ConstDecl:
    type: str
    name: str
    init: object
    line: int


@dataclass
class ReturnStmt:
    value: object
    line: int


@dataclass
class IfStmt:
    condition: object
    then_block: "Block"
    else_clause: object
    line: int


@dataclass
class WhileStmt:
    condition: object
    body: "Block"
    line: int


@dataclass
class ForStmt:
    init: object
    condition: object
    update: object
    body: "Block"
    line: int


@dataclass
class BreakStmt:
    line: int


@dataclass
class ExprStmt:
    expr: object
    line: int


@dataclass
class Assign:
    target: object
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
    op: str
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
# Exceções
# ---------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f"Erro léxico na linha {line}: {msg}")
        self.line = line


class ParseError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f"Erro sintático na linha {line}: {msg}")
        self.line = line


# ---------------------------------------------------------------------------
# Error listeners — capturam erros do ANTLR e lançam nossas exceções
# ---------------------------------------------------------------------------

class _LexErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise LexError(f"caractere não reconhecido na coluna {column + 1}", line)


class _ParseErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        symbol = getattr(offendingSymbol, "text", "?")
        raise ParseError(f"encontrado {symbol!r} na coluna {column + 1}", line)


# ---------------------------------------------------------------------------
# Visitor: converte árvore ANTLR → nós de AST
# ---------------------------------------------------------------------------

def _parse_str(raw: str) -> str:
    inner = raw[1:-1]
    return bytes(inner, "utf-8").decode("unicode_escape")


class JSSASTVisitor(JSSVisitor):

    # ── programa ──────────────────────────────────────────────────────────────

    def visitProgram(self, ctx: JSSParser.ProgramContext):
        decls = []
        for td in ctx.topDecl():
            result = self.visit(td)
            if isinstance(result, list):
                decls.extend(result)
            else:
                decls.append(result)
        return Program(decls)

    def visitTopDecl(self, ctx: JSSParser.TopDeclContext):
        return self.visitChildren(ctx)

    # ── tipos ─────────────────────────────────────────────────────────────────

    def visitType(self, ctx: JSSParser.TypeContext):
        return ctx.getText()

    # ── funções ───────────────────────────────────────────────────────────────

    def visitFunctionDecl(self, ctx: JSSParser.FunctionDeclContext):
        ret_type = self.visit(ctx.type_())
        name = ctx.IDENT().getText()
        params = self.visit(ctx.params())
        body = self.visit(ctx.block())
        line = ctx.start.line
        return FunctionDecl(ret_type, name, params, body, line)

    def visitParams(self, ctx: JSSParser.ParamsContext):
        return [self.visit(p) for p in ctx.param()]

    def visitParam(self, ctx: JSSParser.ParamContext):
        return Param(self.visit(ctx.type_()), ctx.IDENT().getText())

    # ── classes ───────────────────────────────────────────────────────────────

    def visitClassDecl(self, ctx: JSSParser.ClassDeclContext):
        name = ctx.IDENT().getText()
        attrs, ctor, methods = [], None, []
        for m in ctx.classMember():
            result = self.visit(m)
            if isinstance(result, VarDecl):
                attrs.append(result)
            elif isinstance(result, ConstructorDecl):
                ctor = result
            elif isinstance(result, MethodDecl):
                methods.append(result)
        return ClassDecl(name, attrs, ctor, methods, ctx.start.line)

    def visitClassMember(self, ctx: JSSParser.ClassMemberContext):
        return self.visitChildren(ctx)

    def visitConstructorDecl(self, ctx: JSSParser.ConstructorDeclContext):
        class_name = ctx.IDENT().getText()
        params = self.visit(ctx.params())
        body = self.visit(ctx.block())
        return ConstructorDecl(class_name, params, body, ctx.start.line)

    def visitMethodDecl(self, ctx: JSSParser.MethodDeclContext):
        ret_type = self.visit(ctx.type_())
        name = ctx.IDENT().getText()
        params = self.visit(ctx.params())
        body = self.visit(ctx.block())
        return MethodDecl(ret_type, name, params, body, ctx.start.line)

    def visitAttrDecl(self, ctx: JSSParser.AttrDeclContext):
        type_ = self.visit(ctx.type_())
        name = ctx.IDENT().getText()
        return VarDecl(type_, None, name, None, ctx.start.line)

    # ── bloco ─────────────────────────────────────────────────────────────────

    def visitBlock(self, ctx: JSSParser.BlockContext):
        stmts = []
        for s in ctx.statement():
            result = self.visit(s)
            if isinstance(result, list):
                stmts.extend(result)
            else:
                stmts.append(result)
        return Block(stmts)

    def visitStatement(self, ctx: JSSParser.StatementContext):
        return self.visitChildren(ctx)

    # ── var / const ───────────────────────────────────────────────────────────

    def visitVarDecl(self, ctx: JSSParser.VarDeclContext):
        return self._build_var_decls(ctx)

    def visitVarDeclNoSemi(self, ctx: JSSParser.VarDeclNoSemiContext):
        return self._build_var_decls(ctx)

    def _build_var_decls(self, ctx):
        type_ = self.visit(ctx.type_())
        array_size = int(ctx.INT_LIT().getText()) if ctx.INT_LIT() else None
        line = ctx.start.line
        return [self._visit_declarator(d, type_, array_size, line)
                for d in ctx.declarator()]

    def _visit_declarator(self, ctx: JSSParser.DeclaratorContext, type_, array_size, line):
        name = ctx.IDENT().getText()
        init = self.visit(ctx.expr()) if ctx.expr() else None
        return VarDecl(type_, array_size, name, init, line)

    def visitConstDecl(self, ctx: JSSParser.ConstDeclContext):
        type_ = self.visit(ctx.type_())
        name = ctx.IDENT().getText()
        init = self.visit(ctx.expr())
        return ConstDecl(type_, name, init, ctx.start.line)

    # ── statements ────────────────────────────────────────────────────────────

    def visitReturnStmt(self, ctx: JSSParser.ReturnStmtContext):
        value = self.visit(ctx.expr()) if ctx.expr() else None
        return ReturnStmt(value, ctx.start.line)

    def visitIfStmt(self, ctx: JSSParser.IfStmtContext):
        cond = self.visit(ctx.expr())
        then_b = self.visit(ctx.block())
        else_c = self.visit(ctx.elseClause()) if ctx.elseClause() else None
        return IfStmt(cond, then_b, else_c, ctx.start.line)

    def visitElseClause(self, ctx: JSSParser.ElseClauseContext):
        return self.visitChildren(ctx)

    def visitWhileStmt(self, ctx: JSSParser.WhileStmtContext):
        cond = self.visit(ctx.expr())
        body = self.visit(ctx.block())
        return WhileStmt(cond, body, ctx.start.line)

    def visitForStmt(self, ctx: JSSParser.ForStmtContext):
        init = self.visit(ctx.forInit()) if ctx.forInit() else None
        exprs = ctx.expr()
        condition = self.visit(exprs[0]) if len(exprs) > 0 else None
        update    = self.visit(exprs[1]) if len(exprs) > 1 else None
        body = self.visit(ctx.block())
        return ForStmt(init, condition, update, body, ctx.start.line)

    def visitForInit(self, ctx: JSSParser.ForInitContext):
        return self.visitChildren(ctx)

    def visitBreakStmt(self, ctx: JSSParser.BreakStmtContext):
        return BreakStmt(ctx.start.line)

    def visitExprStmt(self, ctx: JSSParser.ExprStmtContext):
        return ExprStmt(self.visit(ctx.expr()), ctx.start.line)

    # ── expressões ────────────────────────────────────────────────────────────

    def visitExpr(self, ctx: JSSParser.ExprContext):
        if ctx.assignOp():
            target = self.visit(ctx.orExpr())
            if not isinstance(target, (Ident, Subscript, Attr)):
                raise ParseError("alvo de atribuição inválido", ctx.start.line)
            op = ctx.assignOp().getText()
            value = self.visit(ctx.expr())
            return Assign(target, op, value, ctx.start.line)
        return self.visit(ctx.orExpr())

    def visitOrExpr(self, ctx: JSSParser.OrExprContext):
        if ctx.orExpr():
            left = self.visit(ctx.orExpr())
            right = self.visit(ctx.andExpr())
            return BinOp("||", left, right, ctx.start.line)
        return self.visit(ctx.andExpr())

    def visitAndExpr(self, ctx: JSSParser.AndExprContext):
        if ctx.andExpr():
            left = self.visit(ctx.andExpr())
            right = self.visit(ctx.cmpExpr())
            return BinOp("&&", left, right, ctx.start.line)
        return self.visit(ctx.cmpExpr())

    def visitCmpExpr(self, ctx: JSSParser.CmpExprContext):
        if ctx.cmpExpr():
            left = self.visit(ctx.cmpExpr())
            op = ctx.cmpOp().getText()
            right = self.visit(ctx.addExpr())
            return BinOp(op, left, right, ctx.start.line)
        return self.visit(ctx.addExpr())

    def visitAddExpr(self, ctx: JSSParser.AddExprContext):
        if ctx.addExpr():
            left = self.visit(ctx.addExpr())
            op = "+" if ctx.getChild(1).getText() == "+" else "-"
            right = self.visit(ctx.mulExpr())
            return BinOp(op, left, right, ctx.start.line)
        return self.visit(ctx.mulExpr())

    def visitMulExpr(self, ctx: JSSParser.MulExprContext):
        if ctx.mulExpr():
            left = self.visit(ctx.mulExpr())
            op = ctx.getChild(1).getText()
            right = self.visit(ctx.powExpr())
            return BinOp(op, left, right, ctx.start.line)
        return self.visit(ctx.powExpr())

    def visitPowExpr(self, ctx: JSSParser.PowExprContext):
        if ctx.getChildCount() == 3:
            left = self.visit(ctx.unaryExpr())
            right = self.visit(ctx.powExpr())
            return BinOp("**", left, right, ctx.start.line)
        return self.visit(ctx.unaryExpr())

    def visitUnaryExpr(self, ctx: JSSParser.UnaryExprContext):
        if ctx.postfixExpr():
            return self.visit(ctx.postfixExpr())
        op = ctx.getChild(0).getText()
        operand = self.visit(ctx.unaryExpr())
        return UnaryOp(op, operand, ctx.start.line)

    def visitPostfixExpr(self, ctx: JSSParser.PostfixExprContext):
        if ctx.primary():
            return self.visit(ctx.primary())
        obj = self.visit(ctx.postfixExpr())
        line = ctx.start.line
        # subscript: postfixExpr '[' expr ']'
        if ctx.getChildCount() == 4 and ctx.getChild(1).getText() == "[":
            idx = self.visit(ctx.expr())
            return Subscript(obj, idx, line)
        # call: postfixExpr '(' argList ')'
        if ctx.argList() is not None:
            args = self.visit(ctx.argList())
            return Call(obj, args, line)
        # attr: postfixExpr '.' IDENT
        name = ctx.IDENT().getText()
        return Attr(obj, name, line)

    def visitArgList(self, ctx: JSSParser.ArgListContext):
        return [self.visit(e) for e in ctx.expr()]

    def visitPrimary(self, ctx: JSSParser.PrimaryContext):
        line = ctx.start.line
        first = ctx.getChild(0).getText()

        if ctx.INT_LIT():
            return IntLit(int(ctx.INT_LIT().getText()), line)
        if ctx.REAL_LIT():
            return RealLit(float(ctx.REAL_LIT().getText()), line)
        if ctx.STR_LIT():
            return StrLit(_parse_str(ctx.STR_LIT().getText()), line)
        if first == "true":
            return BoolLit(True, line)
        if first == "false":
            return BoolLit(False, line)
        if first == "null":
            return NullLit(line)
        if first == "this":
            return Ident("this", line)
        if first == "new":
            name = ctx.IDENT().getText()
            args = self.visit(ctx.argList())
            return NewExpr(name, args, line)
        # cast: type '(' expr ')'  — primeiro filho é um tipo primitivo
        if ctx.type_():
            type_ = self.visit(ctx.type_())
            return Cast(type_, self.visit(ctx.expr()[0]), line)
        # agrupamento: '(' expr ')'
        if first == "(":
            return self.visit(ctx.expr()[0])
        # array literal: '[' expr* ']'
        if first == "[":
            return ArrayLit([self.visit(e) for e in ctx.expr()], line)
        # identificador
        return Ident(ctx.IDENT().getText(), line)


# ---------------------------------------------------------------------------
# Função pública de parse
# ---------------------------------------------------------------------------

def parse(source: str) -> Program:
    input_stream = InputStream(source)

    lexer = JSSLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(_LexErrorListener())

    token_stream = CommonTokenStream(lexer)

    parser = JSSParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(_ParseErrorListener())

    tree = parser.program()
    return JSSASTVisitor().visit(tree)


# ---------------------------------------------------------------------------
# Impressora de AST
# ---------------------------------------------------------------------------

class AstPrinter:
    def __init__(self):
        self._depth = 0

    def _w(self, text: str):
        print("  " * self._depth + text)

    def _dn(self): self._depth += 1
    def _up(self): self._depth -= 1

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
                    self._w("init:")
                    self._dn()
                    if isinstance(i, list):
                        for v in i:
                            self.print(v)
                    else:
                        self.print(i)
                    self._up()
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

"""
Analisador Léxico (Lexer) para a linguagem JSS – JavaScript Simplificado.

Regras léxicas implementadas:
  - Identificadores: [a-zA-Z_][a-zA-Z0-9_]*
  - Literais inteiros, reais (com expoente), strings com escapes, bool, null
  - Palavras reservadas (case-sensitive)
  - Operadores simples e compostos (++, **, +=, ==, &&, ||, …)
  - Delimitadores: { } ( ) [ ] , ; .
  - Comentários de linha: // … (descartados)
  - Espaços/quebras de linha descartados (linha rastreada para mensagens de erro)
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Tipos de token
# ---------------------------------------------------------------------------

class TT(Enum):
    # Literais
    INT_LIT   = auto()
    REAL_LIT  = auto()
    STR_LIT   = auto()
    BOOL_LIT  = auto()
    NULL      = auto()

    # Palavras reservadas
    LET       = auto()
    CONST     = auto()
    FUNCTION  = auto()
    VOID      = auto()
    RETURN    = auto()
    IF        = auto()
    ELSE      = auto()
    WHILE     = auto()
    FOR       = auto()
    BREAK     = auto()
    CLASS     = auto()
    NEW       = auto()
    THIS      = auto()

    # Tipos primitivos (usados como keyword de tipo E como cast)
    INT       = auto()
    REAL      = auto()
    STR       = auto()
    BOOL      = auto()

    # Identificador
    IDENT     = auto()

    # Operadores aritméticos
    PLUS      = auto()   # +
    MINUS     = auto()   # -
    STAR      = auto()   # *
    SLASH     = auto()   # /
    PERCENT   = auto()   # %
    POWER     = auto()   # **

    # Unários
    BANG      = auto()   # !
    INC       = auto()   # ++
    DEC       = auto()   # --

    # Relacionais / igualdade
    EQ        = auto()   # ==
    NEQ       = auto()   # !=
    LT        = auto()   # <
    LTE       = auto()   # <=
    GT        = auto()   # >
    GTE       = auto()   # >=

    # Lógicos
    AND       = auto()   # &&
    OR        = auto()   # ||

    # Atribuição simples e composta
    ASSIGN         = auto()   # =
    PLUS_ASSIGN    = auto()   # +=
    MINUS_ASSIGN   = auto()   # -=
    STAR_ASSIGN    = auto()   # *=
    SLASH_ASSIGN   = auto()   # /=
    PERCENT_ASSIGN = auto()   # %=

    # Delimitadores
    LBRACE    = auto()   # {
    RBRACE    = auto()   # }
    LPAREN    = auto()   # (
    RPAREN    = auto()   # )
    LBRACKET  = auto()   # [
    RBRACKET  = auto()   # ]
    COMMA     = auto()   # ,
    SEMICOLON = auto()   # ;
    DOT       = auto()   # .

    # Fim de arquivo
    EOF       = auto()


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type:  TT
    value: object
    line:  int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Erro léxico
# ---------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f"Erro léxico na linha {line}: {msg}")
        self.line = line


# ---------------------------------------------------------------------------
# Palavras reservadas
# ---------------------------------------------------------------------------

KEYWORDS: dict[str, TT] = {
    "let":      TT.LET,
    "const":    TT.CONST,
    "function": TT.FUNCTION,
    "void":     TT.VOID,
    "return":   TT.RETURN,
    "if":       TT.IF,
    "else":     TT.ELSE,
    "while":    TT.WHILE,
    "for":      TT.FOR,
    "break":    TT.BREAK,
    "class":    TT.CLASS,
    "new":      TT.NEW,
    "this":     TT.THIS,
    # tipos / casts
    "int":      TT.INT,
    "real":     TT.REAL,
    "str":      TT.STR,
    "bool":     TT.BOOL,
    # literais especiais
    "true":     TT.BOOL_LIT,
    "false":    TT.BOOL_LIT,
    "null":     TT.NULL,
}


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Tokeniza o código-fonte JSS caractere por caractere.

    Uso:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()   # lista de Token
    """

    def __init__(self, source: str):
        self._source = source
        self._pos    = 0
        self._line   = 1
        self._tokens: list[Token] = []

    # ── utilitários de leitura ──────────────────────────────────────────────

    def _char(self) -> Optional[str]:
        """Retorna o caractere atual ou None se chegou ao fim."""
        if self._pos < len(self._source):
            return self._source[self._pos]
        return None

    def _next(self) -> Optional[str]:
        """Retorna o próximo caractere (lookahead de 1) ou None."""
        if self._pos + 1 < len(self._source):
            return self._source[self._pos + 1]
        return None

    def _advance(self) -> str:
        """Consome o caractere atual e avança o dedo."""
        char = self._source[self._pos]
        self._pos += 1
        return char

    def _add(self, tipo: TT, valor: object):
        """Adiciona um token na lista."""
        self._tokens.append(Token(tipo, valor, self._line))

    # ── tokenizador principal ───────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        while self._char() is not None:
            c = self._char()

            # ── espaço / tab ──────────────────────────────────────────
            if c in (' ', '\t', '\r'):
                self._advance()

            # ── nova linha ────────────────────────────────────────────
            elif c == '\n':
                self._line += 1
                self._advance()

            # ── comentário (//) ───────────────────────────────────────
            elif c == '/' and self._next() == '/':
                while self._char() is not None and self._char() != '\n':
                    self._advance()

            # ── string ────────────────────────────────────────────────
            elif c == '"':
                self._ler_string()

            # ── número (inteiro ou real) ──────────────────────────────
            elif c.isdigit():
                self._ler_numero()

            # ── identificador ou palavra reservada ────────────────────
            elif c.isalpha() or c == '_':
                self._ler_identificador()

            # ── operadores e delimitadores ────────────────────────────
            else:
                self._ler_operador()

        self._tokens.append(Token(TT.EOF, None, self._line))
        return self._tokens

    # ── leitores específicos ────────────────────────────────────────────────

    def _ler_string(self):
        self._advance()   # pula a aspa de abertura "
        texto = ""
        while self._char() is not None and self._char() != '"':
            if self._char() == '\\':
                self._advance()   # pula a barra
                escape = self._advance()
                # converte o escape para o caractere real
                texto += {'n': '\n', 't': '\t', '\\': '\\', '"': '"'}.get(escape, escape)
            else:
                texto += self._advance()

        if self._char() is None:
            raise LexError("String não fechada", self._line)

        self._advance()   # pula a aspa de fechamento "
        self._add(TT.STR_LIT, texto)

    def _ler_numero(self):
        numero = ""
        while self._char() is not None and self._char().isdigit():
            numero += self._advance()

        # tem ponto decimal? é real
        if self._char() == '.' and self._next() is not None and self._next().isdigit():
            numero += self._advance()   # pula o ponto
            while self._char() is not None and self._char().isdigit():
                numero += self._advance()

            # tem expoente? ex: 2.5E3 ou 1.0e-2
            if self._char() in ('E', 'e'):
                numero += self._advance()   # pula o E
                if self._char() in ('+', '-'):
                    numero += self._advance()
                while self._char() is not None and self._char().isdigit():
                    numero += self._advance()

            self._add(TT.REAL_LIT, float(numero))
        else:
            self._add(TT.INT_LIT, int(numero))

    def _ler_identificador(self):
        palavra = ""
        while self._char() is not None and (self._char().isalnum() or self._char() == '_'):
            palavra += self._advance()

        # verifica se é palavra reservada
        tipo = KEYWORDS.get(palavra, TT.IDENT)

        # booleanos viram valor Python bool
        if tipo == TT.BOOL_LIT:
            self._add(TT.BOOL_LIT, palavra == "true")
        else:
            self._add(tipo, palavra)

    def _ler_operador(self):
        c    = self._char()
        prox = self._next()

        # ── operadores de 2 caracteres ────────────────────────────────
        dois = (c or "") + (prox or "")

        if dois == '**': self._advance(); self._advance(); self._add(TT.POWER,          '**')
        elif dois == '++': self._advance(); self._advance(); self._add(TT.INC,           '++')
        elif dois == '--': self._advance(); self._advance(); self._add(TT.DEC,           '--')
        elif dois == '+=': self._advance(); self._advance(); self._add(TT.PLUS_ASSIGN,   '+=')
        elif dois == '-=': self._advance(); self._advance(); self._add(TT.MINUS_ASSIGN,  '-=')
        elif dois == '*=': self._advance(); self._advance(); self._add(TT.STAR_ASSIGN,   '*=')
        elif dois == '/=': self._advance(); self._advance(); self._add(TT.SLASH_ASSIGN,  '/=')
        elif dois == '%=': self._advance(); self._advance(); self._add(TT.PERCENT_ASSIGN,'%=')
        elif dois == '==': self._advance(); self._advance(); self._add(TT.EQ,            '==')
        elif dois == '!=': self._advance(); self._advance(); self._add(TT.NEQ,           '!=')
        elif dois == '<=': self._advance(); self._advance(); self._add(TT.LTE,           '<=')
        elif dois == '>=': self._advance(); self._advance(); self._add(TT.GTE,           '>=')
        elif dois == '&&': self._advance(); self._advance(); self._add(TT.AND,           '&&')
        elif dois == '||': self._advance(); self._advance(); self._add(TT.OR,            '||')

        # ── operadores de 1 caractere ─────────────────────────────────
        elif c == '+': self._advance(); self._add(TT.PLUS,      '+')
        elif c == '-': self._advance(); self._add(TT.MINUS,     '-')
        elif c == '*': self._advance(); self._add(TT.STAR,      '*')
        elif c == '/': self._advance(); self._add(TT.SLASH,     '/')
        elif c == '%': self._advance(); self._add(TT.PERCENT,   '%')
        elif c == '!': self._advance(); self._add(TT.BANG,      '!')
        elif c == '<': self._advance(); self._add(TT.LT,        '<')
        elif c == '>': self._advance(); self._add(TT.GT,        '>')
        elif c == '=': self._advance(); self._add(TT.ASSIGN,    '=')

        # ── delimitadores ─────────────────────────────────────────────
        elif c == '{': self._advance(); self._add(TT.LBRACE,    '{')
        elif c == '}': self._advance(); self._add(TT.RBRACE,    '}')
        elif c == '(': self._advance(); self._add(TT.LPAREN,    '(')
        elif c == ')': self._advance(); self._add(TT.RPAREN,    ')')
        elif c == '[': self._advance(); self._add(TT.LBRACKET,  '[')
        elif c == ']': self._advance(); self._add(TT.RBRACKET,  ']')
        elif c == ',': self._advance(); self._add(TT.COMMA,     ',')
        elif c == ';': self._advance(); self._add(TT.SEMICOLON, ';')
        elif c == '.': self._advance(); self._add(TT.DOT,       '.')

        # ── caractere desconhecido ────────────────────────────────────
        else:
            raise LexError(f"Caractere não reconhecido: {c!r}", self._line)

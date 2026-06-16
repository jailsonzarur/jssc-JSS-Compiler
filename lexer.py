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

import re
from dataclasses import dataclass, field
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
    ASSIGN        = auto()   # =
    PLUS_ASSIGN   = auto()   # +=
    MINUS_ASSIGN  = auto()   # -=
    STAR_ASSIGN   = auto()   # *=
    SLASH_ASSIGN  = auto()   # /=
    PERCENT_ASSIGN= auto()   # %=

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
# Mapeamento de palavras reservadas
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
# Padrões léxicos (ordem importa!)
# ---------------------------------------------------------------------------

_TOKEN_PATTERNS = [
    # comentário de linha – descartado
    ("COMMENT",    r"//[^\n]*"),
    # espaço + nova linha – rastrear linha
    ("NEWLINE",    r"\n"),
    ("WHITESPACE", r"[ \t\r]+"),

    # literais de string (com escapes \n \t \\ \" etc.)
    ("STR_LIT",    r'"(?:[^"\\]|\\.)*"'),

    # literais numéricos  (real antes de int para evitar engolir só a parte inteira)
    ("REAL_LIT",   r"[0-9]+(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]+)"),  # com expoente
    ("REAL_LIT2",  r"[0-9]+\.[0-9]+"),                            # sem expoente
    ("INT_LIT",    r"[0-9]+"),

    # operadores de 2+ caracteres (antes dos de 1 char)
    ("POWER",          r"\*\*"),
    ("INC",            r"\+\+"),
    ("DEC",            r"--"),
    ("PLUS_ASSIGN",    r"\+="),
    ("MINUS_ASSIGN",   r"-="),
    ("STAR_ASSIGN",    r"\*="),
    ("SLASH_ASSIGN",   r"/="),
    ("PERCENT_ASSIGN", r"%="),
    ("EQ",             r"=="),
    ("NEQ",            r"!="),
    ("LTE",            r"<="),
    ("GTE",            r">="),
    ("AND",            r"&&"),
    ("OR",             r"\|\|"),

    # operadores de 1 char
    ("PLUS",      r"\+"),
    ("MINUS",     r"-"),
    ("STAR",      r"\*"),
    ("SLASH",     r"/"),
    ("PERCENT",   r"%"),
    ("BANG",      r"!"),
    ("LT",        r"<"),
    ("GT",        r">"),
    ("ASSIGN",    r"="),

    # delimitadores
    ("LBRACE",    r"\{"),
    ("RBRACE",    r"\}"),
    ("LPAREN",    r"\("),
    ("RPAREN",    r"\)"),
    ("LBRACKET",  r"\["),
    ("RBRACKET",  r"\]"),
    ("COMMA",     r","),
    ("SEMICOLON", r";"),
    ("DOT",       r"\."),

    # identificadores / palavras reservadas
    ("IDENT",     r"[a-zA-Z_][a-zA-Z0-9_]*"),

    # qualquer coisa não reconhecida
    ("UNKNOWN",   r"."),
]

# Compila o mega-regex com grupos nomeados
_MASTER_RE = re.compile(
    "|".join(f"(?P<{name}>{pat})" for name, pat in _TOKEN_PATTERNS),
    re.DOTALL,
)

# Mapeia nome de grupo → TT (os descartáveis ficam como None)
_GROUP_TO_TT: dict[str, Optional[TT]] = {
    "COMMENT":         None,
    "NEWLINE":         None,
    "WHITESPACE":      None,
    "STR_LIT":         TT.STR_LIT,
    "REAL_LIT":        TT.REAL_LIT,
    "REAL_LIT2":       TT.REAL_LIT,
    "INT_LIT":         TT.INT_LIT,
    "POWER":           TT.POWER,
    "INC":             TT.INC,
    "DEC":             TT.DEC,
    "PLUS_ASSIGN":     TT.PLUS_ASSIGN,
    "MINUS_ASSIGN":    TT.MINUS_ASSIGN,
    "STAR_ASSIGN":     TT.STAR_ASSIGN,
    "SLASH_ASSIGN":    TT.SLASH_ASSIGN,
    "PERCENT_ASSIGN":  TT.PERCENT_ASSIGN,
    "EQ":              TT.EQ,
    "NEQ":             TT.NEQ,
    "LTE":             TT.LTE,
    "GTE":             TT.GTE,
    "AND":             TT.AND,
    "OR":              TT.OR,
    "PLUS":            TT.PLUS,
    "MINUS":           TT.MINUS,
    "STAR":            TT.STAR,
    "SLASH":           TT.SLASH,
    "PERCENT":         TT.PERCENT,
    "BANG":            TT.BANG,
    "LT":              TT.LT,
    "GT":              TT.GT,
    "ASSIGN":          TT.ASSIGN,
    "LBRACE":          TT.LBRACE,
    "RBRACE":          TT.RBRACE,
    "LPAREN":          TT.LPAREN,
    "RPAREN":          TT.RPAREN,
    "LBRACKET":        TT.LBRACKET,
    "RBRACKET":        TT.RBRACKET,
    "COMMA":           TT.COMMA,
    "SEMICOLON":       TT.SEMICOLON,
    "DOT":             TT.DOT,
    "IDENT":           TT.IDENT,
    "UNKNOWN":         None,   # vai gerar LexError
}


# ---------------------------------------------------------------------------
# Conversores de valor bruto → valor Python tipado
# ---------------------------------------------------------------------------

def _parse_string(raw: str) -> str:
    """Remove aspas e processa escapes."""
    inner = raw[1:-1]
    return bytes(inner, "utf-8").decode("unicode_escape")


def _parse_real(raw: str) -> float:
    return float(raw)


def _parse_int(raw: str) -> int:
    return int(raw)


def _parse_bool(raw: str) -> bool:
    return raw == "true"


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Tokeniza o código-fonte JSS.

    Uso:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()   # lista de Token
    """

    def __init__(self, source: str):
        self._source = source

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        line = 1

        for m in _MASTER_RE.finditer(self._source):
            kind = m.lastgroup
            raw  = m.group()

            if kind == "NEWLINE":
                line += 1
                continue

            if kind in ("COMMENT", "WHITESPACE"):
                continue

            if kind == "UNKNOWN":
                raise LexError(f"Caractere não reconhecido: {raw!r}", line)

            tt = _GROUP_TO_TT[kind]

            # Converte valor
            if tt == TT.INT_LIT:
                value = _parse_int(raw)
            elif tt == TT.REAL_LIT:
                value = _parse_real(raw)
            elif tt == TT.STR_LIT:
                value = _parse_string(raw)
            elif kind == "IDENT":
                # Verifica se é palavra reservada
                kw = KEYWORDS.get(raw)
                if kw is not None:
                    tt = kw
                    value = raw if tt == TT.BOOL_LIT else raw
                else:
                    value = raw
            else:
                value = raw

            # BOOL_LIT: converte "true"/"false" → bool Python
            if tt == TT.BOOL_LIT:
                value = _parse_bool(raw)

            tokens.append(Token(tt, value, line))

        tokens.append(Token(TT.EOF, None, line))
        return tokens

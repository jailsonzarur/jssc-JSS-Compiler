"""
Compilador JSS — Análise Léxica e Sintática.

Uso:
    python3 main.py <arquivo.jss>
    python3 main.py < <arquivo.jss>

Flags opcionais:
    --tokens   Executa apenas a análise léxica e imprime os tokens
    --ast      Imprime a Árvore Sintática Abstrata (AST)
"""

import sys
from lexer import Lexer, LexError
from parser import Parser, ParseError, AstPrinter


def main():
    args = sys.argv[1:]
    flag_tokens = "--tokens" in args
    flag_ast    = "--ast"    in args
    src_args    = [a for a in args if not a.startswith("--")]

    # Leitura da fonte
    if src_args:
        try:
            with open(src_args[0], "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Arquivo não encontrado: {src_args[0]}")
            sys.exit(1)
    else:
        source = sys.stdin.read()

    # ── Análise léxica ───────────────────────────────────────────────────────
    try:
        tokens = Lexer(source).tokenize()
    except LexError as e:
        print(str(e))
        sys.exit(1)

    if flag_tokens:
        for tok in tokens:
            print(tok)
        print("\nAnálise léxica concluída sem erros.")
        return

    # ── Análise sintática ────────────────────────────────────────────────────
    try:
        ast = Parser(tokens).parse()
    except ParseError as e:
        print(str(e))
        sys.exit(1)

    if flag_ast:
        AstPrinter().print(ast)
        print()

    print("Análise léxica e sintática concluída sem erros.")


if __name__ == "__main__":
    main()

"""
Compilador JSS — Análise Léxica.

Uso:
    python main.py programa.jss
    python main.py < programa.jss
"""

import sys
from lexer import Lexer, LexError


def main():
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Arquivo não encontrado: {sys.argv[1]}")
            sys.exit(1)
    else:
        source = sys.stdin.read()

    try:
        tokens = Lexer(source).tokenize()
    except LexError as e:
        print(str(e))
        sys.exit(1)

    for tok in tokens:
        print(tok)

    print("\nAnálise léxica concluída sem erros.")


if __name__ == "__main__":
    main()

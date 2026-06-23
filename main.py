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
from parser import parse, ParseError, LexError, AstPrinter


def main():
    args = sys.argv[1:]
    flag_tokens = "--tokens" in args
    flag_ast    = "--ast"    in args
    src_args    = [a for a in args if not a.startswith("--")]

    if src_args:
        try:
            with open(src_args[0], "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Arquivo não encontrado: {src_args[0]}")
            sys.exit(1)
    else:
        source = sys.stdin.read()

    if flag_tokens:
        from antlr4 import CommonTokenStream, InputStream
        from JSSLexer import JSSLexer
        input_stream = InputStream(source)
        lexer = JSSLexer(input_stream)
        stream = CommonTokenStream(lexer)
        try:
            stream.fill()
        except Exception as e:
            print(f"Erro léxico: {e}")
            sys.exit(1)
        for tok in stream.tokens[:-1]:  # exclui EOF
            print(f"Token({lexer.symbolicNames[tok.type]}, {tok.text!r}, line={tok.line})")
        print("\nAnálise léxica concluída sem erros.")
        return

    try:
        ast = parse(source)
    except (LexError, ParseError) as e:
        print(str(e))
        sys.exit(1)

    if flag_ast:
        AstPrinter().print(ast)
        print()

    print("Análise léxica e sintática concluída sem erros.")


if __name__ == "__main__":
    main()

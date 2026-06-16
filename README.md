# Compilador JSS — Análise Léxica

Analisador léxico (lexer) para a linguagem **JSS (JavaScript Simplificado)**, desenvolvido em Python puro, sem bibliotecas externas.

## Pré-requisitos

Apenas **Python 3.10 ou superior**.

```bash
python3 --version
```

## Execução

```bash
python3 main.py <caminho_do_arquivo.jss>
```

Ou lendo da entrada padrão:

```bash
python3 main.py < arquivo.jss
```

## Exemplos

### Programa válido

```bash
python3 main.py exemplos/fatorial.jss
```

Saída (lista de tokens com tipo, valor e linha):
```
Token(FUNCTION, 'function', line=1)
Token(INT, 'int', line=1)
Token(IDENT, 'fatorial', line=1)
...
Análise léxica concluída sem erros.
```

### Programa com erro léxico

```bash
python3 main.py exemplos/erro_lexico.jss
```

Saída:
```
Erro léxico na linha 3: Caractere não reconhecido: '@'
```

O compilador encerra com código de saída `1` em caso de erro e `0` em caso de sucesso.

## Regras léxicas implementadas

| Categoria | Descrição | Exemplos |
|-----------|-----------|---------|
| Identificadores | Iniciam com letra ou `_`, seguidos de letras, dígitos ou `_` | `x`, `_val`, `nome1` |
| Palavras reservadas | Reconhecidas automaticamente pelo nome | `let`, `const`, `function`, `if`, `while`, `for`, `class`, … |
| Tipos primitivos | Usados em declarações e como funções de cast | `int`, `real`, `str`, `bool` |
| Inteiros | Sequência de dígitos | `0`, `42`, `100` |
| Reais | Ponto flutuante com ou sem expoente | `1.5`, `-10.8`, `2.5E3`, `1.0e-2` |
| Strings | Delimitadas por `"…"`, com suporte a escapes | `"Olá\n"`, `"valor:\t"` |
| Booleanos | Literais `true` e `false` | `true`, `false` |
| Nulo | Literal `null` | `null` |
| Operadores compostos | Reconhecidos antes dos simples | `**`, `++`, `--`, `+=`, `-=`, `==`, `!=`, `<=`, `>=`, `&&`, `\|\|` |
| Operadores simples | Aritméticos, relacionais, lógicos e atribuição | `+`, `-`, `*`, `/`, `%`, `!`, `=`, `<`, `>` |
| Delimitadores | Pontuação estrutural | `{ } ( ) [ ] , ; .` |
| Comentários | Linha iniciada com `//` — descartados | `// comentário` |
| Erro | Qualquer caractere não reconhecido | `@`, `#`, `$` |

A linguagem é **case-sensitive**: `var`, `VAR` e `VaR` são identificadores distintos.

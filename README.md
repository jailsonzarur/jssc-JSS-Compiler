# Compilador JSS — Análise Léxica e Sintática

Compilador para a linguagem **JSS (JavaScript Simplificado)**, desenvolvido em Python puro, sem bibliotecas externas.

Etapas implementadas:
- **Fase 1 — Análise Léxica (Lexer):** tokenização completa da linguagem
- **Fase 2 — Análise Sintática (Parser):** construção da AST via descida recursiva

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

Em caso de **sucesso**, exibe:
```
Análise léxica e sintática concluída sem erros.
```

Em caso de **erro**, exibe a mensagem com o número da linha e encerra com código `1`:
```
Erro léxico na linha 3: Caractere não reconhecido: '@'
Erro sintático na linha 4: esperado ';', encontrado 'console'
```

## Flags opcionais

| Flag | Descrição |
|------|-----------|
| `--tokens` | Executa apenas a análise léxica e imprime a lista de tokens |
| `--ast` | Imprime a Árvore Sintática Abstrata (AST) completa |

### Exemplos

```bash
# Programa válido — confirmação de sucesso
python3 main.py exemplos/fatorial.jss

# Programa válido — exibe a AST
python3 main.py --ast exemplos/fatorial.jss

# Apenas tokens
python3 main.py --tokens exemplos/media.jss

# Erro léxico (caractere '@' inválido)
python3 main.py exemplos/erro_lexico.jss

# Erro sintático (';' faltando)
python3 main.py exemplos/erro_sintatico.jss
```

## Exemplos de programas

| Arquivo | Descrição |
|---------|-----------|
| `exemplos/fatorial.jss` | Função recursiva de fatorial |
| `exemplos/media.jss` | Média entre dois valores reais |
| `exemplos/vetores.jss` | Declaração e acesso a arrays |
| `exemplos/erro_lexico.jss` | Erro: caractere `@` não reconhecido |
| `exemplos/erro_sintatico.jss` | Erro: `;` ausente após declaração |
| `exemplos/erro_semantico.jss` | Atribuição a constante (detectado na análise semântica) |

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

## Regras sintáticas implementadas

O parser utiliza **descida recursiva** e constrói uma AST (Árvore Sintática Abstrata).

### Estrutura de um programa

Um programa JSS é composto por zero ou mais declarações globais (variáveis, constantes, funções e classes). A função `main` é facultativa.

### Declarações suportadas

| Construção | Sintaxe |
|---|---|
| Função | `function <tipo> <nome>(<params>) { ... }` |
| Variável simples | `let int x;` / `let int x = 10;` |
| Múltiplas variáveis | `let int n1, n2;` |
| Array | `let int[3] nums = [1, 2, 3];` |
| Constante | `const real pi = 3.14;` |
| Classe | `class Ponto { int x; Ponto constructor(...) { } int soma() { } }` |

### Comandos de controle

| Comando | Sintaxe |
|---|---|
| Condicional | `if (cond) { } else if (cond) { } else { }` |
| Laço while | `while (cond) { }` |
| Laço for | `for (expr; cond; expr) { }` |
| Retorno | `return expr;` |
| Break | `break;` |

### Operadores (precedência — 1 é a mais alta)

| Nível | Operadores | Associatividade |
|-------|-----------|----------------|
| 1 | `!` `+` `-` `++` `--` (prefixo) | — |
| 2 | `**` | Direita |
| 3 | `*` `/` `%` | Esquerda |
| 4 | `+` `-` | Esquerda |
| 5 | `>` `>=` `<` `<=` `==` `!=` | Esquerda |
| 6 | `&&` | Esquerda |
| 7 | `\|\|` | Esquerda |
| 8 | `=` `+=` `-=` `*=` `/=` `%=` | Direita |

### Funções nativas

| Função | Descrição |
|--------|-----------|
| `input(var1, var2, ...)` | Lê valores do teclado |
| `console.log(expr1, expr2, ...)` | Imprime no console |
| `int(expr)` | Cast para inteiro |
| `real(expr)` | Cast para real |
| `str(expr)` | Cast para string |
| `bool(expr)` | Cast para booleano |

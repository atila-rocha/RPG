# PLANO VISUAL V2 — Fluxo Máximo (Edmonds-Karp/BFS e Ford-Fulkerson/DFS)

Fase: **VISUAL (revisão 2)**. Substitui `PLANO_VISUAL_FLUXO.md` **apenas nos pontos aqui
tratados**; tudo o que não é citado (grafo `f/C`, reversas tracejadas, paleta de 7 papéis,
painel de estado, fecho do corte) continua valendo **sem alteração**.

Entrada: `PLANO_VISUAL_FLUXO.md` (V1), `RELATORIO_CODIFICADOR_FLUXO.md`,
`src/flow_common.py`, `src/flow_record.py`, `dataset/tinyFN.txt` (V=6, E=8, s=0, t=5).

Data: 2026-11-12. **Todos os números abaixo foram medidos** com o Manim 0.22.0 do `.venv`
do projeto e o trace real (`coletar_detalhado`), não estimados.

Este documento é contrato: o `codificador` implementa o que está aqui. Divergência sem
pedido volta para correção.

---

## 0. Resumo executivo (o que muda e por quê)

| # | pedido do usuário | decisão | número medido |
|---|---|---|---|
| 1 | animação mais devagar (0,5–1,0 s por linha) | novo `RITMO` em múltiplos de 1/15 s | 0,60–1,00 s por passo; **18,7 min** (BFS) / **13,8 min** (DFS) |
| 2 | fonte do código maior | **paginação por linhas + quebra de linha longa** (a largura era o gargalo, não a altura) | **11,06 pt** (era 6,76) |
| 3 | mais abas de estrutura | 5 abas em **trilho vertical** | `rede`, `busca`, `marcados`, `edge_to`, `adj` |
| 4 | usar o orquestrador | este plano → `codificador` | — |

### 0.1 A descoberta que muda o item 2

O relatório do codificador atribuiu a fonte pequena às **37 linhas** do `__init__`. **Está
errado.** Medido com o `Code` real:

| restrição | valor | escala que impõe |
|---|---|---|
| altura: 37 linhas × 0,3737 = 13,827 | útil 4,03 | 0,2915 |
| **largura: `is_feasible` linha 111 = 128 caracteres = 22,37 un.** | útil 7,54 | **0,2815** |

A **largura** é o gargalo (0,2815 < 0,2915). Paginar só a altura **não ganharia um único
ponto de fonte**. Por isso o V2 faz as duas coisas: pagina **e** quebra a linha longa em
colunas (82), que é o que libera a fonte.

> Consequência de contrato: a skill `manim-codigo-dinamico` §1.5 diz "se não couber, reduza
> a fonte uma vez; não corte linhas". Aqui **não se corta nada** — a quebra insere um
> `\n` num espaço e mantém todos os caracteres na ordem. O invariante está em §2.4 e é
> cobrado pelo validador.

---

## A. RITMO

### A.1 Tabela nova (`RITMO` em `flow_common.py`)

Valores em **múltiplos exatos de 1/15 s** para que o render 480p (15 fps) não arredonde
para cima — foi o que inflou o V1 em 1,2 min.

```python
RITMO = dict(
    play=0.40,            # 6/15  — play único do passo (indicador + grafo + painéis)
    play_destaque=7 / 15, # 0.4667 — passos com Flash
    fade=2 / 15,          # 0.1333 — CADA um dos dois plays da troca (0.2667 por troca)
    pausa={0.55: 3 / 15,  # 0.2000 — bookkeeping (for/while/if/atribuição)
           1.00: 5 / 15,  # 0.3333 — decisão
           1.70: 8 / 15}, # 0.5333 — fecho (|f| += b, check, return da busca)
)
```

### A.2 Regra do tier (o gravador não muda)

O tier vem de `Step.pausa`, gravado por `flow_record` (0,55 / 1,0 / 1,7). A cena **não
recalcula**:

```python
pausa = RITMO["pausa"].get(round(passo.pausa, 2), RITMO["pausa"][0.55])
```

### A.3 Conta do tempo por linha (play + pausa)

| caso | conta | tempo |
|---|---|---|
| bookkeeping | 0,40 + 0,2000 | **0,600 s** |
| bookkeeping + Flash | 0,4667 + 0,2000 | **0,667 s** |
| decisão | 0,40 + 0,3333 | **0,733 s** |
| decisão + Flash | 0,4667 + 0,3333 | **0,800 s** |
| fecho | 0,40 + 0,5333 | **0,933 s** |
| fecho + Flash | 0,4667 + 0,5333 | **1,000 s** |

**Regra da troca (view ou aba) — o passo não fica mais longo por trocar.** A troca custa
`2 × fade = 0,2667` e esse tempo é **descontado da pausa**:

```python
extra = 2 * RITMO["fade"] if (troca_view or troca_aba) else 0.0
self.wait(max(0.0, pausa - extra))
```

Assim a duração de um passo é `play + max(pausa, 2·fade)` — **independente de haver troca**.
Sem essa regra, 597 trocas de página somariam 2,7 min só de fade.

### A.4 Prova da faixa (medida no trace real, passo a passo)

| duração | BFS (1661) | DFS (1218) |
|---|---|---|
| 0,600 | 675 (40,6 %) | 507 (41,6 %) |
| 0,667 | 463 (27,9 %) | 320 (26,3 %) |
| 0,733 | 357 (21,5 %) | 257 (21,1 %) |
| 0,800 | 144 (8,7 %) | 96 (7,9 %) |
| 0,933 | 13 (0,8 %) | 29 (2,4 %) |
| 1,000 | 9 (0,5 %) | 9 (0,7 %) |

- **99,5 % dos passos em [0,60; 0,93] s** (a faixa pedida era 0,55–0,95).
- **Nenhum passo abaixo de 0,60 s** (piso pedido: 0,5).
- Os 9 passos de 1,000 s são `tier 1,7 + Flash` (o `return` da busca com `Flash` em `t`) —
  exatamente o teto de 1,0 s pedido, e são 0,5 % da cena.

### A.5 Duração total esperada

| parcela | BFS | DFS |
|---|---|---|
| plays base (n × 0,40) | 664,4 | 487,2 |
| extra de Flash (n × 0,0667) | 14,8 | 8,8 |
| pausa 0,55 (n × 0,20) | 234,8 | 170,6 |
| pausa 1,0 (n × 0,3333) | 158,3 | 112,3 |
| pausa 1,7 (n × 0,5333) | 6,4 | 14,9 |
| trocas de aba (16 × 0,2667) | 4,3 | 4,3 |
| montagem + `fechar` + `limpar` | 7,2 | 7,2 |
| **total** | **≈ 1 090 s = 18,2 min** | **≈ 805 s = 13,4 min** |

Medido por simulação passo a passo (incluindo a regra A.3): **18,7 min** e **13,8 min**.
Adote **18,7 / 13,8 min** como alvo (a diferença é a quantização de frame, ±2 %).

> **Custo declarado**: o V1 tinha 11,8 / 8,0 min. O pedido de 0,5–1,0 s por linha **implica**
> ~16,6 min só de plays no BFS (1661 × 0,60). Não existe versão mais lenta e mais curta.
> Botão documentado (não aplicar sem pedido): `play=0.33` ⇒ 0,53 s/linha e 15,6 min.

---

## B. TIPOGRAFIA E PAGINAÇÃO DO CÓDIGO

### B.1 Constantes

```python
COLUNAS_MAX = 82          # limite de colunas por linha física (quebra em espaço)
MAX_LINHAS_PAGINA = 23    # linhas FÍSICAS por página
FONTE_CODIGO = 24         # fonte nativa do Code (base do pt efetivo)
```

### B.2 Conta da altura (por que 23)

- Moldura: 4,55 de altura; padding topo 0,12 + base 0,12 ⇒ **4,31 úteis**.
- Cabeçalho (fonte 11 + respiro): **0,28** ⇒ **4,03** para o `Code`.
- Altura de linha do `Code` a fonte 24: **0,3737** (medido: 13,827 / 37 linhas).
  > Nota: 0,384 é o **passo entre bases** (13,827 / 36); a altura total de `n` linhas é
  > `n × 0,3737`. Para dimensionar a página vale o segundo (é o que o `Code` ocupa).
- `23 × 0,3737 = 8,595` ⇒ escala de altura `4,03 / 8,595 = 0,4689`.

### B.3 Conta da largura (por que 82 colunas)

- Largura útil: `7,86 − 0,16 − 0,16 = 7,54`.
- Gutter próprio (3 dígitos a fonte 24 = 0,593) + respiro 0,14 ⇒ **0,733**.
- Maior página medida a 82 colunas: **15,63** de `Code` ⇒ total **16,36**.
- Escala de largura: `7,54 / 16,36 = 0,4608`.

### B.4 Escala única e fonte efetiva

```
escala = min(0,4689, 0,4608) = 0,4608
fonte efetiva = 24 × 0,4608 = 11,06 pt
```

**11,06 pt** (V1: 6,76 pt) — **+64 %**. Piso de teste do validador: **10,5 pt**.
A escala é calculada **uma vez** pela maior **página** (não pela maior função) e vale para
todas as páginas das duas cenas. Sem zoom na troca.

Prova com o `__init__` de 37 linhas: vira **2 páginas** de 18 e 19 linhas físicas
(`28–45` e `46–64`), ambas abaixo de 23 ⇒ não é mais ele que manda na escala.

### B.5 Quebra de linha longa (o que libera a fonte)

- Quebra **só** quando `len(linha) > 82`, no **último espaço antes da coluna 82**
  (`textwrap.wrap(..., width=82, subsequent_indent=indent+4, break_long_words=False,
  break_on_hyphens=False)`).
- A continuação recebe `indentação original + 4` espaços.
- **Nada é removido**: `"".join(pedaços).split() == linha.split()` (invariante do validador).
- Linhas afetadas (medido): `is_feasible` 111 (128 ch), `check` 153 (116 ch),
  `validate` 71 (93 ch), `FlowNetwork.__init__` docstring (79 ch), `add_residual_flow_to`
  77 ch. Total: **6 linhas quebradas** por cena.

### B.6 Numeração de linhas (gutter próprio)

`Code(..., add_line_numbers=False)` + gutter desenhado pela cena:

- Um `Text(str(lineno), font_size=24, color="#8d99ae")` por **linha-fonte** da página,
  alinhado à direita em `x = code.get_left()[0] - 0,14`, na altura da **primeira linha
  física** daquela linha-fonte.
- Linhas de continuação **não** recebem número.
- O gutter entra no `VGroup` de conteúdo **antes** do `scale(escala)` ⇒ escala junto.
- **Desvio declarado**: `line_numbers_from` não pode ser usado com quebra de linha (numeraria
  a continuação). O número exibido continua sendo o **real** do arquivo; o primeiro número
  da página é o da primeira linha-fonte da página.

### B.7 Paginação (fronteira de comando, nunca no meio de bloco)

```python
# candidatos: linhas físicas que iniciam um comando DIRETO do corpo da função
# (ast: FunctionDef.body, i.e. indentação de nível 1 — nunca dentro de for/if/while)
cand = [i for i in range(1, len(fis))
        if fis[i].lineno in marcas_corpo and fis[i-1].lineno != fis[i].lineno]

# guloso: maior candidato que ainda cabe em MAX_LINHAS_PAGINA
while ini < len(fis):
    if len(fis) - ini <= MAX_LINHAS_PAGINA:
        paginas.append(fis[ini:]); break
    opcoes = [c for c in cand if ini < c <= ini + MAX_LINHAS_PAGINA]
    fim = max(opcoes) if opcoes else ini + MAX_LINHAS_PAGINA   # fallback declarado
    paginas.append(fis[ini:fim]); ini = fim
```

- **Nunca** quebra dentro de `for`/`while`/`if` (só em comando de nível 1 do corpo).
- Fallback (comando de nível 1 maior que 23 linhas): corta duro em 23 e o validador
  **falha** — hoje não ocorre (o maior comando de nível 1 tem 16 linhas: o `while` de
  `__init__`, linhas 46–61).
- A página **contém a linha executada** por construção: as páginas particionam as linhas
  da função.

**Páginas medidas** (BFS 17 / DFS 18):

| função | páginas | faixas |
|---|---|---|
| `FordFulkerson.__init__` | 2 | 28–45 · 46–64 |
| `in_cut` | 1 | 66–68 |
| `validate` | 1 | 70–72 |
| `has_augmenting_path` | 1 | 74–95 |
| `excess` | 1 | 97–105 |
| `is_feasible` | 2 | 107–123 · 124–130 |
| `check` | 2 | 132–147 · 148–156 |
| `FlowNetwork.__init__` | 2 | 115–137 · 138–145 |
| `add_edge` / `adj` / `other` / `residual_capacity_to` | 1 cada | — |
| `add_residual_flow_to` | 1 | 71–88 |

(DFS: `dfs` 1 página 85–98; `is_feasible` 110–126 · 127–133; `check` 135–150 · 151–159.)

### B.8 Histerese e flicker (medido)

- A página é função **pura** da linha executada ⇒ não existe ambiguidade nem "pisca".
- **Medido**: 597 trocas de página no BFS (596 de função + **1** avanço `check` 1→2) e
  419 no DFS. **Voltas de página (k → k−1 na mesma função): 0 nas duas cenas.**
- Como 0 ≤ 8, **não é preciso folga de 1 linha**. A regra de quebra em comando de nível 1
  já elimina o caso clássico (laço partido entre páginas).

### B.9 Cabeçalho de cada página

Fonte **11** (medido: 6,68 un. no BFS e **7,32** no DFS, ambos ≤ 7,54; a fonte 12 estoura
em 7,98 no DFS). Cor `#48cae4`. Uma linha, `aligned_edge=LEFT`.

```
{nome} · {arquivo_curto}:{inicio}–{fim} · p.{k}/{n}{sufixo}
```

- `arquivo_curto` = só o nome do arquivo (`ford_fulkerson.py`), **sem** `algs4/`.
- Toda função exibe `p.1/1` quando tem uma única página.
- `sufixo` depende **da troca**, não de `k`:
  - página `k` entrando vinda de `k-1`: ` · ▸ continuação da p.{k-1}/{n}`;
  - página `k` voltando vinda de `k+1`: ` · ◂ volta da p.{k+1}/{n}`;
  - página `k` sem troca (inicial, permaneceu ou nunca alcançada): **sem sufixo**.
- Se a página `k` nunca é alcançada por uma troca, **não** se inventa marcador.

Exemplos exatos:

```
FordFulkerson.has_augmenting_path · ford_fulkerson.py:74–95 · p.1/1
FordFulkerson.__init__ · ford_fulkerson.py:28–64 · p.1/2
FordFulkerson.__init__ · ford_fulkerson.py:28–64 · p.2/2 · ▸ continuação da p.1/2
FordFulkerson.__init__ · ford_fulkerson.py:28–64 · p.1/2 · ◂ volta da p.2/2
FlowNetwork.__init__ · flow_network.py:115–145 · p.1/2
FordFulkerson.check · ford_fulkerson.py:132–156 · p.2/2 · ▸ continuação da p.1/2
```

### B.10 Troca de página (dois plays, indicador por página)

```python
if self.codigo.mudou(passo):          # (funcao, pagina) diferente
    sai, entra = self.codigo.trocar(passo)
    self.play(*sai)                   # 1º play: FadeOut(pagina antiga + indicador antigo)
    self.play(*entra)                 # 2º play: FadeIn(pagina nova + indicador novo)
```

- **Nunca** `Succession` num play só.
- **Indicador por página**: cada página tem o seu `SurroundingRectangle`, já posicionado na
  linha executada antes do `FadeIn` ⇒ nunca existe indicador órfão.
- **Grupo estável = só a moldura** (`VGroup(self.moldura)`); conteúdo, gutter e indicador
  são mobjects de cena (top-level) ⇒ zero texto fantasma.
- `run_time = RITMO["fade"]` nos dois plays.

---

## C. ABAS DE ESTRUTURA (5 abas)

### C.1 Geometria — e o conflito com o número pedido

O pedido dizia "painel 6,70 × 2,90 centrado em (−3,35, −2,30)". **Não cabe**:

- topo em `−2,30 + 1,45 = −0,85` **invade** a moldura do código (fundo em `−1,10`);
- base em `−3,75` **sai** do safe frame (`−3,72`).

**Regra escolhida** (mantém o contrato de layout do V1 e ganha o que dá):

```python
ESTRUTURA = dict(centro=(-2.63, -2.51), largura=7.86, altura=2.42)
```

| bloco | x | y | dimensão |
|---|---|---|---|
| **Painel** | −6,56 → 1,30 | −3,72 → −1,30 | 7,86 × 2,42 |
| **Trilho de abas** | −6,48 → −5,18 | −1,40 → −3,20 | 1,30 × 1,80 |
| **Corpo da aba** | −5,08 → 1,20 | −1,40 → −3,20 | 6,28 × 1,80 |
| **Faixa de contadores** | −6,48 → … | y = −3,50 | 1 linha, fonte 11 |

Folgas: código → estrutura **0,20**; estrutura → safe frame **0,00** (borda em −3,72);
gutter central 1,30 → 1,50 = **0,20**; trilho → corpo **0,10**.

### C.2 Trilho vertical × barra horizontal (avaliação pedida)

| opção | altura do corpo | cabe `adj` (6 linhas × 0,26 = 1,56)? |
|---|---|---|
| barra horizontal de 2 linhas (5 abas) | 2,42 − 0,06 − 0,60 − 0,10 − 0,30 = **1,36** | **não** (1,56 > 1,36) |
| **trilho vertical (escolhido)** | **1,80** | **sim** (1,56 ≤ 1,80) |

**Decisão: trilho vertical à esquerda.** 5 abas de **1,30 × 0,32**, gap 0,05, centros em
`y = −1,56, −1,93, −2,30, −2,67, −3,04`. Rótulo a **fonte 10** (piso pedido), centralizado;
"Rede residual" mede **0,96** ≤ 1,14 úteis (1,30 − 0,16). Aba ativa: borda `#48cae4` 1,6 +
fill `#1f2637` + texto branco; inativa: borda `#8d99ae` 1,2 + fill `#0f111a` + texto
`#8d99ae`.

### C.3 As 5 abas

```python
ABAS = {
  "edmonds_karp":       (("rede", "Rede residual"), ("busca", "Fila (BFS)"),
                         ("marcados", "marked[]"), ("edge_to", "edgeTo[]"), ("adj", "adj[]")),
  "ford_fulkerson_dfs": (("rede", "Rede residual"), ("busca", "Pilha (DFS)"),
                         ("marcados", "marked[]"), ("edge_to", "edgeTo[]"), ("adj", "adj[]")),
}
```

Ordem fixa no trilho: `rede`, `busca`, `marcados`, `edge_to`, `adj`.

### C.4 Regra determinística da aba ativa (cobre 100 % dos passos)

Avaliada **passo a passo, na ordem do trace**, com herança do chamador:

```python
def aba_do_passo(passo, aba_anterior) -> str:
    fn, ln = passo.funcao, passo.linha
    if fn in ("FlowNetwork.__init__", "FlowNetwork.add_edge"):
        return "adj"                       # janela de montagem da Bag
    if fn == "FlowNetwork.adj" or fn.startswith("FlowEdge."):
        return aba_anterior                # herda do chamador (ver tabela)
    if fn.endswith("has_augmenting_path") or fn.endswith(".dfs"):
        return "busca"
    if fn.endswith("__init__"):            # FordFulkerson.__init__
        return "edge_to" if 46 <= ln <= 53 else "rede"
    if fn.endswith(("check", "in_cut", "validate")):
        return "marcados"
    return "rede"
```

Depois, **fusão de runs curtos** (histerese da aba, uma passada da esquerda para a direita):

```python
# todo run de comprimento 1 vira a aba anterior (i > 0)
```

Tabela de cobertura (o que cada faixa mostra):

| módulo / função | faixa | aba | por quê |
|---|---|---|---|
| `flow_network.__init__` | 115–145 | `adj` | a Bag está sendo montada (parcial) |
| `flow_network.add_edge` | 151–158 | `adj` | `adj[u].append(e)` / `adj[v].append(e)` |
| `flow_network.adj` | 160–162 | **herda** | getter: mostra a estrutura do chamador |
| `flow_edge.other` | 55–61 | **herda** | idem |
| `flow_edge.residual_capacity_to` | 63–69 | **herda** | idem |
| `flow_edge.add_residual_flow_to` | 71–88 | **herda** | idem |
| `has_augmenting_path` (BFS) | 74–95 | `busca` | a fila é o sujeito |
| `dfs` (DFS) | 85–98 | `busca` | a pilha de recursão é o sujeito |
| `__init__` linhas **46–53** (gargalo) | 46–53 | `edge_to` | percorre `edgeTo[v]` para achar `b` |
| `__init__` linhas **56–61** (aumento) | 56–61 | `rede` | o fluxo muda: a tabela residual é o sujeito |
| `__init__` 28–45 e 63–64 | — | `rede` | setup / `assert check` |
| `check` | 132–156 | `marcados` | verifica o corte (lado S = `marked`) |
| `in_cut` | 66–68 | `marcados` | lê `marked[v]` |
| `validate` | 70–72 | `marcados` | chamado por `in_cut` (herança de fase) |
| `is_feasible` / `excess` | — | `rede` | capacidade/fluxo, não `marked` |

**Cobertura medida** (nenhum passo sem aba):

| aba | BFS | DFS |
|---|---|---|
| `adj` | 83 | 83 |
| `busca` | 825 | 382 |
| `rede` | 526 | 526 |
| `edge_to` | 120 | 120 |
| `marcados` | 107 | 107 |
| **trocas de aba** | **16** | **16** |

16 trocas × 0,2667 s = 4,3 s por cena. Sem a fusão de runs seriam 27 (e `marcados` cairia
para 16 passos — frágil); com `min_run=3` `marcados` **desapareceria** (0 passos) e o QA
"cada aba usada" falharia. **`min_run = 2` é o valor do contrato.**

### C.5 Conteúdo de cada aba (corpo 6,28 × 1,80, origem `x0 = −5,00`, `y_topo = −1,46`)

Todas as abas têm **caption** (fonte 9, `#8d99ae`) na primeira linha do corpo, em
`y = −1,52`, `aligned_edge=LEFT` em `x0`.

**`rede` — Rede residual** (existente, re-encaixada)
- Caption: `Rede residual · C, f, res→, res←`
- 2 metades × 4 arestas (ordem do arquivo). Colunas: `aresta 0,85 · C 0,42 · f 0,42 ·
  res→ 0,50 · res← 0,50` = 2,69 por metade; metades em `x0` e `x0 + 3,10`.
- Cabeçalho de coluna em `y = −1,80` (fonte 9); 4 linhas a partir de `y = −2,06`, passo
  0,28. Chip 0,22 de altura. `res→ = 0` em `#06d6a0`.

**`busca` — Fila (BFS) / Pilha (DFS)** (existente, re-encaixada)
- Caption: `Fila (BFS) · ordem real` / `Pilha (DFS) · caminho de recursão`
- Chips 0,42 × 0,30, passo 0,54, `y = −2,30`; `frente`/`fim` (BFS) ou `base`/`topo` (DFS)
  em `y = −2,02` e `y = −2,60` (rótulos em palavra — `↓`/`↑` viram "l"/"1" a fonte 9).
- Bloco de informação à direita em `x = x0 + 3,60`: `edgeTo …` (fonte 10), `marcados {…}`
  (`#80ed99`), `inspeções n` (`#8d99ae`), linhas em `y = −2,02 / −2,30 / −2,58`.

**`marcados` — `marked[]`**
- Caption: `marked[] · {k}/6 vértices · alcançados na residual`
- 6 chips de 0,62 × 0,30, passo 0,72, `y = −2,20`, `x` de `x0` a `x0 + 3,60`.
  Marcado: fill `#80ed99` op. 0,22 + borda `#80ed99` 1,6 + texto branco.
  Não marcado: fill `#1f2637` + borda `#8d99ae` 1,0 + texto `#8d99ae`.
- À direita (`x = x0 + 3,90`): `S = {0, 2}` quando `estado["corte"]` existe, senão `—`.

**`edge_to` — `edgeTo[]`**
- Caption: `edgeTo[] · caminho s→t`
- Tabela 6 linhas × 3 colunas: `v` (0,55) · `pai` (0,75) · `nível (derivado)` (1,10).
  Cabeçalho em `y = −1,80`; linhas a partir de `y = −2,00`, passo 0,22 (última em −3,10).
  `pai` = `—` quando `edge_to[v]` é `None`; `nível` = `—` idem.
- À direita (`x = x0 + 2,70`): `caminho s→t` em `#ffd166` (fonte 10) com
  `0→2→4→5` ou `—`, e `b = 1` abaixo.
- **`nível` é rotulado "derivado"** no cabeçalho da coluna: não existe `distTo` em fluxo
  máximo; a profundidade é `nível[v] = nível[pai] + 1` a partir de `edge_to`.

**`adj` — `adj[]` (Bag real, ordem LIFO)**
- Caption: `adj[] · Bag (ordem LIFO) · {n}/8 arestas` (`n` = Σ `len(adj[v])`; na montagem
  cresce 0→8).
- 6 linhas (uma por vértice), passo 0,25, a partir de `y = −1,78` (última em −3,03). Rótulo
  do vértice `0:` (fonte 10, `#8d99ae`) em `x0`; chips a partir de `x0 + 0,42`, passo 0,66.
- Chip 0,62 × 0,24, texto **fonte 9**: `{sinal}{w} {f:g}/{C:g}` com
  `sinal = ">"` se a aresta **sai** de `u` (`e.from_() == u`) e `"<"` se **entra**
  (`e.to() == u`). Ex.: `>1 0/2`, `<0 2/3`.
- Legenda da seta na caption: `> sai de u · < entra em u` (ASCII — glifo de seta a fonte 9
  não é confiável, ver §4.1 do relatório do codificador).
- Ordem dos chips = **ordem real da Bag** (`estado["adj"][v]`), nunca ordenada.
- Grau máximo medido: 3 ⇒ 3 chips = 1,98 ≤ 6,28. Cabe com folga.
- **Janela de montagem**: nos passos de `FlowNetwork.__init__`/`add_edge` a Bag está
  parcial; a aba mostra exatamente o que existe (nunca "completa" antes da hora).

### C.6 Troca de aba (dois plays)

```python
if troca:
    self.play(*[FadeOut(m, run_time=RITMO["fade"]) for m in aba_antiga.todos()])
    self.add(*novos)
    self.play(*[FadeIn(m, run_time=RITMO["fade"]) for m in novos])
```

- `todos()` devolve a lista **viva** (correção do bug de fantasma do V1 — manter).
- **Nunca** as duas abas no mesmo frame.
- O estilo das abas (borda/fill/texto) muda no **primeiro** play (junto com o fade-out).

### C.7 Cores — nenhuma cor nova

| papel | hex | onde nas abas |
|---|---|---|
| `alcancado` | `#80ed99` | chip marcado, `S = {…}`, `marcados {…}` |
| `caminho` | `#ffd166` | caminho `s→t` na aba `edge_to` |
| `exame` | `#e879f9` | borda do chip em foco (`rede`, `adj`) |
| `saturada` | `#06d6a0` | `res→ = 0` na tabela |
| `fora` | `#8d99ae` | texto neutro / chip não marcado |
| `fluxo` | `#4cc9f0` | (só no grafo) |
| `reversa` | `#ef476f` | (só no grafo) |

Estruturais (`#0f111a`, `#151824`, `#1f2637`, `#2a2f45`, `#48cae4`, `#f2f4f8`) não entram
no contrato de legenda. **A legenda de 7 papéis continua válida e o QA de pixels exige
7/7 usados** — as abas não introduzem cor semântica nova.

---

## D. IMPACTO NOS VALIDADORES

### D.1 `validate_flow_layout.py`

**Trocar**
- `FONTE_MINIMA = 6.5` → **`FONTE_MINIMA = 10.5`** (alvo 11,06; piso de teste 10,5).

**Manter (continua valendo)**
- gutter central ≥ 0,20; colisões `PARES`; safe frame; rótulo em todo nó; `f/C` em toda
  aresta; legenda fiel nos dois sentidos; `todos()` vivo (anti-fantasma); painéis dentro
  dos bounds.

**Adicionar (especificação, não implementação)**
1. **Página**: `max(len(p) for p in paginas) <= 23`; toda linha executada cai em
   **exatamente uma** página (`sum(1 for p in paginas if linha in p) == 1` para todo
   `Step`); o conjunto de páginas particiona as linhas da função (sem buraco nem
   sobreposição).
2. **Cabeçalho**: sempre contém `p.{k}/{n}` (inclusive `p.1/1`); o sufixo é o de §B.9 e
   depende **só da troca real**: entrada `k-1 → k` ou `k+1 → k`. Página sem troca, inicial
   ou nunca alcançada fica **sem sufixo**; `n == 1` também não tem sufixo. Largura ≤ 7,54.
3. **Quebra de linha**: para cada linha-fonte quebrada,
   `"".join(pedaços).split() == original.split()`; nenhuma linha física > 82 colunas.
4. **Gutter**: um número por linha-fonte, consecutivo a partir do início da página;
   nenhum número em linha de continuação; `int(texto) == lineno` real.
5. **5 abas**: `set(ABAS[alg]) == {"rede","busca","marcados","edge_to","adj"}`;
   `len(estrutura.abas) == len(passos)`; **cada aba tem ≥ 8 passos** (medido: mínimo 83);
   `aba_ativa` nunca vazia; a sequência é **idêntica** à de `aba_do_passo` + fusão
   `min_run=2` (determinismo).
6. **Troca em 2 plays**: a troca de aba e a de página devolvem **duas** listas
   (`sai`, `entra`) e o `play_step` faz dois `self.play` — verificar por introspecção do
   retorno (`len(sai) > 0 and len(entra) > 0`) e que `sai` e `entra` não compartilham
   mobject.
7. **`adj` na ordem real**: `[c.w for c in aba_adj.chips[v]] == [e["w"] for e in
   estado["adj"][v]]` em 3 passos (início/meio/fim) — nunca ordenado.
8. **`edge_to`**: `pai` e `nível` batem com `estado["edge_to"]`; `None` → `—`; o caminho
   `s→t` exibido é o de `estado["caminho"]`.
9. **`marcados`**: `k` do caption == `len(estado["marcados"])`; chips acesos == conjunto.
10. **Sem cor nova**: `set(hex) ⊆ PALETA ∪ ESTRUTURAIS` em todos os mobjects das abas.

### D.2 `validate_flow_videos.py`

- `ALVO = {"edmonds": 18.7 * 60, "ford": 13.8 * 60}` (era 10,6 / 8,0).
- Manter a folga de 40 % (aceita 11,2–26,2 min no BFS e 8,3–19,3 no DFS).
- **Novo**: amostrar **1 frame por aba** (5 frames extras) e exigir que a cor semântica
  daquela aba apareça **fora** da caixa do guia (ex.: `#80ed99` no frame da aba
  `marcados`, `#ffd166` no frame da aba `edge_to`).
- **Novo**: no frame da aba `adj`, contar pixels de `#1f2637` (chips) > 0 — prova que a
  aba não está vazia.
- Manter: último frame não preto, bandas de texto, 7/7 da paleta, `#4a4e69` ausente,
  `#f2f4f8` só em rótulo.

### D.3 `validate_flow_scenes.py`

**Não muda** (trace, golden, determinismo, `stages_fluxo.json` com o mesmo SHA).

---

## E. INTROS (item OPCIONAL e separado)

**Não tocar nas duas cenas de execução por causa disto.** Se o usuário pedir, aplicar só
em `EdmondsKarpIntro_new` / `FordFulkersonIntro_new`:

1. **Pré-preenchimento**: o painel esquerdo entra **junto** com o título
   (`FadeIn(painel)` no mesmo play do cabeçalho, `run_time=0.8`) — elimina os ~2,5 s de
   lado esquerdo vazio (hoje o painel só aparece no passo 78, ~4 s depois do título).
2. **Blocos acumulando**: os 4 `_bloco` entram **um a um** (`FadeIn(bloco, shift=UP)`,
   `run_time=0.45`, `self.wait(0.25)` entre eles) e **ficam**; hoje entram como um
   `VGroup` único e depois somem de uma vez (`FadeOut(lista)`).
3. **Grafo mais cedo**: `FadeIn(grafo.mobject)` em paralelo ao 2º bloco (o lado direito
   fica vazio até o passo 84).
4. **Ritmo**: `wait` de leitura 1,2 → 1,6 s nos slides de conceito; nada além disso.

Custo: +6 s por intro. Nenhuma mudança em `flow_common.py`.

---

## F. Lista de mudanças por arquivo/função (para o `codificador`)

### `src/flow_common.py`

| símbolo | mudança |
|---|---|
| `RITMO` | novos valores de §A.1 (múltiplos de 1/15) |
| `ESTRUTURA` | `centro=(-2.63, -2.51)`, `altura=2.42` |
| **novo** `COLUNAS_MAX = 82`, `MAX_LINHAS_PAGINA = 23` | constantes de paginação |
| **novo** `paginar_funcao(funcao) -> list[PaginaCodigo]` | §B.7 (ast + textwrap + guloso) |
| **novo** `PaginaCodigo` (dataclass) | `funcao, k, n, linhas_fisicas, mapa_linha→row, texto, inicio, fim` |
| `CodePanel.__init__` | construir **uma `Code` por página** (`add_line_numbers=False`), gutter próprio, escala única pela maior página, `fonte_efetiva` |
| `CodePanel._rotulo` | §B.9 (arquivo curto + `p.k/n` + marcador) |
| `CodePanel._view` → `_pagina` | devolve `(funcao_idx, pagina_idx)` |
| `CodePanel.mudou/trocar/destacar` | operar por página; indicador por página; `_posicionar` usa `mapa_linha→row` |
| `ABAS` | 5 abas (§C.3) |
| **novo** `aba_do_passo(passo, aba_anterior)` + `fundir_runs(abas, 2)` | §C.4 |
| `calcular_abas` | passa a devolver a sequência de 5 abas (substitui a lógica de janela) |
| `EstruturaPanel._montar_abas` | trilho vertical (§C.2) |
| **novo** `_AbaMarcados`, `_AbaEdgeTo`, `_AbaAdj` | §C.5 (mesma interface `construir/sincronizar/todos`) |
| `_AbaRede` | colunas e origem re-encaixadas (§C.5) |
| `_AbaBusca` | origem re-encaixada (§C.5) |
| `EstruturaPanel.preparar/atualizar` | 5 abas; contadores em `y=-3.50` |
| `FlowExecucaoBase.play_step` | `self.wait(max(0.0, pausa - extra))` (§A.3) |

### `src/edmonds_karp_scene_new.py` / `src/ford_fulkerson_scene_new.py`

- **Nenhuma mudança obrigatória** nas cenas de execução (herdam tudo de `flow_common`).
- Intros: só se o item E for aprovado.

### `validate_flow_layout.py` / `validate_flow_videos.py`

- §D.1 e §D.2.

---

## G. Autoconferência (checklist `manim-qa-visual`)

| # | critério | resultado |
|---|---|---|
| 1 | todo nó tem `str(v)` | 6/6 (inalterado) ✓ |
| 2 | toda aresta tem `f/C` com fundo opaco | 8/8 (inalterado) ✓ |
| 3 | rótulo × rótulo / nó / aresta alheia | 0 colisões (inalterado) ✓ |
| 4 | painel × painel (gutter ≥ 0,20) | 0,20 ✓ |
| 5 | código × estrutura | 0,20 ✓ |
| 6 | estrutura × safe frame | borda em −3,72 = limite ✓ |
| 7 | legenda: 7 papéis usados / 7 itens | ✓ (abas não criam cor) |
| 8 | estados não separados só por cor | ✓ (símbolo + traço + sentido) |
| 9 | troca de view/aba em **dois** plays | ✓ (§B.10, §C.6) |
| 10 | indicador por página, sem órfão | ✓ (§B.10) |
| 11 | grupo estável só com a moldura | ✓ |
| 12 | fonte efetiva ≥ 10,5 pt | **11,06** ✓ |
| 13 | toda linha executada em exatamente 1 página | ✓ (partição) |
| 14 | cabeçalho com `k/n` e marcador | ✓ (§B.9) |
| 15 | 5 abas, cada uma usada | ✓ (mín. 83 passos) |
| 16 | aba ativa nunca vazia | ✓ (regra total) |
| 17 | `adj` na ordem real da Bag | ✓ (§C.5) |
| 18 | último frame não preto | fecho com corte (inalterado) ✓ |
| 19 | nada fora de x ∈ [−6,56; 6,79], y ∈ [−3,72; 3,55] | ✓ |
| 20 | texto dentro do quadro | cabeçalho 7,32 ≤ 7,54 ✓ |

Pendente para o codificador provar com número: #3–#5 no código real, #12–#17 por
introspecção, e o QA de pixels.

---

## H. Riscos

| risco | probabilidade | mitigação no plano |
|---|---|---|
| **Flicker de página em laço** | **baixa** — medido **0 voltas** de página nas duas cenas | quebra só em comando de nível 1 do corpo; validador cobra `voltas == 0` |
| **Aba ativa ambígua** | baixa — regra total (todo passo casa um `if`) | validador exige `len(abas) == len(passos)` e cada aba ≥ 8 passos |
| **Colisão na barra de abas** | média — 5 rótulos em 1,30 de largura | fonte 10, "Rede residual" mede 0,98 ≤ 1,14 úteis; validador mede a caixa de cada aba |
| **Custo de render** | **alto** — 18,7 min de vídeo a 15 fps ≈ 16 800 frames; o V1 levou 123 min no 480p | render **só 480p** primeiro; a paginação não aumenta o nº de frames (só +2 trocas); `-ql` com `--media_dir media_dev_fluxo` |
| **Gutter próprio dessincroniza** | média — é código novo | validador #4 (um número por linha-fonte, consecutivo, igual ao real) |
| **Quebra de linha "cortar" código** | baixa | invariante `"".join(pedaços).split() == original.split()` |
| **`marcados` com poucos passos** | média — 107 passos, mas depende da fusão | `min_run=2` fixo no contrato; validador exige ≥ 8 |
| **Duração 18,7 min** | certo | declarado; botão `play=0.33` documentado (15,6 min) |

---

## I. Resumo de uma linha

Código em **17/18 páginas** de ≤ 23 linhas e ≤ 82 colunas a **11,06 pt** (troca em dois
plays, indicador por página, cabeçalho `p.k/n` com sufixo de direção da troca), **5 abas** em
trilho vertical (`rede`, `busca`, `marcados`, `edge_to`, `adj`, 16 trocas por cena), ritmo
**0,60–1,00 s por linha** ⇒ **18,7 min (BFS)** e **13,8 min (DFS)**.

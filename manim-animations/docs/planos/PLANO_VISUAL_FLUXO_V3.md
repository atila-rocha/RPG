# PLANO VISUAL V3 — Fluxo Máximo (Edmonds-Karp/BFS e Ford-Fulkerson/DFS)

Fase: **VISUAL (revisão 3)**. Substitui `PLANO_VISUAL_FLUXO_V2.md` **apenas nos pontos aqui
tratados**; tudo o que não é citado (ritmo A.1–A.3, paleta de 7 papéis, 5 abas em trilho,
paginação por comando de nível 1, troca em dois plays, fecho do corte) continua valendo
**sem alteração**. O V2 fica como registro do que foi entregue.

Entrada: `PLANO_VISUAL_FLUXO_V2.md`, `src/flow_common.py`, `src/flow_record.py`,
`validate_flow_layout.py`, `dataset/tinyFN.txt` (V=6, E=8, s=0, t=5) e o relatório da fase
`algoritmo` (Gate 0 6/6, `stages` sha `e9975393292db428e9570e010aa23868235f6c807da3ccc33f6224a1e3e1814f`).

Data: 2026-11-13. **Todos os números abaixo foram medidos** com o Manim 0.22.0 do `.venv`
do projeto e com o trace real (`coletar_detalhado`), não estimados.

Este documento é contrato: o `codificador` implementa o que está aqui. Divergência sem
pedido volta para correção.

---

## 0. Resumo executivo (feedback → decisão → número medido)

| # | feedback literal | decisão | número medido |
|---|---|---|---|
| 1 | "Faltou a função validatevertex() no painel codigo dinamico" | view de 1 página (3 linhas-fonte / 4 físicas), **todos os 73/63 passos**; aba herdada; selo contador (§E) | 16 chamadas de `add_edge` + 57/47 de `adj`; cabeçalho 2 linhas |
| 2 | "Faltou ter um guia visual para explicar o que é C, f, res→, res←" | **linha de guia fixa no rodapé da aba de estrutura** (opção i), contextual, com a **notação `C_f`** do guia de estudo | fonte 10, pior largura **5.27** ≤ 6.20 |
| 3 | "use parte 1 de 2" em vez de "p1/2" | `parte {k} de {n}` em **cabeçalho de 2 linhas** (não cabe em 1) | cont. atual 8.35 → linha 2 = **3.36**; fonte **11.06 pt** preservada |
| 4 | "não consigo ver quanto do fluxo passou e quanto a seta reversa tem" | bloco de **2 linhas** por aresta: `f/C` + `→C−f ←f` (**= `C_f(u,v)` / `C_f(v,u)`**) | bloco 0.59 × 0.33; **0 colisões** |
| 5 | "a seta às vezes cruza os quadrados no dfs, principalmente o topo" | **bug de id×índice** em `_AbaBusca._seta`; seta só no gutter entre chips | pilha máx. **4** (3 setas), gutter 0.24 |
| 6 | 73 repetições do `if` que nunca falha | **selo `validate_vertex {n}× · 0 violações`** no slot 5 do painel de estado + 1 Flash na 1ª chamada | fonte 10, 2.32 ≤ 4.89 |

**Duração: alvo RE-BASELINADO para 19.44 min (BFS) e 14.45 min (DFS)** — opção (a):
absorver. A view nova entra em todos os passos (fidelidade), e o cronômetro se ajusta ao
conteúdo, não o contrário. Valores exatos de `ALVO` em §F.2.

---

## A. GUIA VISUAL DE SÍMBOLOS (item 2)

### A.1 Decisão — opção (i), uma linha por aba

**Escolhida: (i) linha de guia fixa dentro do chrome da aba de estrutura**, em
`y = −3,30`, logo acima da faixa de contadores (`y = −3,50`).

Por que (e não as outras duas):

1. **Não rouba área do grafo nem sai do safe frame**: fica dentro do painel
   `−3,72 … −1,30`, no espaço hoje vazio entre o corpo (`−3,20`) e os contadores (`−3,50`).
2. **Persistente de verdade**: nasce em `EstruturaPanel.preparar` e só troca na troca de
   aba; fica na tela durante os 99–851 passos daquela aba. Nada precisa ser decorado.
3. **Contextual**: mostra só os símbolos da aba ativa (≤ 5,27 un. contra 6,20 úteis), o que
   mantém a fonte 10 legível a 480p. Uma legenda global passaria de 9 un. e cairia para
   fonte 8 — ilegível no 480p.

A legenda de **cores** (`GuiaVisual`, 7 papéis) **não é substituída**; o guia de símbolos é
outra dimensão (texto), como manda `manim-visual` §2.

### A.2 Textos — a notação OFICIAL do guia de estudo (`C_f`), medidos

Fonte única do material do aluno: `faculdade/grafos/Guia de Estudo Completo Fluxo Máximo em
Redes.md` (vault Obsidian; **o codificador não abre esse caminho** — o texto canônico está
aqui). A tela usa **exatamente** essa notação.

```python
GUIA_SIMBOLOS = {
    "rede":      "C = C(u,v) nominal · f = f(u,v) · res→ = C_f(u,v) = C−f · res← = C_f(v,u) = f",
    "busca_bfs": "frente = próximo a sair · fim = último a entrar",
    "busca_dfs": "base = primeiro da pilha · topo = chamada atual",
    "marcados":  "marked[v] = alcançado pela residual · S* = lado da fonte",
    "edge_to":   "edgeTo[v] = aresta que descobriu v · s = fonte · t = sumidouro",
    "adj":       "▸ sai de v · ◂ entra de v · chip = w · f/C",
}
```

| chave | largura a fonte 10 | margem |
|---|---|---|
| `rede` | **5.27** | 0.93 |
| `busca_bfs` / `busca_dfs` | 3.30 | 2.90 |
| `marcados` | 3.88 | 2.32 |
| `edge_to` | 4.55 | 1.65 |
| `adj` | 3.00 | 3.20 |

- `Text(..., font_size=10, color=COR_BORDA_NO)`, `move_to([X0_ESTRUTURA, −3.30, 0],
  aligned_edge=LEFT)`.
- Faixa vertical: topo `−3.234`, base `−3.366`. Folga até o conteúdo mais baixo do corpo
  (`edge_to` última linha em `−3.10`, altura 0.119 → base `−3.16`): **0,074**. Até o topo dos
  contadores (`−3.4275`): **0,062**. Base do painel `−3,72`: **0,354**. Nenhum conteúdo de
  aba muda de `y` (sem reflow).

### A.3 Objeto e ciclo de vida

- **Dono: `EstruturaPanel`** (um único `Text`), não as 5 classes de aba.
- `preparar()` devolve `[..., self.guia]`; `atualizar()` na troca de aba põe
  `FadeOut(self.guia)` em `sai` e o novo guia em `novos` (entra com o corpo da aba).
- O guia **não** entra em `todos()` de aba alguma (é chrome do painel, como os contadores).

### A.4 Correção que o guia revelou (caption de `adj`)

`_AbaAdj._texto_caption` (l.2146-2151) monta hoje

```
adj[] · Bag real (LIFO) · 12 entradas (2E=16) · em construção · w · f/C · ▸ sai de v · ◂ entra de v
```

que mede **7.12** a fonte 9 — **estoura** os 6.20 do corpo (já hoje). Com o guia novo:

```
adj[] · Bag real (LIFO) · {n} entradas (2E=16)[ · em construção]
```

(3.02 a fonte 9). Os símbolos `▸ ◂ w f/C` passam para o guia.

### A.5 Cobertura (conferência com o pedido)

| símbolo | onde aparece | onde é explicado |
|---|---|---|
| `C`, `C(u,v)` | aba `rede` (coluna), grafo `f/C` | `rede` |
| `f`, `f(u,v)` | aba `rede`, grafo `f/C` | `rede` |
| `res→` = `C_f(u,v)` = `C−f` | aba `rede`, grafo `→` | `rede` |
| `res←` = `C_f(v,u)` = `f` | aba `rede`, arco tracejado, grafo `←` | `rede` |
| `marked[]`, `S*` | aba `marcados`, estado | `marcados` |
| `edgeTo[]`, `s`, `t` | aba `edge_to`, estado | `edge_to` |
| `▸ ◂`, `w`, `f/C` | aba `adj` | `adj` |
| fila/pilha, `frente/fim`, `base/topo` | aba `busca`, estado | `busca_bfs` / `busca_dfs` |

---

## B. PAGINAÇÃO EM PORTUGUÊS (item 3)

### B.1 O problema medido

Com `p.{k}/{n}` o pior cabeçalho do DFS era 7.32 (≤ 7.54). Com `parte {k} de {n}`:

| caso | largura | veredito |
|---|---|---|
| pior **base** (`FordFulkersonDFS.is_feasible · ford_fulkerson_dfs.py:110–133 · parte 2 de 2`) | **6.32** | cabe |
| pior **base + " · ▸ continuação da parte 1 de 2"** | **8.35** | **estoura 7.54** |
| `FordFulkersonDFS.check` + continuação | 8.00 | estoura |
| `FordFulkersonDFS.__init__` + continuação | 7.91 | estoura |
| `FordFulkerson.is_feasible` + continuação | 7.71 | estoura |

Não existe sufixo curto que salve a linha única: `" · ▸ (da parte 1)"` mede 1.41 e
`6.32 + 1.41 = 7.72` > 7.54. Reduzir a fonte do cabeçalho está proibido (fonte única).

### B.2 Solução: cabeçalho de DUAS linhas (sempre)

```
linha 1: {nome} · {arquivo_curto}:{inicio}–{fim}
linha 2: parte {k} de {n}{sufixo}
```

- `Text` único com `"\n"` (Manim renderiza duas linhas; medido: altura **0.262** a fonte 11
  contra 0.118 de uma linha). `original_text` continua a string com `\n`, então
  `_atualizar_cabecalho` e o validador seguem comparando strings.
- Piores larguras: linha 1 = **6.32**, linha 2 = **3.36** — ambas ≤ 7.54.
- **Fonte preservada: 11.06 pt.** Com `altura_cabecalho = Text("x\ny", 11).height + 0.06 =
  0.322`: `(4.31 − 0.322) / 8.595 = 0.4640` (altura) contra `0.4609` (largura) ⇒ a **largura
  continua mandando**. Conteúdo total 0.322 + 3.96 = 4.28 ≤ 4.31.
- **Não** usar duas `Text`: `cabecalhos[i]` é um `Text` e `original_text` é o contrato.

### B.3 Textos exatos

| situação | linha 2 |
|---|---|
| sempre | `parte {k} de {n}` |
| página `k` vinda de `k−1` | `parte {k} de {n} · ▸ continuação da parte {k-1} de {n}` |
| página `k` vinda de `k+1` | `parte {k} de {n} · ◂ volta da parte {k+1} de {n}` |
| sem troca adjacente / `n == 1` | só `parte {k} de {n}` |

Exemplos (medidos 3.36 e 2.80):

```
FordFulkersonDFS.is_feasible · ford_fulkerson_dfs.py:110–133
parte 2 de 2 · ▸ continuação da parte 1 de 2
```
```
FordFulkerson.check · ford_fulkerson.py:132–156
parte 1 de 2 · ◂ volta da parte 2 de 2
```
```
FlowNetwork.validate_vertex · flow_network.py:147–149
parte 1 de 1
```

Regra de ouro do V2 mantida: o sufixo depende **só da troca real**; página nunca alcançada
não ganha marcador, e `n == 1` nunca ganha sufixo.

### B.4 `escala_codigo()` — mudança obrigatória

`src/flow_common.py` l.1029-1030 mede uma linha; passa a medir o pior caso real (2 linhas):

```python
altura_cabecalho = Text("x\ny", font_size=CodePanel.FONTE_CABECALHO).height
altura_cabecalho += CodePanel.BUFF_CABECALHO
```

Sem isso o conteúdo sai ~0.16 abaixo da moldura e o validador "conteudo de toda pagina
dentro da moldura" reprova.

---

## C. LEITURA DE FLUXO E REVERSA NO GRAFO (item 4a)

### C.1 Diagnóstico

Hoje cada aresta tem **um** `Text` `f/C` (fonte 13) e o arco reverso só ganha rótulo
(`res = f`) **no passo em que a reversa está em foco** (`animar`, l.775-792). Nos demais
passos o arco aparece sem número — e a caixa opaca do `f/C` (0,30 de altura, centrada no
arco deslocado 0,15) frequentemente **cobre o próprio arco**, que é o que o usuário
descreve como "não consigo ver quanto a seta reversa tem".

### C.2 Decisão: bloco de DUAS linhas por aresta (uma única caixa)

```
f/C                 ← linha 1, fonte 13, #f2f4f8
→{C−f} ←{f}         ← linha 2, fonte 11
```

Em notação do guia de estudo, a linha 2 é **`C_f(u,v)` e `C_f(v,u)`**:
`→` = `res→` = `C_f(u,v) = C−f` ("quanto ainda cabe de u para v"); `←` = `res←` =
`C_f(v,u) = f` ("quanto dá para devolver de v para u").

- **Linha 1** é o que já existe (fluxo / capacidade nominal).
- **Linha 2** dá as duas residuais de uma vez:
  - `→{C−f}`: `#06d6a0` quando é `0` (mesma semântica da aba `rede`), senão `#f2f4f8`.
  - `←{f}`: `#ef476f` quando `f > 0`, senão `#8d99ae` (não passa).
- A linha 2 aparece **sempre**, inclusive `←0` ("não passa" também é informação).
- **Nenhuma cor nova**: `#06d6a0` (`saturada`), `#ef476f` (`reversa`) e `#8d99ae` (`fora`) já
  estão na `PALETA`; a legenda continua 7/7 usada.

### C.3 Trade-off de notação medido (registro)

| rótulo na linha 2 | largura do bloco | colisões |
|---|---|---|
| `→3 ←1` (**escolhido**) | **0.59** | **0** |
| `Cf→3 ←1` | 0.70 | 1 |
| `C_f→3 C_f←1` | 1.00 | **5** |

A notação formal `C_f` **não cabe** como rótulo de aresta no grafo (1.00 de largura gera 5
colisões). Ela vai **na linha de guia** (§A.2, 5.27 ≤ 6.20), onde o aluno lê a definição
completa. O grafo usa a forma curta `→`/`←`, que é exatamente `res→`/`res←` da tabela e das
colunas da aba `rede`. Coerência preservada: um único significado por símbolo.

### C.4 Geometria medida

- Bloco (caixa + folga): **0.59 × 0.33**.
- Posição calculada **uma vez** em `_calcular_rotulos`, com o **pior caso** dos textos
  (capacidades do arquivo ≤ 3 no `tinyFN`), sem reposicionamento quando o fluxo muda.
- Grade estendida: `t ∈ {0.50, 0.44, 0.56, 0.40, 0.60, 0.36, 0.64, 0.32, 0.68, 0.28, 0.72,
  0.24, 0.76, 0.20, 0.80}`, `desvio ∈ {0, ±0.16, ±0.24, ±0.30, ±0.36, ±0.42}`.
- **O arco reverso da própria aresta entra na colisão** (hoje `posicao_rotulo` faz
  `continue` quando `chave == (u, v)`; passa a penalizar). Medido com o bloco 0.59×0.33:
  **0 colisões nas 8 arestas**, e o arco fica **inteiro visível** (bloco no lado oposto).
  Posições: `0→1 (2.86,1.87) d=−0.30`, `0→2 (2.46,0.49) d=−0.30`, `1→3 (4.22,2.54)
  d=−0.16`, `1→4 (3.83,1.44) d=−0.36`, `2→3 (4.77,1.49) d=−0.36`, `2→4 (4.25,−0.06)
  d=−0.16`, `3→5 (5.63,1.83) d=−0.24`, `4→5 (5.94,0.61) d=−0.24`.

### C.5 Troca de valor e legibilidade

- `_troca_texto` (l.583-592) vira `_troca_bloco`: monta o `VGroup` novo no mesmo centro e
  devolve **um** `AnimationGroup(FadeOut, FadeIn)` — sem custo extra no play do passo.
- `self.textos[(u,v)]` = `VGroup` do bloco; `fundo_atual`/`res_atual` guardam os textos das
  duas linhas para o diff. `_aplicar_imediato` (l.596-626), `aplicar` (l.628-675) e
  `animar` (l.750-752) usam o mesmo `_montar_bloco`.
- O rótulo temporário `res = f` de `animar` (l.775-792) **deixa de existir** (o valor é
  permanente na linha 2): remover `rotulo_rev`/`rotulo_rev_chave` e o FadeIn/FadeOut
  correspondente.
- 480p: fonte 13 = 0.159 un. ≈ 9,5 px; fonte 11 ≈ 8,7 px — os mesmos pisos dos contadores.

---

## D. SETA DA PILHA NO DFS (item 4b)

### D.1 Causa raiz (é bug, não estética)

`_AbaBusca._seta(a, b)` (l.1673-1683) recebe **vértices** e chama `self._x(a)`/`self._x(b)`,
mas `_x(i)` espera o **índice** na lista. Com a pilha `[0, 2]`, o chip `2` está no índice
**1**, mas a seta `(0,2)` termina em `_x(2)` — dentro/atrás do chip do índice 2. Daí "cruza
os quadrados, principalmente quando o elemento é o topo": o erro é `|id − índice|`.

### D.2 Geometria nova (seta só no gutter)

- `_seta(indice: int)` entre o chip `indice−1` e o chip `indice`:
  `x0 = _x(indice−1) + 0.21 + 0.02`, `x1 = _x(indice) − 0.21 − 0.02`, `y = −2.30`.
- Chip 0,42 × 0,30 com `PASSO_PILHA = 0.66` ⇒ gutter **0,24**; seta de **0,20**
  (`tip_length=0.07`, `stroke_width=1.6`, `buff=0`).
- Cobre pilha de 1 (nenhuma seta) a 4 (3 setas; **máximo medido** no `tinyFN`; fila máx. 3,
  sem setas).
- `self.setas` indexado pelo **índice** `i` (1..len−1). Em `sincronizar`, o conjunto é
  `range(1, len(lista))`; sobras dão `FadeOut` + `remove`; novas entram; e **todas** recebem
  `put_start_and_end_on(...)` com as posições atuais (determinístico e barato).
- Pilha de 1 elemento ⇒ `setas` vazio (sem órfão).

### D.3 Validador (obrigatório)

Em 3 passos de DFS (início/meio/fim, com pilha ≥ 2): `start.x ≥ x(i−1)+0.21` e
`end.x ≤ x(i)−0.21`; o segmento não intersecta a caixa de **nenhum** chip (margem 0.02);
não há seta para índice ≥ len.

---

## E. `FlowNetwork.validate_vertex` (item 1)

### E.1 O que a view mostra

- Fonte real `algs4/flow_network.py` **147–149** (3 linhas-fonte):
  147 `def validate_vertex(self, v):`, 148 `if not (0 <= v < V):`, 149 `raise …`.
  **Não existe `return`** (150 é vazia) e **149 nunca executa** no `tinyFN`.
- A linha 149 tem 96 caracteres ⇒ a quebra em 82 colunas (V2 §B.5) gera **4 linhas
  físicas** (147, 148, 149, continuação). 1 página, muito abaixo de 23.
- Cabeçalho (2 linhas, §B): linha 1 `FlowNetwork.validate_vertex · flow_network.py:147–149`
  (4.05), linha 2 `parte 1 de 1`.
- Moldura fixa, indicador por página, troca em dois plays — nada novo. **O indicador só
  anda na 148** (é a única linha que gera passo); nenhuma linha de retorno é inventada e
  149 não é tratada como passo frequente.
- **A escala não muda**: a maior página continua 82 colunas / 23 linhas ⇒ **11.06 pt**.

### E.2 Todos os passos entram (decisão de fidelidade)

O trace já gated tem **73 passos no BFS** e **63 no DFS** de `validate_vertex` (16 de
`add_edge`, l.154/155 + 57/47 de `adj`, l.161; todas passam). **Nenhum filtro por chamador**
— a cena mostra todos. A recomendação anterior desta revisão (filtrar `adj`) está
**revogada**: cortar passo por cronômetro trairia a fidelidade, e o custo é absorvido no
alvo (§E.4).

### E.3 Correção OBRIGATÓRIA de flicker de aba (`src/flow_common.py:1456`)

Hoje:

```python
if fn == "FlowNetwork.adj" or fn.startswith("FlowEdge."):
    return aba_anterior
```

com `validate_vertex` caindo em `"rede"` e o `adj` seguinte herdando o valor bruto, gera
runs de 2 que sobrevivem à histerese: **32 de 73 passos com flicker no BFS e 22 de 63 no
DFS**. Trocar para:

```python
if fn in ("FlowNetwork.adj", "FlowNetwork.validate_vertex") or fn.startswith("FlowEdge."):
    return aba_anterior
```

Medido pela fase `algoritmo`: trocas de aba **80 → 16 (BFS)** e **60 → 16 (DFS)**, sem
mexer na duração. Depois da correção a distribuição por aba é estável: BFS `adj` 99,
`rede` 551, `busca` 851, `edge_to` 120, `marcados` 113; DFS `busca` 398 (as demais iguais).

### E.4 Selo pedagógico no painel de estado (item 7)

73 repetições de um `if` que nunca falha é conteúdo vazio. **Adotado** um contador
derivado do trace, sem novo campo de estado:

- **Slot 5 do `StatePanel`** (hoje reservado ao veredito do corte, e **vazio durante toda a
  execução**), em `posicoes[4]` = `(1.72, −3.52)`, `aligned_edge=LEFT`, **fonte 10**,
  cor `COR_BORDA_NO` (`#8d99ae`).
- Texto: `validate_vertex {n}× · {k} violações`, com `n` = passos de `validate_vertex` já
  executados e `k` = passos na linha 149 (**0 no `tinyFN`**, medido do próprio trace, nunca
  digitado). Largura 2.32 ≤ 4.89 úteis (5.33 − 0.44).
- Aparece no **primeiro** passo de `validate_vertex` e só incrementa (crossfade normal do
  `StatePanel`, dentro do play do passo — sem duração extra). No `fechar()` o slot 5 volta a
  ser o veredito do corte, como hoje.
- **Realce único**: no primeiro passo de `validate_vertex`, um `Flash` no centro do
  indicador do código (`self.codigo.indicador.get_center()`), `color=COR_ACENTO`,
  `line_length=0.16`, `num_lines=10`, `flash_radius=0.30` — custa +0,0667 s **uma vez** por
  cena.

### E.5 Ritmo e alvo (decisão (a): absorver e re-baselinar)

| cenário | BFS | DFS |
|---|---|---|
| V2 (antes da view) | 18.61 min | 13.73 min |
| **V3 (todos os passos)** | **19.44 min (+4,5 %)** | **14.45 min (+5,2 %)** |

**Decisão: (a)**. O ritmo lento foi vendido ao usuário e a view nova é conteúdo real; cortar
passo para caber num cronômetro seria trair a fidelidade. O alvo passa a ser
**19.44 / 14.45 min** (§F.2). O `RITMO` (A.1) **não muda**.

---

## F. IMPACTO NOS VALIDADORES

### F.1 `validate_flow_layout.py`

**Trocar**
- `rotulo_base` / `rotulo_esperado` (l.362-382): string de **duas linhas**
  (`f"{nome} · {arq}:{ini}–{fim}\nparte {k} de {n}"` + `· ▸ continuação da parte …` /
  `· ◂ volta da parte …`). Comparar `original_text` inteiro.
- Largura do cabeçalho: medir **cada linha** (`texto.split("\n")`) ≤ 7.54.
- `conteudo_abas` / `abas`: `validate_vertex` herda a aba (§E.3); trocas **16/16**.
- Páginas: **18 (BFS) / 19 (DFS)**; passos 1734 / 1281; views 14 / 15.

**Adicionar**
1. **Guia de símbolos**: `estrutura.guia.original_text == GUIA_SIMBOLOS[aba_ativa]` em 5
   passos; `guia.width <= 6.20`; caixa dentro do painel; folga ≥ 0.05 até o conteúdo mais
   baixo e até os contadores.
2. **Bloco do grafo**: `dim_rotulo[(u,v)]` é o bloco de 2 linhas; a caixa **não** cruza o
   arco reverso da **própria** aresta (margem 0.02) nem o de outra; `len(textos[(u,v)]) == 2`;
   linha 1 = `fluxo`, linha 2 = `(C−f, f)`.
3. **Setas da pilha**: geometria do §D.3.
4. **`adj`**: caption ≤ 6.20 (hoje 7.12 — deve falhar antes e passar depois).
5. **Selo**: no passo do 1º `validate_vertex`, slot 5 ==
   `validate_vertex 1× · 0 violações`; no último passo, o número == total de passos de
   `validate_vertex` do trace e o de violações == passos na linha 149.

**Manter** todo o resto (fonte ≥ 10.5, partição, gutter, `PARES`, legenda 7/7, `todos()`
vivo, dois plays).

### F.2 `validate_flow_videos.py` — `ALVO` NOVO (exato)

```python
ALVO = {"edmonds": 19.44 * 60, "ford": 14.45 * 60}   # 1166.4 s / 867.0 s
```

Faixa ±1 % que o plano cobra: **1154.7–1178.1 s** (19.25–19.64 min) e
**858.3–875.7 s** (14.31–14.59 min). A folga de 40 % do validador pode ficar como está.

- **Novo frame**: aba `rede` com `f > 0` e `#ef476f` **fora** da caixa do guia → prova que
  `←f` está na tela; e `#06d6a0` (`→0` saturado) em algum frame.
- Manter: último frame não preto, bandas, 7/7, `#4a4e69` ausente.

### F.3 `validate_flow_scenes.py`

- O golden já foi re-gated pela fase `algoritmo`: **sha
  `e9975393292db428e9570e010aa23868235f6c807da3ccc33f6224a1e3e1814f`**, Gate 0 6/6
  (1734/1281 passos, 14/15 views, 18/19 páginas). O `codificador` **não toca** no trace
  nem em `FUNCOES_PAINEL`.

---

## G. Lista de mudanças por arquivo/função (para o `codificador`)

### `src/flow_common.py`

| símbolo | linha | mudança |
|---|---|---|
| `posicao_rotulo` | 293-327 | grade estendida (§C.4) + parâmetro `proprio` (arco da própria aresta) com penalidade |
| `FlowGraphView._calcular_rotulos` | 444-459 | `dim_rotulo` = bloco 2 linhas; passar `amostras_reversa(u,v)` como `proprio` |
| `FlowGraphView._criar_aresta` | 461-494 | `textos` = `VGroup(linha1, linha2)` com fundo único; `fundo_atual`/`res_atual` |
| `FlowGraphView._troca_texto` | 583-592 | vira `_troca_bloco` (um `AnimationGroup`) |
| `FlowGraphView.animar` | 750-752, 775-792 | usar `_troca_bloco`; **remover** `rotulo_rev*` e seu fade |
| `FlowGraphView.aplicar` / `_aplicar_imediato` | 596-675 | montar o bloco 2 linhas |
| `escala_codigo` | 1029-1030 | `Text("x\ny", ...)` |
| `CodePanel._rotulo` | 1167-1190 | duas linhas (§B.2/B.3) |
| `aba_do_passo` | 1451-1464 | **`validate_vertex` herda a aba** (§E.3) — obrigatório |
| **novo** `GUIA_SIMBOLOS` | junto de `ABAS` (l.1422) | dict de §A.2 (notação `C_f`) |
| `EstruturaPanel.preparar` | 2366-2378 | criar `self.guia`, devolvê-lo |
| `EstruturaPanel.atualizar` | 2382-2401 | FadeOut do guia em `sai`, novo guia em `novos` |
| `_AbaAdj._texto_caption` | 2146-2151 | remover a legenda de símbolos (caption 3.02) |
| `_AbaBusca._seta` | 1673-1683 | `_seta(indice)` por índice (§D.2) |
| `_AbaBusca.construir` | 1703-1711 | setas por índice |
| `_AbaBusca.sincronizar` | 1773-1785 | por índice + `put_start_and_end_on` em todas |
| `StatePanel.textos_do_passo` / `FlowExecucaoBase.play_step` | 1355-1374 / 2489-2534 | **selo** no slot 5 + Flash único (§E.4) |

### `src/flow_record.py`

- **Nada.** `FUNCOES_PAINEL` já contém `validate_vertex` (l.250/267) e o trace está gated.

### `validate_flow_layout.py` / `validate_flow_videos.py`

- §F.1 e §F.2.

---

## H. Autoconferência (checklist `manim-qa-visual`)

| # | critério | resultado |
|---|---|---|
| 1 | todo nó tem `str(v)` | 6/6 (inalterado) ✓ |
| 2 | toda aresta tem `f/C` com fundo opaco | 8/8, em bloco de 2 linhas ✓ |
| 3 | rótulo × rótulo / nó / aresta alheia | **0 colisões** com o bloco 0.59×0.33 ✓ |
| 4 | rótulo × arco reverso **da própria aresta** | 0 (critério novo; era ignorado) ✓ |
| 5 | painel × painel (gutter ≥ 0,20) | 0,20 ✓ |
| 6 | código × estrutura | 0,20 ✓ |
| 7 | estrutura × safe frame | borda −3,72; contadores −3,5725; guia −3,366 ✓ |
| 8 | guia de símbolos dentro da aba | 5,27 ≤ 6,20; folgas 0,074 / 0,062 ✓ |
| 9 | legenda de cores 7/7 | ✓ (nenhuma cor nova; §C.2) |
| 10 | estados não separados só por cor | ✓ (símbolo + traço + sentido + texto) |
| 11 | troca de view/aba em dois plays | ✓ (inalterado) |
| 12 | indicador por página, sem órfão | ✓ (inalterado) |
| 13 | grupo estável só com a moldura | ✓ (inalterado) |
| 14 | fonte efetiva ≥ 10,5 pt | **11.06** (largura segue mandando) ✓ |
| 15 | toda linha executada em 1 página | ✓ (partição) |
| 16 | cabeçalho com `parte k de n` e marcador | ✓ §B.3: ≤ 6.32 / 3.36 |
| 17 | 5 abas, cada uma usada | BFS 99/851/113/120/551; DFS 99/398/113/120/551 ✓ |
| 18 | `validate_vertex` com view usada | 73/63 passos, 1 página, indicador só na 148 ✓ |
| 19 | seta da pilha não cruza chip | por índice; gutter 0,24 ✓ |
| 20 | selo no slot 5 | 2.32 ≤ 4.89; aparece no 1º passo e só incrementa ✓ |
| 21 | nada fora de x ∈ [−6,56; 6,83], y ∈ [−3,72; 3,55] | ✓ |
| 22 | último frame não preto | fecho com corte (inalterado) ✓ |

Pendente para o codificador provar com número: #3–#4 no código real, #8, #16, #18–#20 por
introspecção, e o QA de pixels.

---

## I. Riscos

| risco | probabilidade | mitigação |
|---|---|---|
| **cabeçalho de 2 linhas estourar a moldura** | média | `escala_codigo` com `Text("x\ny")`; validador "conteudo dentro da moldura" |
| **guia de símbolos colidir com contadores** | baixa (0,062) | validador #8 mede a folga |
| **bloco do grafo cobrir a reversa** | média — era o bug | arco próprio entra na colisão; 0 colisões medidas |
| **`→C−f ←f` com 2 dígitos** | baixa no `tinyFN` (C ≤ 3) | dim pelo pior caso das capacidades do arquivo |
| **strobe de página com 73 visitas a `validate_vertex`** | média — 743 trocas de página no BFS | assumido: é a descida real ao método; o selo dá sentido. Botão documentado (não aplicar): filtrar chamadas de `adj` (629 trocas, 18,81 min) |
| **flicker de aba** | alta **sem** a correção | §E.3 obrigatória (80→16 / 60→16) |
| **duração 19.44/14.45** | certo | alvo re-baselinado em §F.2; `RITMO` intacto |

---

## J. Resumo de uma linha

Cabeçalho em **2 linhas** (`parte k de n` + sufixo, 11.06 pt), **guia de símbolos com a
notação `C_f`** na base da aba (5,27 ≤ 6,20), **bloco `f/C` + `→C−f ←f`** em toda aresta
(0 colisões, reversa sempre visível), **seta da pilha por índice** no gutter, `validate_vertex`
com **todos os 73/63 passos**, aba herdada e **selo `n× · 0 violações`** ⇒ alvo **19.44 /
14.45 min**.
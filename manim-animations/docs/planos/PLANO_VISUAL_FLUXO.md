# PLANO VISUAL — Fluxo Máximo (Edmonds-Karp/BFS e Ford-Fulkerson/DFS)

Fase: **VISUAL**. Entrada: `PLANO_FLUXO.md`, `RELATORIO_ROTEIRO_FLUXO.md`,
`RELATORIO_ALGORITMO_FLUXO.md`, `src/flow_record.py` (schema real de `Step.estado`).
Data: 2026-11-12. Fonte única dos números: `dataset/tinyFN.txt` (V=6, E=8, s=0, t=5).

Este documento é **contrato**: o `codificador` implementa o que está aqui; divergência
sem pedido volta para correção. Nada de estado inventado: todo valor exibido vem de
`Step.estado` / `Step.destaque` / `Step.acao`.

---

## 0. Decisões que governam a cena

| # | decisão | por quê |
|---|---|---|
| 1 | Layout em **quatro quadrantes**: código (sup. esq.), grafo (sup. dir.), estrutura (inf. esq.), estado (inf. dir.) | cabe o painel de código mais alto (a maior view tem 37 linhas) sem esmagar o grafo |
| 2 | Painel de código **mais largo e mais alto** que o do MST (7,86 × 4,55 vs 6,40 × 3,72) | a maior view de fluxo tem 37 linhas e uma linha de 120 caracteres; com 6,40 a fonte cairia para 6 pt |
| 3 | Rótulo de aresta = **`f/C`** (fluxo/capacidade), sempre visível; residual fica na tabela e na legenda da ação | "o número da aresta" nesta obra é o par (fluxo, capacidade) — é o que o algoritmo muda |
| 4 | **Aresta reversa** = arco tracejado em sentido oposto, deslocado 0,15 perpendicular, **sem rótulo permanente**; ganha rótulo `res = f` só quando é o foco do passo | 8 reversas com 8 rótulos fixos viram sopa de números; o conceito aparece quando o algoritmo olha para ela |
| 5 | **Duas abas** na estrutura: `Rede residual` (tabela) e `Busca BFS`/`Busca DFS` (fronteira) | a tabela e a fila não cabem juntas em 2,28 de altura; a aba segue o código executado |
| 6 | Contadores (`it`, `|f|`, `inspeções`, `caminho`, `b`) numa **faixa fixa** no rodapé da estrutura, fora das abas | pedido do briefing: sempre visível, nunca pisca na troca de aba |
| 7 | Todo passo é animado; o que muda é o **ritmo** (pausa por bucket do gravador) | "reduzir pausa ao mínimo sem pular passo" (§8) |
| 8 | `flow_common.py` é **autossuficiente**: não importa `mst_common` nem `dijkstra_common` | paleta/abas de fluxo têm papéis próprios; reutilizar cor de "aceita/MST" criaria dois significados |

---

## 1. Layout — coordenadas (unidades Manim, frame 14,22 × 8)

Frame: x ∈ [−7,11, 7,11], y ∈ [−4, 4]. **Safe frame** com folga 0,28:
x ∈ [−6,83, 6,83], y ∈ [−3,72, 3,72].

| bloco | x | y | dimensão |
|---|---|---|---|
| Título + subtítulo (coluna direita) | 1,55 → ~6,35 | 3,15 → 3,55 | 2 linhas (15 / 11) |
| **Moldura do código** | −6,56 → 1,30 | −1,10 → 3,45 | 7,86 × 4,55 |
| **Grafo** | 1,63 → 6,79 | −0,25 → 3,05 | bbox do desenho |
| **Guia visual** (2 linhas) | 1,55 → 6,31 | −0,95 → −0,45 | 4,76 / 4,41 de largura |
| **Painel de estrutura** | −6,56 → 1,30 | −3,72 → −1,44 | 7,86 × 2,28 |
| **Painel de estado** | 1,50 → 6,83 | −3,72 → −1,60 | 5,33 × 2,12 |

Folgas verificadas (contrato do QA):

- código → estrutura: −1,10 → −1,44 = **0,34**
- código → estado (gutter central): 1,30 → 1,50 = **0,20**
- grafo → guia: −0,25 → −0,45 = **0,20**
- guia → estado: −0,95 → −1,60 = **0,65**
- título → grafo: 3,15 → 3,05 = **0,10**
- tudo dentro de x ∈ [−6,56, 6,79], y ∈ [−3,72, 3,55] (safe frame 0,28 respeitado)

Construção no código (para não sobrar número solto):

```python
CODIGO = dict(largura=7.86, altura=4.55, canto=UL, buff=0.55)   # moldura.to_corner(UL, buff=0.55)
ESTRUTURA = dict(centro=(-2.63, -2.58), largura=7.86, altura=2.28)
ESTADO    = dict(centro=( 4.17, -2.66), largura=5.33, altura=2.12)
TITULO_X  = 1.55      # coluna direita, alinhado à esquerda
```

> Por que o título não é centralizado no topo: a moldura do código termina em y=3,45
> ocupando toda a largura da esquerda; um título centralizado colidiria com ela. O título
> vive sobre a coluna do grafo (x ≥ 1,55), que começa em y=3,05.

---

## 2. Grafo `tinyFN` — `FlowGraphView`

### 2.1 Posições fixas (validadas numericamente, ver §10)

```python
COORDS = {
    0: (1.90, 1.40),   # s (origem)
    1: (3.42, 2.78),
    2: (3.42, 0.02),
    3: (5.05, 2.62),
    4: (5.05, 0.18),
    5: (6.52, 1.40),   # t (sumidouro, = V-1)
}
RAIO_NO   = 0.27
BUFF_SETA = 0.30        # a seta nasce/termina fora do nó
LARG_SETA = 3.2
PONTA     = 0.16
```

Leiaute em 4 colunas (s | {1,2} | {3,4} | t). Único cruzamento de arestas: `1→4` × `2→3`
em ≈ (4,3, 1,4) — permitido (aresta × aresta pode cruzar); os rótulos dessas duas ficam
em t=0,38 e t=0,68, longe do cruzamento.

### 2.2 Nós

- Círculo raio 0,27, `fill=#2b2d42`, borda 1,8 `#8d99ae`; **rótulo = `str(v)`** (fonte 17, branco).
- **s (0)**: anel externo raio 0,34 (`#4cc9f0`) + etiqueta `s` acima-esquerda (fonte 11, `#4cc9f0`).
- **t (5)**: anel externo raio 0,34 (`#ffd166`) + etiqueta `t` acima-esquerda (fonte 11, `#ffd166`).
  O id continua visível dentro do nó — a etiqueta é papel, não identidade.
- `marcados` (alcançados na residual / lado S): `fill=#80ed99`, opacidade 1.
- **foco** (o `v` do passo: `queue.popleft()`, `v` do `dfs`, ou extremo do destaque):
  anel externo raio 0,34 `#e879f9` (mesmo papel "em exame" da aresta).

### 2.3 Arestas diretas

- `Arrow` (ou `Line` + ponta) com `buff=0.30`, `stroke_width=3.2`, `tip_length=0.16`.
- Cor por estado derivado de `estado["fluxos"]` / `estado["capacidades"]`:

| condição | status | cor | traço |
|---|---|---|---|
| `f == 0` | `fora` | `#8d99ae` | 3,2 |
| `0 < f < C` | `fluxo` | `#4cc9f0` | 4,2 |
| `f == C` (res. direta 0) | `saturada` | `#06d6a0` | 4,2 |

- **Rótulo `f/C`** em toda aresta: `Text(f"{f:g}/{C:g}", font_size=13, color="#f2f4f8")`
  com `RoundedRectangle` opaco `#0f111a` atrás (abre o vão da linha). Fundo/sombra em
  z=2, texto z=3, aresta z=0.
- Posições dos rótulos **calculadas uma vez** (determinístico, ordem do arquivo), com a
  busca: centro → ao longo (0,44 / 0,56 / 0,38 / 0,62 / 0,32 / 0,68 / 0,26 / 0,74) →
  perpendicular (±0,16 / 0,22 / 0,28) → menos colisões. Colisões contadas contra:
  nós (caixa 0,34), outras arestas diretas (Liang–Barsky, margem 0,05), **arcos reversos
  de todas as arestas**, rótulos já postos e o limite da área útil.
  Resultado medido com este algoritmo (reproduzir e conferir no teste):

  | aresta | t | desvio | centro |
  |---|---|---|---|
  | 0→1 | 0,50 | 0,00 | (2,66, 2,09) |
  | 0→2 | 0,50 | 0,00 | (2,66, 0,71) |
  | 1→3 | 0,50 | 0,00 | (4,23, 2,70) |
  | 1→4 | 0,38 | 0,00 | (4,08, 1,73) |
  | 2→3 | 0,68 | 0,00 | (4,47, 1,70) |
  | 2→4 | 0,50 | 0,00 | (4,23, 0,10) |
  | 3→5 | 0,50 | 0,00 | (5,78, 2,01) |
  | 4→5 | 0,50 | 0,00 | (5,78, 0,79) |

  Todos os 8 ficaram **livres** (0 colisões) com as coordenadas de §2.1 — nenhum caiu no
  fallback "menos colisões". A tabela é a *conferência* do algoritmo; a cena **calcula**,
  não digita.

### 2.4 Aresta reversa (o conceito central)

- Desenhada **só quando `residual_reversa > 0`** (ou seja, quando `f > 0`), no sentido
  `v→u`, como **arco tracejado**:
  ```python
  arco = ArcBetweenPoints(p_ini, p_fim, angle=-0.45)   # p_ini/p_fim = extremos encurtados
  arco = arco.shift(perpendicular * 0.15)              # desloca para não tocar a direta
  tracejado = DashedVMobject(arco, num_dashes=14, dashed_ratio=0.55)
  ```
  com ponta de seta no fim (`v→u`), `stroke_width=1.8`, cor `#ef476f`.
- **Sem rótulo permanente.** Quando o passo foca a reversa (ver §2.5), nasce um rótulo
  `res = {f:g}` (fonte 12, `#ef476f`, fundo opaco) no meio do arco, deslocado +0,16
  perpendicular; ele sai no passo seguinte.
- Entrada/saída com `FadeIn`/`FadeOut` de 0,18 — a reversa "nasce" quando o primeiro
  gargalo é empurrado (isso é visível e é o ponto didático).

### 2.5 Foco do passo (`Step.destaque`) → o que acende

`destaque = (tipo, u, v, status)`. Mapeamento da aresta: se `(u,v)` é aresta da rede →
**direta**; se `(v,u)` é aresta da rede → **reversa** (acende o arco tracejado). É essa
regra que torna visível "a busca inspecionou a reversa `2→0` com residual 2".

| destaque | efeito no grafo |
|---|---|
| `("inicio", …)` | nada (rede montada, f=0) |
| `("aresta", u, v, "insere")` | aresta pisca `#ffd166` (montagem da rede) |
| `("busca", u, v, "olhando"/"examina")` | aresta/arco em `#e879f9` + `Flash` no ponto médio (raio 0,22, 8 linhas, 0,10) |
| `("busca", u, v, "descoberto")` | aresta em `#e879f9` + nó `v` com anel de foco + `Flash` no nó |
| `("busca", None, None, "nova"/"fim")` | caminho inteiro (de `estado["caminho"]`) em `#ffd166`; `Flash` em `t` |
| `("caminho", u, v, "aumentante")` | aresta do caminho em `#ffd166`, traço 5,5 |
| `("aumento", u, v, "augmenta")` | aresta em `#ffd166` + `Flash`; o `f/C` já mostra o novo `f` |
| `("valor", …)` | `Flash` no nó `t` + contador `|f|` no rodapé |
| `("corte", u, v, "cruza")` | aresta em `#ffd166`, traço 5,5 (só no fecho) |
| `("corte", v, None, "lado_s"/"lado_t")` | anel do nó (S = `#80ed99`, T = `#8d99ae`) |
| `("corte", None, None, "fechado")` | corte inteiro + veredito no painel |

**Regra de ouro da cor**: a cada passo a cor-alvo de cada aresta é `foco` se ela é o
foco, senão o estado base (`fora`/`fluxo`/`saturada`). Como é um *diff* contra a cor
atual, o foco anterior volta sozinho ao estado base no passo seguinte. Nunca há cor
"acumulada" que minta sobre o estado.

### 2.6 Custo por passo (importante para 1661 passos)

`animar()` devolve só o que mudou: comparar cor-alvo por aresta, presença de reversa,
texto de `f/C`, fill dos nós, anel de foco. Em passo de bookkeeping típico o diff é
**vazio ou 1 mobject** — nada de reconstruir o grafo.

---

## 3. Paleta e guia visual (contrato de legenda)

```python
PALETA = {                      # papel -> (hex, texto da legenda, símbolo)
    "fora":      ("#8d99ae", "sem fluxo",        "dot"),
    "fluxo":     ("#4cc9f0", "com fluxo",        "dot"),
    "saturada":  ("#06d6a0", "saturada",         "dot"),
    "exame":     ("#e879f9", "em exame",         "dot"),
    "caminho":   ("#ffd166", "caminho",          "dot"),
    "reversa":   ("#ef476f", "reversa (res. f)", "dash"),
    "alcancado": ("#80ed99", "alcançado/lado S", "ring"),
}
ESTRUTURAIS = dict(fundo="#0f111a", painel="#151824", no="#2b2d42",
                   borda="#8d99ae", texto="#f2f4f8", rotulo_no="#ffffff")
```

**Uma cor por papel, um item por cor.** O vértice em foco usa o **mesmo** magenta de
"em exame" (o papel é o mesmo: *isto é o que o algoritmo está olhando agora*); o tipo é
distinguido pelo símbolo (ponto = aresta, anel = vértice). Por isso são **7 itens**, não 8.

Notas de projeto (por que não reutilizei a paleta do MST ao pé da letra):

- `#8d99ae` (neutro) = "sem fluxo" — não é "fora da árvore", é "f=0"; papel novo, texto novo.
- `#06d6a0` (verde) = **saturada** (res. direta 0). Não é "aceita na MST".
- `#4cc9f0` (ciano) = com fluxo e ainda com residual. Distinto do cinza e do verde.
- `#ffd166` (âmbar) = caminho aumentante / corte. É a cor de "isto é o resultado agora".
- `#e879f9` (magenta) = **em exame** (aresta e vértice em foco). Papel único.
- `#ef476f` (vermelho) = **reversa**; o símbolo é tracejado + sentido oposto, então o
  significado não depende só da cor (daltonismo).
- `#80ed99` (verde claro) = alcançado/lado S, com símbolo **anel** (vértice).

**Cobertura nas duas direções** (verificada no teste, não na mão):

| papel | aparece na cena? | onde |
|---|---|---|
| fora | sim | passos iniciais (f=0 em 8 arestas) |
| fluxo | sim | 0→2 fica 2/3 até o fim |
| saturada | sim | 1→4, 2→3, 2→4, 3→5 terminam f=C |
| exame | sim | 164 (BFS) / 74 (DFS) inspeções |
| caminho | sim | 4 caminhos + 4 augmentações + corte |
| reversa | sim | 8 reversas nascem quando f>0 |
| alcançado | sim | `marcados` de toda busca + `corte` |

Formato do guia: **fonte única 12**, marca única (dot raio 0,075; anel raio 0,075
stroke 2,6; `dash` = segmento tracejado 0,16 × 1,8). **7 itens em duas linhas (4 + 3)**,
larguras 4,76 e 3,31 ≤ 5,28 — **sem** `scale_to_fit_width`. Bloco
`next_to(grafo, DOWN, buff=0.20, aligned_edge=LEFT)`.

---

## 4. Painel de código — `CodePanel` (cópia adaptada, moldura fixa)

Medido com o `flow_record` real (não estimado):

| variante | views | maior view | altura bruta | largura bruta | escala | fonte efetiva |
|---|---|---|---|---|---|---|
| Edmonds-Karp | 13 | `FordFulkerson.__init__` (37 linhas) | 13,83 | 25,58 (`is_feasible`) | 0,3069 | **≈ 7,4 pt** |
| Ford-Fulkerson DFS | 14 | `FordFulkersonDFS.__init__` (37 linhas) | 13,83 | 26,79 (`is_feasible`) | 0,2933 | **≈ 7,0 pt** |

- Moldura **7,86 × 4,55** em `to_corner(UL, buff=0.55)`; conteúdo com padding
  0,30 esq / 0,34 dir / 0,16 topo / 0,16 base.
- Escala = `min((4.55-0.30)/max_altura, 7.86/max_largura)` **uma vez por vídeo**;
  nenhum zoom na troca.
- Cabeçalho por view: `{nome} · {arquivo}:{inicio}–{fim}` (fonte 12, `#48cae4`).
- `Code(..., formatter_style="monokai", add_line_numbers=True, line_numbers_from=f.inicio)`
  e **remover `codigo.background`** (moldura nativa não acompanha o texto).
- Grupo estável = **só a moldura**; conteúdo e indicador são mobjects de cena.
- Troca: `play(*sai)` → `play(*entra)`, dois plays, `run_time=0.09` cada. Indicador
  por view (`SurroundingRectangle` na linha real).
- `encaixar(passo)` na primeira montagem (indicador nasce na linha executada, não no
  `class`).

> Registro honesto: 7,4 pt ≈ 14 px em 1080p, contra 11,3 pt dos vídeos de MST. A causa é
> objetiva — 37 linhas e uma linha de 120 caracteres (`is_feasible`, linha 111). Reduzir
> mais a moldura piora; cortar linha é proibido pela skill. Se o usuário pedir fonte
> maior, a única saída é quebrar a linha longa na renderização (decisão dele, não nossa).

---

## 5. Painel de estrutura — `EstruturaPanel` (abas)

Dimensões: 7,86 × 2,28, centro (−2,63, −2,58). Interno: abas em y ≈ −1,56 (altura 0,30);
corpo y ∈ [−1,78, −3,38]; **faixa de contadores fixa** em y ≈ −3,55 (fora das abas).

### 5.1 Abas

```python
ABAS = {
  "edmonds_karp":       (("rede", "Rede residual"), ("busca", "Fila (BFS)")),
  "ford_fulkerson_dfs": (("rede", "Rede residual"), ("busca", "Pilha (DFS)")),
}
```

Regra de troca (derivada do trace, não de número de linha digitado):

- **`busca`** enquanto a busca está aberta: entra quando `estado["iteracao"]` muda ou
  `fila`/`pilha` fica não vazia; sai no passo cujo `destaque` é
  `("busca", _, _, "nova"|"fim")` (o `return marked[t]` fecha a busca).
- **`rede`** em todo o resto (montagem, gargalo, augmentação, `check`/corte).
- Troca = `play(FadeOut de todos os mobjects da aba))` → `play(FadeIn dos novos)` —
  dois plays, `run_time=0.09`, **nunca as duas abas no mesmo frame**.
- Aba ativa: borda `#48cae4` 1,6, fill `#1f2637`, texto branco; inativa: borda cinza,
  fill `#0f111a`, texto `#8d99ae`.

### 5.2 Aba `Rede residual` — a tabela

Duas metades de 4 arestas (ordem do arquivo: 0→1, 0→2, 1→3, 1→4 | 2→3, 2→4, 3→5, 4→5),
cada metade com cabeçalho próprio. Colunas (larguras em unidades):

| aresta | C | f | res→ | res← |
|---|---|---|---|---|
| 0,95 | 0,45 | 0,45 | 0,60 | 0,60 |

- Célula = `Text` (fonte 10) sobre chip `RoundedRectangle` 0,22 de altura
  (`#1f2637` inativa; `#2a2f45` quando é a aresta em foco; borda `#e879f9` 1,2 no foco).
- Linha de cabeçalho em `#8d99ae` (fonte 9, sem chip).
- `res→` = `C−f`, `res←` = `f` — **valores do `estado`**, nunca recalculados na cena.
- `res→ = 0` recebe o texto em `#06d6a0` (saturada) — reforça "saturada bloqueia".
- Troca de valor de célula: crossfade curto (`AnimationGroup(FadeOut, FadeIn)`, 0,15)
  no mesmo slot — nunca `Transform` de string.

### 5.3 Aba `Busca BFS` / `Busca DFS`

- **Fila (BFS)**: chips na ordem real de `estado["fila"]` (0,42 × 0,30, fonte 11),
  com `↓ frente` acima do primeiro e `↑ fim` abaixo do último; chips entram com
  `FadeIn` e saem com `FadeOut` (removidos da cena).
- **Pilha (DFS)**: `estado["pilha"]` como caminho de recursão `0 → 2 → 4 → 5` com
  setas entre chips e `topo` sob o último.
- Ao lado: `edgeTo` compacto (`2←0  3←2  4←2 …`, fonte 10) e `marcados {0,2,3}`
  (fonte 10, `#80ed99`), e `inspeções 37` (fonte 10, `#8d99ae`).
- Tudo derivado de `Step.estado`; nenhum valor digitado.

### 5.4 Faixa de contadores (sempre visível, fora das abas)

Uma linha, fonte 11, `aligned_edge=LEFT` em x = −6,24:

```
it 2/5 · |f| = 2 · inspeções 37 · caminho 0→2→3→5 · b = 1
```

- `it` = `estado["iteracao"]` (1-based, o número da busca em curso);
- `|f|` = `estado["valor"]`;
- `inspeções` = `estado["inspecoes"]`;
- `caminho` = `estado["caminho"]` (`0→2→3→5`) ou `—`;
- `b` = `estado["gargalo"]` ou `—`.
- Troca por crossfade curto. Dimensão do card pelo pior caso (string acima).

---

## 6. Painel de estado (inferior direito)

5 slots fixos, `aligned_edge=LEFT`, largura 5,33 (x = 1,72), sem trepidação:

| slot | conteúdo | fonte | cor |
|---|---|---|---|
| 1 | `passo.acao` — parte 1 | 12 | cor do destaque |
| 2 | `passo.acao` — parte 2 (quebra no último espaço antes de 44 ch) | 12 | cor do destaque |
| 3 | `fila [1, 4] · frente 1` / `pilha [0,2,4,5] · topo 5` | 11 | `#8d99ae` |
| 4 | `marcados {0,2,3}` | 11 | `#80ed99` |
| 5 | no fecho: `corte S*={0,2} · C(S,T)=4 = |f|` | 12 | `#ffd166` |

- A ação vem em **duas linhas fixas** porque a maior string tem 76 caracteres (6,68
  unidades em fonte 12 > 5,33). Quebra determinística, duas linhas sempre reservadas.
- Slot 5 vazio durante a execução (não pisca: só entra no `fechar()`).
- Cor da ação = `cor_destaque(passo)`: `busca`→`#e879f9`, `caminho`/`aumento`/`valor`→
  `#ffd166`, `corte`→`#06d6a0`, `aresta`→`#8d99ae`, sem destaque→`#f2f4f8`.

---

## 7. Roteiro de cenas

Nomes exatos (não renomear): `EdmondsKarpIntro_new`, `EdmondsKarpExecutionScene_new`,
`FordFulkersonIntro_new`, `FordFulkersonExecutionScene_new`, `FullEdmondsKarpVideo_new`,
`FullFordFulkersonVideo_new`.

### 7.1 `EdmondsKarpIntro_new` (~50 s) — conceitos, dados de `tinyFN`

1. Título `Fluxo Máximo — Edmonds-Karp (BFS)` (30) + subtítulo
   `Rede de fluxo tinyFN · V=6 · E=8 · s=0 · t=5` (16) — números de `rec.V_REDE`,
   `rec.ARESTAS_REDE`, `rec.S_FONTE`, `rec.T_SUMIDOURO`.
2. Grafo à direita em f=0 (capacidades visíveis: `0/2`, `0/3`, …).
3. Painel esquerdo (6,2 × 4,6, 4 itens, como nos intros do MST):
   - `• Capacidade` — cada arco tem `C(u,v) ≥ 0`;
   - `• Conservação` — `0 ≤ f ≤ C`; nos internos, entra = sai;
   - `• Valor` — `|f| = Σ f(s,·) = Σ f(·,t)`;
   - `• Rede residual` — `C_f(u,v) = C−f` (direta) e `C_f(v,u) = f` (reversa).
4. **Slide 2 (residual)**: foca `0→2` (C=3) com `f=2`: mostra `res→ = 1` e o arco
   tracejado `2→0` com `res← = 2`; texto "a reversa desfaz fluxo".
5. **Slide 3 (caminho + gargalo)**: acende `0→2→4→5` com residuais 1, 1, 2 →
   `b = min = 1`; "empurra b, `|f| += b`".
6. **Slide 4**: laço "repete enquanto existir caminho" + `BFS ⇒ caminho de menor
   número de arestas` + `O(V·E²)`.
7. Fecho do intro: `|f| = 4 · corte mínimo = 4` (de `coletar("edmonds_karp")[-1]`).

### 7.2 `FordFulkersonIntro_new` (~50 s)

Mesma espinha (itens 1–6), trocando o último slide:

- `DFS ⇒ desce até t e volta` · `O(E·|f|)` · pseudo-polinomial (depende das capacidades).
- **Nota medida** (não inventada): "nesta rede os 4 caminhos são os mesmos; a diferença
  está na busca: **27 inspeções de aresta** (DFS) contra **69** (BFS)" — valores de
  `coletar(...)[-1].estado["inspecoes"]` das duas variantes.
- Declarar honestamente: "BFS garante o caminho mais curto em arestas; em `tinyFN` todos
  os caminhos têm 3 arcos, então a garantia não se manifesta aqui".

### 7.3 `*ExecutionScene_new` (linha a linha)

`FlowExecucaoBase(Scene)` com `algoritmo` ∈ {`edmonds_karp`, `ford_fulkerson_dfs`}:

1. `camera.background_color = #0f111a`.
2. `passos = rec.coletar_detalhado(algoritmo)` (**1661** / **1218**).
3. Título + subtítulo; `CodePanel.encaixar(passos[0])`; `FlowGraphView`;
   `EstruturaPanel.preparar(passos[0])`; guia visual; `StatePanel.iniciar`.
4. `for passo in passos: play_step(passo)`.
5. `fechar()` — corte mínimo (§7.4).

`play_step(passo)` (ordem obrigatória):

```python
if self.codigo.mudou(passo):
    sai, entra = self.codigo.trocar(passo)
    self.play(*sai)            # 1º play
    self.play(*entra)          # 2º play
anims_estrutura, add, rem, troca = self.estrutura.atualizar(passo)
if troca:                      # troca de aba: fade-out total → fade-in
    self.play(*sai_aba); self.add(*novos); self.play(*[FadeIn(m) for m in novos])
if add: self.add(*add)
anims = [self.codigo.destacar(passo)] + grafo.animar(...) + self.painel.atualizar(...) + anims_estrutura
self.play(*anims, run_time=RITMO["play"])
if rem: self.remove(*rem)
self.wait(RITMO["pausa"][passo.pausa])
```

### 7.4 `fechar()` — corte mínimo (o fecho que o guia pede)

1. Pinta `S* = estado["corte"]` (nós com anel `#80ed99`) e `T*` (cinza).
2. Acende as arestas que cruzam (`u ∈ S*, v ∉ S*`) em `#ffd166` com `Flash`.
3. Caixa no canto inferior direito (dentro do painel de estado, slot 5 + realce):
   ```
   S* = {0, 2}   T* = {1, 3, 4, 5}
   C(S,T) = 2 + 1 + 1 = 4 = |f|
   ```
4. Frase didática (armadilha nº 1 do roteiro): "a saída de s soma 5, mas o gargalo
   interno (2→3 e 2→4, ambos cap. 1) limita o fluxo a 4" — valores de `estado`.
5. `self.wait(2.2)`.

---

## 8. Orçamento de duração (conta explícita)

### 8.1 Parâmetros (`RITMO` em `flow_common.py`)

```python
RITMO = dict(
    play=0.18,          # play único do passo (indicador + grafo + painéis)
    play_destaque=0.24, # passos com Flash (busca/caminho/aumento/valor/corte)
    fade=0.09,          # cada play da troca de view/aba (0.18 por troca)
    pausa={0.55: 0.06,  # bookkeeping (for/while/if/atribuição)
           1.00: 0.22,  # decisão
           1.70: 0.90}, # fecho (|f| += b, check, return da busca)
)
```

Nenhum passo é pulado. `pausa` é só o `self.wait` depois do play; o passo existe.

### 8.2 Edmonds-Karp (1661 passos, 596 trocas de view)

| parcela | conta | segundos |
|---|---|---|
| plays base | 1661 × 0,18 | 299,0 |
| extra de destaque | 223 passos × 0,06 | 13,4 |
| pausa bookkeeping | 1174 × 0,06 | 70,4 |
| pausa decisão | 475 × 0,22 | 104,5 |
| pausa fecho | 12 × 0,90 | 10,8 |
| trocas de view | 596 × 0,18 | 107,3 |
| trocas de aba | ~15 × 0,18 | 2,7 |
| montagem + `fechar` | — | 25,0 |
| **total** | | **≈ 633 s = 10,6 min** |

### 8.3 Ford-Fulkerson DFS (1218 passos, 418 trocas)

| parcela | conta | segundos |
|---|---|---|
| plays base | 1218 × 0,18 | 219,2 |
| extra de destaque | 133 passos × 0,06 | 8,0 |
| pausa bookkeeping | 853 × 0,06 | 51,2 |
| pausa decisão | 337 × 0,22 | 74,1 |
| pausa fecho | 28 × 0,90 | 25,2 |
| trocas de view | 418 × 0,18 | 75,2 |
| trocas de aba | ~15 × 0,18 | 2,7 |
| montagem + `fechar` | — | 25,0 |
| **total** | | **≈ 481 s = 8,0 min** |

Ambas dentro da meta 8–12 min **sem parâmetro diferente entre as duas**. Botão de
ajuste (documentar, não aplicar sem pedido): `play=0.16` ⇒ BFS 9,5 min / DFS 7,3 min;
`pausa[1.0]=0.30` ⇒ +34 s em cada.

### 8.4 Política dos passos repetitivos (inspeção de aresta em laço)

- A inspeção (`residual_capacity_to` → `other` → `residual_capacity_to`) custa
  `0,18` de play + `0,06` de pausa, com **Flash magenta** no ponto médio da aresta —
  é o pulso visual que mostra "o algoritmo olhou aqui".
- Quando o diff do passo é vazio (estado idêntico, só o indicador anda), o play é o
  mesmo `0,18` — não há passo "invisível".
- **Proibido**: colapsar passos repetidos, agrupar inspeções, inventar estado
  intermediário ou reduzir a pausa a zero (frame congelado).
- Piso medido do sistema: 1661 × 0,18 = 5,0 min só de plays. Não existe versão
  didática de 1661 passos em menos de ~5 min.

---

## 9. Arquivos e trabalho do codificador

### 9.1 Escrever

| arquivo | conteúdo |
|---|---|
| `manim-animations/src/flow_common.py` | `PALETA`, `COR_*`, `COORDS`, `RITMO`, `FlowGraphView`, `CodePanel`, `EstruturaPanel` (abas `rede`/`busca`), `StatePanel`, `GuiaVisual`, `FlowExecucaoBase`, `cor_destaque`, `fmt_*` |
| `manim-animations/src/edmonds_karp_scene_new.py` | `EdmondsKarpIntro_new`, `EdmondsKarpExecutionScene_new`, `FullEdmondsKarpVideo_new` |
| `manim-animations/src/ford_fulkerson_scene_new.py` | `FordFulkersonIntro_new`, `FordFulkersonExecutionScene_new`, `FullFordFulkersonVideo_new` |
| `manim-animations/validate_flow_layout.py` (novo) | QA de geometria sem render: rótulos de nó, `f/C` em toda aresta, colisões (`PARES` do §10), legenda fiel nos dois sentidos, bounds dos painéis, e o teste de que todo `Step` cai em exatamente uma aba/uma view |

### 9.2 Não tocar

- `src/mst_common.py`, `src/dijkstra_common.py`, `src/flow_record.py`,
  `src/*_scene_new.py` de MST/Dijkstra, `media/`, `algs4-py/`.

### 9.3 Verificação obrigatória (nesta ordem)

1. `python validate_flow_scenes.py` → 6/6 (não pode regredir; `stages_fluxo.json`
   continua com o mesmo SHA se nada mudou).
2. `python validate_flow_layout.py` → 0 falhas.
3. **Um** render 480p por cena:
   `manim -ql --media_dir media_dev_fluxo src/edmonds_karp_scene_new.py EdmondsKarpIntro_new`
   (idem `EdmondsKarpExecutionScene_new`, `FordFulkersonIntro_new`,
   `FordFulkersonExecutionScene_new`). Os `Full*` **não** renderizam agora (são
   wrappers intro+execução e dobram o tempo).
4. QA de pixels em 480p (`extrair_frames.py`): último frame não preto, cada cor da
   `PALETA` presente **fora** da caixa do guia, `#4a4e69` ausente, `#f2f4f8` só em rótulo.
5. Reportar tempo de render e duração de cada MP4. **Parar** e aguardar o usuário
   para o 1080p60.

---

## 10. Autoconferência (checklist `manim-qa-visual`)

Geometria — **executada nesta fase**, com as coordenadas de §2.1 e o algoritmo de §2.3
(Manim importado, sem render):

| # | critério | resultado |
|---|---|---|
| 1 | todo nó tem `str(v)` | 6/6 ✓ |
| 2 | toda aresta tem `f/C` com fundo opaco | 8/8 ✓ |
| 3 | rótulo × rótulo (folga 0,02) | 0 colisões ✓ |
| 4 | rótulo × nó (folga 0,06) | 0 colisões ✓ |
| 5 | rótulo × aresta alheia (Liang–Barsky 0,05) | 0 colisões ✓ |
| 6 | rótulo × **arco reverso** (desloc. 0,15 / ângulo −0,45) | 0 colisões ✓ (a única falha era `2→3`; resolvida em t=0,68) |
| 7 | arco reverso × nó alheio | mín. 1,10 ✓ |
| 8 | desenho dentro da área útil | x 1,63–6,79 · y −0,25–3,05 ✓ |
| 9 | painel × painel (gutter ≥ 0,20) | 0,20 ✓ |
| 10 | código × estrutura | 0,34 ✓ |
| 11 | guia × estado | 0,65 ✓ |
| 12 | guia em 2 linhas, fonte única 12, sem escala | 4,76 / 4,41 ≤ 5,28 ✓ |
| 13 | legenda: 7 papéis usados / 7 itens, cobertura dupla | ✓ (§3) |
| 14 | estados não separados só por cor | saturada (verde, cheia) × reversa (vermelho, tracejada, sentido oposto) × caminho (âmbar, 5,5) ✓ |
| 15 | troca de view/aba em **dois** plays | ✓ (regra em §4/§5) |
| 16 | último frame não preto | fecho com corte + veredito ✓ |

Pendente para o codificador provar com número (o teste é dele): #3–#7 no código real
(as coordenadas dos rótulos têm de sair do algoritmo, não da tabela), #13 por contagem
de uso em `coletar_detalhado`, e o QA de pixels.

---

## 11. Resumo de uma linha

Código à esquerda (7,86 × 4,55, 13/14 views, troca em dois plays), grafo `f/C` à direita
com reversas tracejadas, tabela/busca em abas embaixo à esquerda, ação+corte embaixo à
direita, 7 cores unívocas na legenda — 10,6 min (BFS) e 8,0 min (DFS) com o mesmo ritmo.

# PLANO VISUAL V4 — Fluxo Máximo (Edmonds-Karp/BFS e Ford-Fulkerson/DFS)

Fase: **VISUAL (revisão 4)** — correção do vídeo entregue. Substitui o
`PLANO_VISUAL_FLUXO_V3.md` **apenas nos pontos aqui tratados**; tudo o que não é citado
(guia de símbolos §A, cabeçalho de 2 linhas §B, bloco `f/C` + `→C−f ←f` §C, seta da pilha
§D, `validate_vertex` + selo §E, `RITMO`, `PALETA`, `GUIA_SIMBOLOS`, 5 abas em trilho,
troca em dois plays, fecho do corte) continua valendo **sem alteração**.

Entradas medidas: `src/flow_common.py` (118 138 B), `src/flow_record.py` (86 006 B, já com
`Step.escrita` e `Step.estado_pos`), `validate_flow_layout.py` (56 806 B),
`validate_flow_scenes.py`, `docs/relatorios/QA_COLISAO_EK_0451.md`, `dataset/tinyFN.txt`
(V=6, E=8, s=0, t=5) e o trace real (`coletar_detalhado`): **1510 passos (EK) / 1281 (DFS)**,
18/19 páginas, 14/15 views, `stages` sha `c19ee524…a3a` (inalterado).

Data: 2026-11-20. **Todo número abaixo foi medido** com o Manim 0.22.0 do `.venv` e com o
trace real — scripts `build/_medir_v4*.py` (descartáveis) —, não estimado.

> **Revisão 4.1 (2026-11-20, só o §B.6).** A V4 entregue deixou medido que, com
> `aba_do_passo` devolvendo `passo.escrita`, **a linha que escreve é quase sempre a linha que
> troca de aba**: o elemento novo aparecia só pelo `FadeIn` do corpo inteiro (77 EK / 62 DFS)
> e o `Flash` local só disparava nas 5/5 escritas que caem em aba já ativa. O §B.6 deixava
> `EstruturaPanel.atualizar` congelado e por isso o `Flash` não podia ser emitido no ramo de
> troca. **Rev. 4.1 autoriza e exige** o realce local também nesse ramo. Medido
> (`build/_medir_realce_v41c.py` e `_v41d.py`): **70 (EK) / 55 (DFS)** das **82/67** adições
> têm exatamente **1** elemento novo identificável (e recebem `Flash`); as **12/12** restantes
> são `tipo == "reset"` (reconstrução da lista inteira, sem elemento único) e continuam
> entrando pelo `FadeIn` do corpo. **Custo de duração: 0,0 s** (o `Flash` entra no play de
> `0,40`/`0,4667` s que já existia). Nada mais do plano muda.

> **Fase `algoritmo` conferida.** `docs/relatorios/RELATORIO_ALGORITMO_ESTADO_POS.md` foi
> entregue e confirma os números usados aqui: 1510/1281 passos, **153/135 passos com
> `escrita`**, Gate 0 **8/8** e `stages` sha `c19ee524…a3a` **inalterado** (o golden não exporta
> `estado_pos`/`escrita`). `src/flow_record.py` **não é tocado** por esta fase; se algum número
> do relatório divergir do que está abaixo, o plano volta para revisão antes do código.

---

## 0. Resumo executivo (feedback → decisão → número medido)

| # | feedback literal | decisão | número medido |
|---|---|---|---|
| 1 | "Em 04:51, tem elementos se conflitando com os chips/elementos da edgeTo" | bloco `caminho`+`b` deixa a coluna direita e passa a ficar **fixo abaixo da fila** (§A) | V3: **90 passos / 120** com colisão (180 eventos); V4: **0/146 (EK)** e **0/141 (DFS)** |
| 2 | "não apareceu muito as estruturas de dados edgeTo e marked … mudasse para a aba de visualização da respectiva estrutura … faça a ação do código" | a aba passa a ser **a estrutura escrita pela linha** (`passo.escrita`), na ordem real do fonte (§B) | aba ativa: `edge_to` **120→146**, `marcados` **113→144** (EK); **120→141 / 113→139** (DFS) |
| 3 | "Não quero que seja só adicionado no bfs e escrever no texto adicionando o vertice dos textos de edgeto e marked da aba de bfs" | **remover** os textos `edgeTo`/`marcados` da aba `busca`; o elemento entra com `FadeIn`+`Flash` na aba certa (§B.4/B.5) | 2 textos e o bloco de `_troca` deles removidos; aba `busca` = fila/pilha + `frente`/`fim` + `inspeções` |
| 4 | "essas duas considerações … também podem ser aplicadas para … ford fulkerson dfs" | mesma coreografia; a `busca` do DFS é a **pilha**; `dfs` call/return = push/pop (§C) | DFS: 74 trocas, 0 colisões, 40 adições de pilha (20 push / 20 pop) |
| 5 | resto do contrato | intros, paleta, legenda, guia, RITMO e trace **intactos** | duração **+3,9 s (EK) / +1,5 s (DFS)** |

**Duração (modelo exato de `play_step`, validado contra o MP4 atual):**
EK **16.83 → 16.90 min** · DFS **14.38 → 14.40 min**. O passo 433 cai em **285,9 s (V3)** /
**287,0 s (V4)** no modelo; o frame QA 4365 (`04:51` = 291 s) confirma o modelo com a montagem
inicial (≈5 s).

---

## A. CORREÇÃO DA COLISÃO DA `edgeTo` (feedback 1)

### A.1 O que está medido hoje (V3)

Geometria da `_AbaEdgeTo` (l.2223-2434), tudo derivado das constantes:

| objeto | fórmula / constante | valor |
|---|---|---|
| fila (6 chips) | `X_FILA=-4.60`, `LARGURA=0.72`, `PASSO=0.86` | x **−4.60 … +0.42**, y `−2.31 … −1.89` |
| coluna de info | `X_INFO = X0_ESTRUTURA + 5.14` | x começa em **+0.14** |
| `caminho` | `(X_INFO, −2.02)`, fonte 10 | x **0.14 … 0.82** |
| `gargalo` | `(X_INFO, −2.30)`, fonte 10 | x **0.14 … 0.56** |
| `fim` | centrado sob o último chip, `Y_FILA−0.35` | centro x **0.42**, y **−2.45** |
| setas | gutter entre chips | y **−2.10**, última termina em **x −0.31** |

Medido sobre **todos** os passos em que a aba `edge_to` está ativa na sequência V3:

```
EK : 120 passos edgeTo → 90 passos com colisão → 180 eventos
     chip5×caminho 90 · chip5×gargalo 90
DFS: 120 passos edgeTo →   0 passos com colisão
```

Bate exatamente com o QA (`QA_COLISAO_EK_0451.md`: "90 dos 120 passos"; DFS limpo). A causa é
aritmética: `−4.60 + 5·0.86 + 0.72 = 0.42 > 0.14`. Com 5 chips a borda é −0.44 e sobra folga —
por isso o problema só aparece no EK, que descobre os 6 vértices dentro da janela de gargalo.

### A.2 Decisão: mover **sempre** (não "só com 6 chips")

| opção | veredito |
|---|---|
| (a) mover só quando a fila tem 6 chips | **rejeitada**: (i) a condição muda *durante* a iteração — no passo em que o 6º vértice é descoberto o bloco pularia de `y` no meio do bloco de gargalo, exatamente quando o espectador está olhando; (ii) com 6 chips a coluna direita tem **0.72** de largura útil (0.42…1.14) e o caminho mede **0.68** → sobra 0.04 e qualquer caminho maior (outro `.txt`) estoura; (iii) seriam **duas** geometrias para validar. |
| (b) **sempre abaixo da fila** | **escolhida**: geometria única, determinística, independente do número de chips, no vão que hoje está vazio; 0 colisões medidas em 287 passos (146 EK + 141 DFS). |

### A.3 Geometria exata (contrato)

```python
class _AbaEdgeTo:
    ...
    X_INFO      = X0_ESTRUTURA          # -5.00  (era X0_ESTRUTURA + 5.14 = +0.14)
    Y_CAMINHO   = -2.74                 # era -2.02
    Y_GARGALO   = -2.96                 # era -2.30
```

- `caminho` e `gargalo` continuam `aligned_edge=LEFT` em `X_INFO`, fonte 10, mesmas cores,
  mesmos textos (`fmt_caminho(estado)` e `f"b = {fmt_num(gargalo)}"`) — **nenhuma string muda**
  (o `validate_flow_layout.py` continua comparando `aba.caminho.text`).
- Nada mais da aba se move: `X_FILA`, `Y_FILA`, `LARGURA`, `ALTURA`, `PASSO`, `frente`, `fim`,
  setas, caption (`Y_CAPTION=-1.52`) e o `vazio` ficam **idênticos**.

Folgas medidas com a nova posição (pior caso: 6 chips, caminho `0→2→4→5` = 0.68, `b = —` = 0.42,
altura de texto fonte 10 = 0.132):

| par | medida | exigência |
|---|---|---|
| chip × caminho / gargalo | **0.364** (chip base −2.310; topo do caminho −2.674) | > 0 |
| seta × caminho / gargalo | **0.50** (seta em −2.10) | > 0 |
| `fim` × caminho | 0 eventos (x disjunto: `fim` em ~0.42) | > 0 |
| caminho × gargalo | **0.088** (−2.806 … −2.894) | ≥ 0.04 |
| gargalo × guia (`−3.30`, topo −3.234) | **0.208** | ≥ 0.05 |
| bloco dentro do corpo (`−5.00…1.14 × −3.20…−1.30`) | sim | 0.00 |
| caminho/gargalo dentro do corpo | x −5.00…−4.32 | 0.02 |

O bloco fica no vão livre entre `fim` (base −2.503) e o topo do guia (−3.234): `−2.674 …
−3.026`, com 0.171 acima e 0.208 abaixo. É o arranjo mais folgado possível: descer **0,15**
ainda deixa 0,058 até o guia e subir **0,15** deixa 0,021 até o `fim` — a liberdade é ±0,15,
e o escolhido é o meio.

**O frame do QA continua sendo um passo `edge_to` no V4** (4365 = passo 433, linha 49
`bottle = float("inf")`, herdada do bloco de gargalo): o caminho `0→2→4→5` e o `b = —` passam a
ser escritos em `y=−2.74 / −2.96`, abaixo da fila — é o mesmo frame que ele reprovou, corrigido.

### A.4 O que o validador passa a proibir (em **todos** os passos, não numa amostra)

O ponto cego do `validate_flow_layout.py` (l.784-842) é comparar **só** chip × chip. Passa a
existir um teste **por passo** com a aba `edge_to` ativa na **sequência nova** (146/141 passos),
montando a aba real (`_AbaEdgeTo.construir`) e medindo caixas:

```python
PARES_EDGE_TO = [  # (papel_a, papel_b, folga)
    ("chip", "caminho", 0.00), ("chip", "gargalo", 0.00),
    ("chip", "seta", 0.00),    ("chip", "fim", 0.00),
    ("seta", "caminho", 0.00), ("seta", "gargalo", 0.00),
    ("caminho", "fim", 0.00),  ("gargalo", "fim", 0.00),
    ("caminho", "gargalo", 0.04),
    ("caminho", "guia", 0.05), ("gargalo", "guia", 0.05),
    ("caminho", "contadores", 0.02), ("gargalo", "contadores", 0.02),
    ("bloco", "caption", 0.04),
]
```

`chip × seta` entra com folga **0**: a seta do gutter nasce a 0,01 da borda do chip por
construção (`chips_fila`), então encostar não é colidir — o que o QA viu em 04:51 foi o
**texto** sobre a seta, coberto por `seta × caminho` (folga 0 é o piso que trava o texto).

Mais três invariantes:

1. `caixa_dentro` de `caminho` e `gargalo` em `(X0_ESTRUTURA, −3.20, X0_ESTRUTURA+6.20, −1.30)`.
2. `caminho.get_top()[1] < min(chip.get_bottom()[1]) − 0.30` (o bloco está **abaixo** da fila).
3. `largura(caminho) ≤ 6.20` e `largura(gargalo) ≤ 6.20` (texto nunca estoura a linha).

O teste roda para **todos** os passos `edge_to` (não `passos_edge[len//2]`), e a mensagem de
falha nomeia passo, papel e caixa (padrão `manim-qa-visual` §4).

---

## B. COREOGRAFIA DE ABAS POR LINHA DE ESCRITA (feedback 2 e 3)

### B.1 A ordem é a do fonte, não a do exemplo

| algoritmo | linha do fonte | código | `escrita` → aba | ordem |
|---|---|---|---|---|
| BFS | **90** | `self.edgeTo[w] = e` | `edge_to` | 1º |
| BFS | **91** | `self.marked[w] = True` | `marcados` | 2º |
| BFS | **92** | `queue.append(w)` | `busca` (fila) | 3º |
| DFS | **95** | `self.edgeTo[w] = e` | `edge_to` | 1º |
| DFS | **96** | `self.marked[w] = True` | `marcados` | 2º |
| DFS | **97** | `if self.dfs(g, w, t):` | `busca` (pilha, **push**) | 3º |

O pedido do usuário exemplifica `marked → edgeTo → BFS`; o código escreve `edgeTo` **antes** de
`marked`. **A cena segue o código** (§fidelidade) — o exemplo dele é invertido e está
documentado aqui para não ser "corrigido" por engano.

Blocos de reset/abertura também são escritas e entram na coreografia (medidos):
BFS 75 `edgeTo=[None]*V` → `edge_to`, 76 `marked=[False]*V` → `marcados`, 79 `queue=deque()` →
`busca`, 80 `queue.append(s)` → `busca`, 81 `marked[s]=True` → `marcados`;
DFS 76/77 (resets) e 80/81 (idem).

### B.2 A regra (uma linha de código, uma aba)

```python
def aba_do_passo(passo, aba_anterior: str) -> str:
    if passo.escrita is not None:      # a linha ESCREVE uma estrutura → a aba dela
        return passo.escrita
    ...                                # regra V3 inalterada (adj/rede/herda/busca/...)
```

- `escrita` tem **precedência** sobre a herança de `FlowNetwork.adj`,
  `FlowNetwork.validate_vertex` e `FlowEdge.*` — mas essas linhas só leem, então continuam
  herdando (`escrita is None`). As únicas linhas de `FlowEdge.*` com escrita são
  `self.flow += delta` (76/78/85) → `rede`, e é isso que a tabela da rede mostra.
- **Leitura não vira escrita**: `if e.residual_capacity_to(w) > 0` (88), `if not self.marked[w]`
  (89), `w = e.other(v)` (85), `v = self.edgeTo[v].other(v)` (53/59), `bottle = min(...)` (52),
  `for e in g.adj(v)` (84), `return self.marked[t]` (95/84) → `escrita is None` → aba herdada,
  sem nenhum realce de adição.
- `fundir_runs` **não pode** engolir run de 1 passo que contenha escrita:

```python
def fundir_runs(abas, min_run: int = 2, protegidos: list[bool] | None = None):
    ...
    if (j - i) < min_run and i > 0:
        protegido = bool(protegidos) and any(protegidos[i:j])
        if not protegido:
            ...
```

`calcular_abas` chama `fundir_runs(abas, 2, [p.escrita is not None for p in passos])`. Sem
`protegidos` o comportamento antigo é preservado (o autoteste do validador continua válido).

### B.3 Qual estado a aba usa — **medição que corrige o briefing**

O briefing pedia "usar `passo.estado_pos` quando `passo.escrita` aponta para a aba". **Medido**,
isso está errado na metade dos casos:

- `Step.estado` **já é o estado DEPOIS da linha** (o snapshot do `sys.settrace` é tirado antes
  de executar e `passos_detalhados` usa o próximo evento do mesmo frame), exceto nas linhas
  "pré-chamada" (`if`/chamada solta de função com view), onde ele é o estado **anterior**.
- `Step.estado_pos` é o `estado` do **passo seguinte**, isto é, o pós-linha **da próxima
  linha**. Usá-lo na aba escrita antecipa um passo.

Prova (eventos crus do EK, 1ª descoberta): evento da linha 90 → `edgeTo []`; evento da 91 →
`edgeTo [2]`; evento da 92 → `marked [0,2]`; evento da 84 → `fila [2]`. Logo o passo da 90 tem
`estado.edge_to = {2}` (pós-90 ✓) e `estado_pos.edge_to = {2}` (idem, porque a 91 não mexe em
`edgeTo`), mas `estado.marcados = [0]` e `estado_pos.marcados = [0,2]` — a aba `edge_to`
pintaria o chip do 2 de verde **uma linha antes** da 91. Pior: no DFS 77/80 (reset e
`marked[s]`) o `estado_pos` já tem `s` marcado no passo do reset.

Contrato do conteúdo (por aba):

| aba | fonte do conteúdo | por quê |
|---|---|---|
| `edge_to` | `passo.estado` | é pós-linha nas 26/21 escritas (verificado) e não antecipa `marked`/`caminho` |
| `marcados` | `passo.estado` | idem nas 31/26 escritas |
| `busca` | `passo.estado` — **exceto** o push do `dfs` | 83/88/92/98/99 têm `estado == estado_pos`; mas 81/97 são pré-chamada (o `if self.dfs(...)`) e o `estado` ainda **não** tem `w` na pilha |

Verificado nos **153 (EK) / 135 (DFS)** passos de escrita: a regra acima acerta **0 falhas**
(reset zera, `w` presente no `edgeTo`/`marked`, fila com `w` no fim, `popleft` sem `v`, push com
`w` na pilha, `return` com o topo removido). E `estado_pos["marcados"] != estado["marcados"]`
em **24 (EK) / 19 (DFS)** passos de `edge_to` — é o sinal que o teste de não-antecipação usa.

O relatório da fase `algoritmo` confirma a leitura (§2.4/§4: "o efeito do reset aparece no
`estado` pós-linha do próprio passo — o `estado_pos` é o estado do passo seguinte, que já contém
a escrita seguinte"). A recomendação dele em §5 ("animar com `passo.estado_pos`") vale **só**
para a lista da pilha no push — é a única linha escrita que é pré-chamada. O resto da aba usa
`estado`, e o teste #3 de §E.1 é a rede que impede a antecipação.

Implementação (em `flow_common.py`, sem tocar no trace):

```python
def estado_da_busca(passo) -> dict:
    """Estado com o efeito da linha visível na aba `busca`.

    `estado` é pós-linha; só o push do `dfs` (chamada dentro de `if`, linha
    pré-chamada) fica uma linha atrás — ali o `estado_pos` é o pós-linha.
    """
    est = passo.estado
    if passo.escrita != "busca" or passo.estado_pos is None:
        return est
    if len(passo.estado_pos.get("pilha") or []) > len(est.get("pilha") or []):
        return {**est, "pilha": list(passo.estado_pos["pilha"])}
    return est
```

(a troca é só da **lista**; contadores/`inspeções` continuam vindo de `estado`, para nada mais
andar um passo à frente). As abas `edge_to`/`marcados` **não** chamam `estado_pos` — e o
validador cobra isso (§E).

### B.4 Aba `busca` sem os textos das outras estruturas

Em `_AbaBusca` (l.1871-2085):

- **remover** `self.edge_to`, `self.marcados`, as três linhas de `construir` que os criam
  (l.1973-1982), o bloco `"edgeTo"`/`"marcados"` de `sincronizar` (l.2054-2069) e as duas
  entradas de `todos()`; `self.conteudos` fica só com `"inspecoes"`.
- **fica**: caption (`Fila (BFS) · ordem real` / `Pilha (DFS) · caminho de recursão`),
  chips (`0.42×0.30`, fonte 11), setas por índice (V3 §D), `frente`/`fim` (BFS) ou
  `base`/`topo` (DFS), e `inspeções {n}` em `(X0_ESTRUTURA+3.60, −2.58)`.
- medição de espaço: fila máx. **3** chips (borda direita −3.61) e pilha máx. **4** (−2.71); o
  texto de inspeções começa em −1.40 → folga **1.31** no pior caso (DFS) e ~0.85 de largura
  para dentro do corpo (que fecha em 1.14). Nada colide.

### B.5 Adição com animação (o que o usuário quer ver)

Nenhuma aba redesenha tudo a cada passo (hoje a `edgeTo` refaz a fila inteira quando qualquer
cor muda: 6 `FadeOut` + 6 `FadeIn` — é o "pisca" que o usuário descreveu como texto em vez de
ação). Passa a ser **incremental**, com identidade por vértice:

`_AbaEdgeTo.sincronizar(passo)` (novo, espelhando `_AbaBusca.sincronizar`):

```python
self.chips: dict[int, VGroup]      # por VÉRTICE (antes: reconstrução total)
self.estilos: dict[int, tuple]     # (cor, fill, opacidade) aplicados
self.setas: dict[int, Arrow]       # por ÍNDICE no gutter
```

1. `itens = self._itens(est)` (ordem de descoberta, igual a hoje);
2. chips que saíram → `FadeOut` + `self.remove` (lista `remover`);
3. chips novos (o `w` da linha) → `FadeIn` **+ `Flash(centro, color=COR_ACENTO,
   line_length=0.14, num_lines=8, flash_radius=0.26, stroke_width=2)`**; entram com
   `adicionar` (a cena faz `add` antes do play);
4. chips que mudaram de índice → `animate.move_to`;
5. estilo (`cor`/`fill`/`opacidade` do papel caminho/alcancado/neutro) → `animate.set_stroke` +
   `set_fill` (como `_AbaMarcados._aplicar_estilo`);
6. setas: sobras `FadeOut`, novas `FadeIn`, e **todas** recebem `put_start_and_end_on` no
   gutter atual (mesma regra do V3 §D.2);
7. `caminho`/`gargalo` só trocam quando o **texto** muda (`_troca_texto` no mesmo `x/y`).

`_AbaMarcados.sincronizar`: manter o estilo atual e, para cada vértice que **acabou de** ficar
marcado (`marcados - self.acesos`), somar `Flash(chip, color=PALETA["alcancado"][0],
line_length=0.12, num_lines=8, flash_radius=0.30)` + `Indicate(chip, color=..., scale_factor=1.12)`.

`_AbaBusca.sincronizar`: o `FadeIn` do chip novo (já existe) ganha o mesmo `Flash` em
`COR_ACENTO`; o `FadeOut` do que sai (pop) fica como está.

Contagem de adições realçadas (FadeIn+Flash): **EK 82** (26 `edge_to` + 31 `marcados` +
25 `busca`) · **DFS 67** (21 + 26 + 20). Pops (só `FadeOut`): **18 (EK) / 20 (DFS)**.
`Flash`/`Indicate` entram na lista de animações do mesmo `play` do passo — **sem tempo extra**
(o `run_time` do play já os limita).

### B.6 Troca de aba continua em DOIS plays — com realce local no ramo de troca (rev. 4.1)

A troca continua em dois plays: `self.play(*sai_aba)` (todos os `FadeOut` com `RITMO["fade"]`)
e **depois** `self.play(*[FadeIn(...)])`. O `extra = 2·fade` já sai da pausa. O `_i`/`abas`
continua indexado por passo (`preparar(passos[0])` + um `atualizar` por passo).

**Rev. 4.1 — o que entra.** O `FadeIn` do corpo é *fundo* (a aba inteira aparece), não
*destaque*: o olho não sabe qual elemento a linha escreveu. `atualizar` ganha, **só** no ramo
de troca, o `Flash` do elemento novo **dentro de `anims`** — logo ele toca no **play seguinte**
ao `FadeIn` (o play de indicador+grafo+estado), nunca junto do fade (flashes de um mobject
ainda invisível) e sem nenhum play extra.

Identificação do elemento (diferença entre `passo.estado` e `self.estado_anterior`, ambos vistos
na tela; na `busca` os dois lados passam por `estado_da_busca`):

| aba | elemento novo | cor / parâmetros |
|---|---|---|
| `edge_to` | `ordem_descoberta` − anterior | `COR_ACENTO`, `line_length=0.14`, `num_lines=8`, `flash_radius=0.26`, `line_stroke_width=2` |
| `marcados` | `marcados` − anterior | `PALETA["alcancado"][0]`, `line_length=0.12`, `num_lines=8`, `flash_radius=0.30`, `line_stroke_width=2` + `Indicate(chip, color=..., scale_factor=1.12)` |
| `busca` | `fila`/`pilha` − anterior | `COR_ACENTO`, idem `edge_to` |

Regras do contrato:

1. só emite quando `passo.escrita == aba` (a linha escreve **esta** estrutura) — leitura que
   herda aba não pisca;
2. exige **exatamente 1** elemento novo; com 0 (reset do §B.1) ou >1 devolve `[]` e a adição
   aparece pelo `FadeIn` do corpo (é reconstrução, não adição pontual);
3. o alvo é o **mobject vivo** que `construir(passo)` acabou de criar (`self.chips[v]` da aba),
   que já está em cena (`self.add(*novos)` antes do fade-in);
4. nenhuma cor nova: as três já estão na legenda/guia (§I.9).

Medido no trace real (mesma classificação de `tipo_de` do validador, `popleft`/`return`
excluídos): **70 EK / 55 DFS** adições com realce de elemento único; **12 / 12** reconstruções
(`init` 38/39 + reset 75/76, EK; 39/40 + 76/77, DFS) só com `FadeIn` do corpo; **0** adições
sem entrada animada. Total inalterado: 82 / 67. Duração: **0,0 s** de acréscimo.

---

## C. DFS (Ford-Fulkerson recursivo)

Mesma coreografia, com a `busca` = **pilha de recursão** (`_pilha(frame)`):

| passo | linha | efeito | aba |
|---|---|---|---|
| push | 81 / 97 | entra o frame do argumento (`s` na 81, `w` na 97) | `busca` (chip novo + Flash) — pilha do `estado_pos` |
| pop | 88 / 98 / 99 | `return` fecha o frame | `busca` (chip sai) — estado pós-return |
| descoberta | 95 → 96 → 97 | `edgeTo` → `marked` → `dfs` | `edge_to` → `marcados` → `busca` |

- A pilha cresce **no passo da chamada** (81/97) via `estado_da_busca` (§B.3); o pop aparece no
  passo do `return` (o `estado` já é pós-return). Medido: **20 chamadas** (5 na 81 + 15 na 97) e
  **20 `return`** (4 na 88 + 12 na 98 + 4 na 99).
- `pilha` máx. **4** chips (setas 1..3, gutter 0.24 — V3 §D.2 intacto).
- A `edgeTo` do DFS tem no máx. **5** chips e já não colidia (QA); a geometria nova do §A é a
  mesma — 0 colisões em 141 passos.

---

## D. NÚMEROS (sequência, trocas, ritmo)

### D.1 Sequência de abas e distribuição

| métrica | EK V3 | EK V4 | DFS V3 | DFS V4 |
|---|---|---|---|---|
| passos | 1510 | 1510 | 1281 | 1281 |
| `adj` | 99 | **99** | 99 | **99** |
| `busca` | 627 | **572** | 398 | **353** |
| `marcados` | 113 | **144** | 113 | **139** |
| `edge_to` | 120 | **146** | 120 | **141** |
| `rede` | 551 | **549** | 551 | **549** |
| **trocas** | 16 | **99** | 16 | **74** |
| runs | 17 | **100** | 17 | **75** |
| runs de 1 passo | 0 | **57** | 0 | **37** |

Transições medidas (EK): `marcados→busca` 30 · `edge_to→marcados` 25 · `busca→edge_to` 24 ·
`edge_to→rede` 5 · `rede→edge_to` 5 · `busca→marcados` 5 · `rede→marcados` 2 · `adj→rede` 1 ·
`marcados→edge_to` 1 · `busca→rede` 1 = **99**.
DFS: `edge_to→marcados` 20 · `marcados→busca` 20 · `busca→edge_to` 19 · `edge_to→rede` 5 ·
`rede→edge_to` 5 · `rede→marcados` 2 · `adj→rede` 1 · `marcados→edge_to` 1 · `busca→rede` 1 =
**74**.

Amostra real (EK, 1ª busca, 2ª descoberta) — a coreografia pedida:

```
 321 L68 residual_capacity_to  escrita=—        aba=busca     pausa 1.0
 322 L89 has_augmenting_path   escrita=—        aba=busca     pausa 1.0
 323 L90 has_augmenting_path   escrita=edge_to  aba=edge_to   pausa 1.0   ← chip novo (1) + ←2
 324 L91 has_augmenting_path   escrita=marcados aba=marcados  pausa 0.55  ← 1 fica verde
 325 L92 has_augmenting_path   escrita=busca    aba=busca     pausa 0.55  ← 1 entra na fila
 326 L84 has_augmenting_path   escrita=—        aba=busca     pausa 0.55
```

### D.2 Duração e ritmo

| | EK | DFS |
|---|---|---|
| V3 (modelo) | 16.83 min (1010,1 s) | 14.38 min |
| V4 | **16.90 min (1013,9 s)** | **14.40 min** |
| delta | **+3,9 s** | **+1,5 s** |

O delta é pequeno porque a troca de aba paga-se na pausa (`espera = pausa − 2·fade`): nos
passos de pausa 1,0/1,7 ela é **absorvida** (custo 0); só os de pausa 0,55 somam **+0,0667 s**.
Passo continua entre **0,60 e 1,00 s** (o teste `ritmo` do validador segue válido).

`RITMO` **não muda** (`play 0.40`, `play_destaque 0.4667`, `fade 0.1333`, pausas
0.20/0.333/0.533). Uma aba de 1 passo fica em cena de **0,60 a 1,00 s** (9–15 frames a 15 fps).
Se o usuário achar curto, o botão documentado (não aplicar agora) é um `RESPIRO_ESTRUTURA =
3/15 s` nos passos com `escrita in ("edge_to","marcados")`: **+11,4 s (EK) / +9,4 s (DFS)**.

> **Nota de padrão da equipe.** O piso de 1,0 s por linha do painel de código
> (`PAUSA_CODIGO_MIN`) **não** está implementado no projeto: o contrato validado pelo usuário
> é a tabela `RITMO` (passo de 0,60–1,00 s) e os carimbos de tempo que ele cita (04:51) supõem
> esse ritmo. Aplicá-lo agora levaria o EK a ~26 min e invalidaria o 480p já assistido — fica
> registrado como decisão pendente de produto, **fora** desta correção.

---

## E. VALIDADORES

### E.1 `validate_flow_layout.py`

**Trocar**

| item | hoje | V4 |
|---|---|---|
| `abas` → `esperada` (l.648-655) | `rede 551 · busca 627/398 · marcados 113 · edge_to 120 · adj 99` | `rede 549 · busca 572/353 · marcados 144/139 · edge_to 146/141 · adj 99` |
| `abas` → l.678 | `trocas == 16` | **99 (EK) / 74 (DFS)** |
| `troca_sem_fantasma` l.1218 | `trocas == 16` | **99 / 74** |
| `fantasmas` l.1100-1111 | audita `busca.edge_to` (deixa de existir) | auditar `busca.inspecoes` (texto trocado sai da lista viva) |
| `conteudo_abas` l.784-842 | **1** passo de `edgeTo`, só chip×chip | **todos** os passos `edge_to` + `PARES_EDGE_TO` do §A.4 |

**Adicionar**

1. `escrita` manda na aba: a sequência **crua** (antes da fusão) é `passo.escrita or
   aba_do_passo(...)`, e depois da fusão **nenhuma posição com `escrita` muda de aba** (o run
   dela é protegido).
2. `fundir_runs` protege escrita: `fundir_runs(["b","e"], 2, [False,True]) == ["b","e"]` e
   `fundir_runs(["b","b","e","b"], 2, [False,False,True,False]) == ["b","b","e","b"]`; sem
   `protegidos`, comportamento antigo (o autoteste atual continua).
3. **Sem antecipação**: nos **24 (EK) / 19 (DFS)** passos de `edge_to` em que
   `estado_pos["marcados"] != estado["marcados"]` (a linha 91 vem em seguida), a aba `edge_to`
   montada tem de usar `estado["marcados"]` — o chip do `w` **não** pode estar verde antes da
   91. Idem `marcados` no par reset→`marked[s]` (DFS 77→80).
4. **Escrita visível na própria linha**: para todo passo com `escrita`, o estado usado contém a
   escrita — `edge_to`: `w` presente (ou `{}` no reset); `marcados`: `w` presente (ou `[]`);
   `busca`: `append` → `fila[-1] == w`; `popleft` → `v ∉ fila`; `dfs` (push) → `w ∈ pilha` do
   estado escolhido; `return` → pilha com o topo removido.
5. **Adição animada (rev. 4.1, duas classes explícitas)** — o teste deixa de aceitar o
   `FadeIn` do corpo como atalho:
   - `tipo_de(passo) != "reset"` → `Flash` (ou `Indicate`) presente em `anims`, **medido em
     70 EK / 55 DFS passos**, tanto no ramo de mesma aba quanto no de troca;
   - `tipo_de(passo) == "reset"` → **12 / 12** passos, sem `Flash`/`Indicate` (não há elemento
     único) e com `troca is not None` (o corpo entra inteiro pelo `FadeIn` do 2º play);
   - soma das duas = 82 / 67 e **nenhuma** adição sem entrada animada;
   - para um passo **sem** escrita cujo estado não mudou, lista vazia (nada pisca à toa).
6. `_AbaBusca` sem texto de estrutura: `not hasattr(busca, "edge_to")` e
   `not hasattr(busca, "marcados")`, `"marcados" not in busca.conteudos`, e
   `"inspeções" in {t.original_text.split()[0] for t in busca.todos() if isinstance(t, Text)}`.

**Manter**: fonte 11.06, páginas 18/19, views 14/15, passos 1510/1281, gutter, `PARES`,
legenda 7/7, guia de símbolos, selo, setas da pilha, dois plays, `todos()` vivo.

### E.2 `validate_flow_scenes.py`

**Nada a mudar** (o golden é `stages`, que não carrega `escrita`/`estado_pos`). Rodar e conferir
`SHA_STAGES_ESPERADO = c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a`.
Se a fase `algoritmo` mudar `flow_record.py`, este é o portão que diz se o vídeo existente
deixou de ser o mesmo.

### E.3 `validate_flow_videos.py`

`ALVO` (l.55) passa a ser o medido no modelo: `{"edmonds": 16.90 * 60, "ford": 14.40 * 60}`
(cena de execução; o vídeo completo soma a intro, que não muda — comparar sempre o mesmo tipo
de arquivo). Manter: último frame não preto, bandas, 7/7, `#4a4e69` ausente, `#ef476f`/`#06d6a0`
fora da legenda.

---

## F. LISTA DE MUDANÇAS POR ARQUIVO/FUNÇÃO

### `src/flow_common.py`

| símbolo | linha | mudança |
|---|---|---|
| `aba_do_passo` | 1690-1707 | 1ª linha: `if passo.escrita is not None: return passo.escrita` |
| `fundir_runs` | 1710-1722 | parâmetro `protegidos: list[bool] | None = None`; run de 1 com escrita nunca funde |
| `calcular_abas` | 1725-1733 | passa `[p.escrita is not None for p in passos]` |
| **novo** `estado_da_busca` | junto de `fmt_pilha` | §B.3 (só a lista da pilha vem do `estado_pos` no push) |
| `_AbaBusca.__init__` | 1877-1890 | remover `edge_to`, `marcados`; `conteudos = {"inspecoes": ""}` |
| `_AbaBusca.construir` | 1935-1988 | remover os `Text` de `edgeTo` e `marcados`; **manter** `inspeções`; lista por `estado_da_busca` |
| `_AbaBusca.sincronizar` | 2000-2070 | remover o bloco `edgeTo`/`marcados`; `Flash` no chip novo; lista de `estado_da_busca` |
| `_AbaBusca.todos` | 2072-2085 | tirar `edge_to`/`marcados` |
| `_AbaMarcados.sincronizar` | 2166-2216 | `Flash`+`Indicate` nos vértices que acabaram de ficar marcados |
| `_AbaEdgeTo.X_INFO/Y_CAMINHO/Y_GARGALO` | 2239-2241 | `X0_ESTRUTURA`, `−2.74`, `−2.96` |
| `_AbaEdgeTo.__init__` | 2243-2256 | `chips: dict[int, VGroup]`, `estilos: dict[int, tuple]`, `setas: dict[int, Arrow]`; remover `assinatura` |
| `_AbaEdgeTo._montar_fila` | 2297-2336 | devolve os chips indexados por vértice (mantém `chips_fila`) |
| `_AbaEdgeTo.construir` | 2338-2361 | monta com o novo bloco de info (sem mudar strings) |
| `_AbaEdgeTo.sincronizar` | 2373-2421 | **incremental** §B.5 (adicionar/remover/mover/setar/estilo + `Flash`) |
| `_AbaEdgeTo.todos` | 2423-2434 | incluir o que está em cena (chips, setas, frente, fim, vazio, caminho, gargalo) |
| `EstruturaPanel.__init__` | ~2803 | `self.estado_anterior = None` |
| `EstruturaPanel.preparar` | ~2880 | gravar `self.estado_anterior = estado_da_busca(passo)` |
| **novo** `EstruturaPanel._realce` | junto de `_atualizar_contadores` | §B.6 rev. 4.1: `Flash` (+`Indicate` em `marcados`) do elemento novo |
| `EstruturaPanel.atualizar` | 2897-2921 | ramo de troca: `anims = self._realce(passo) + self._atualizar_contadores(passo)`; gravar `estado_anterior` nos dois ramos (`play_step` **não** muda) |

### `validate_flow_layout.py`

§E.1 (distribuição, 99/74, `PARES_EDGE_TO` em todos os passos, sem antecipação, escrita
visível, adição animada, `busca` sem textos, `fantasmas`).

### `validate_flow_videos.py`

§E.3 (`ALVO`).

### Não tocar

`src/flow_record.py` (trace/golden), `src/*_scene_new.py` (intros e classes de execução são só
`montar/executar_passos/fechar`), `RITMO`, `PALETA`, `GUIA_SIMBOLOS`, `StatePanel`, `CodePanel`,
`FlowGraphView`, `algs4-py/`.

---

## G. FORA DE ESCOPO

- **Intros** (`EdmondsKarpIntro_new`, `FordFulkersonIntro_new`): não mudam.
- **`algs4-py/`**: read-only (fonte real do painel de código e do trace).
- **Render**: nenhum; o 480p é etapa do pipeline (`build/media`) e o 1080p60 está **bloqueado**
  até o usuário validar o 480p.
- **`flow_record.py`**: o `estado_pos`/`escrita` são da fase `algoritmo` (relatório entregue,
  Gate 0 8/8, sha `c19ee524…a3a`); esta fase **não** toca no gravador nem no golden.

---

## H. PRESERVAÇÃO DO CÓDIGO ANTIGO

Antes de sobrescrever, copiar para `src/_snapshot_v3/` (a pasta já existe com
`flow_record_v3.py` e `validate_flow_videos_pre_fix9.py` — **não sobrescrever esses dois**):

```
src/_snapshot_v3/flow_common_v3.py
src/_snapshot_v3/validate_flow_layout_v3.py
```

Sem sufixo `_new` nos arquivos vivos (`flow_common.py` continua sendo o alvo); o snapshot é a
rede de segurança.

---

## I. AUTOCONFERÊNCIA (checklist `manim-qa-visual`)

| # | critério | resultado |
|---|---|---|
| 1 | todo nó tem `str(v)` | 6/6 (inalterado) ✓ |
| 2 | toda aresta tem `f/C` + `→C−f ←f` com fundo opaco | 8/8 (inalterado) ✓ |
| 3 | chip × caminho/gargalo (todos os passos `edgeTo`) | **0** em 146 (EK) e 141 (DFS) ✓ |
| 4 | chip × `fim` / seta × `fim` | **0** ✓ |
| 5 | caminho/gargalo × `fim` / guia / contadores | **0** (folgas 0,171 / 0,208 / ≥0,02) ✓ |
| 6 | bloco de info dentro do corpo | x −5,00…−4,32; y −2,674…−3,026 ✓ |
| 7 | painel × painel / código × estrutura | 0,20 (inalterado) ✓ |
| 8 | nada fora de x ∈ [−6,56; 6,83], y ∈ [−3,72; 3,55] | ✓ |
| 9 | legenda 7/7 (nenhuma cor nova) | ✓ (`COR_ACENTO` e `#80ed99` já são estruturais/papel) |
| 10 | símbolo distingue tipo (ponto=aresta, anel=vértice) | ✓ (inalterado) |
| 11 | toda aba usada, ≥ 8 passos | 99/572/144/146/549 e 99/353/139/141/549 ✓ |
| 12 | a aba segue a **linha escrita**, na ordem do fonte | 90→91→92 / 95→96→97 ✓ |
| 13 | leitura não vira escrita | 88/89/84/85/53/59/52 → `escrita None` ✓ |
| 14 | run de 1 passo de escrita não é fundido | 57 (EK) / 37 (DFS) runs de 1 preservados ✓ |
| 15 | troca de aba em dois plays, sem mobject compartilhado | inalterado ✓ |
| 16 | sem antecipação de estado | `estado` nas 3 abas; `estado_pos` só na lista da pilha no push — **0 falhas** em 153/135 passos de escrita ✓ |
| 17 | adição realçada (`FadeIn`+`Flash`), **inclusive na troca de aba** (rev. 4.1) | **70/55** com `Flash` de elemento único + **12/12** reconstruções só com `FadeIn` do corpo = 82/67 ✓ |
| 18 | `busca` sem texto de estrutura | `edge_to`/`marcados` removidos ✓ |
| 19 | último frame não preto | fecho com corte (inalterado) ✓ |
| 20 | passo entre 0,60 e 1,00 s | mínimo 0,60 / máximo 1,00 (com as 99 trocas) ✓ |

Pendente para o `codificador` provar com número: #3-#6 no código real, #12-#14, #16-#17 e #18
por introspecção; o QA de pixels fica para depois do 480p.

---

## J. RISCOS

| risco | prob. | mitigação |
|---|---|---|
| 99 trocas de aba parecerem "pisca-pisca" | média | cada troca é um passo do painel de código (0,6–1,0 s); o `Flash` marca a adição; se o usuário reclamar, `RESPIRO_ESTRUTURA` medido (+11,4 s) |
| `fundir_runs` mudar a sequência sem `protegidos` | baixa | parâmetro opcional; autoteste antigo do validador mantido |
| `_AbaEdgeTo` incremental deixar fantasma | média | `todos()` cobrado pelo teste `troca_sem_fantasma` (já existe) e `remover` explícito |
| `estado_pos` usado "por engano" e antecipar `marked` | alta sem o teste #16 | teste #3 do §E.1 |
| DFS: push invisível na linha da chamada | média | `estado_da_busca` (§B.3) + teste #4 |
| duração/alvo desatualizados (19.44 no `validate_flow_videos`) | certa | §E.3 re-baseline medido |
| recomendar `estado_pos` "porque o relatório manda" | média | §B.3: o próprio relatório (§2.4/§4) mostra que `estado` é o pós-linha; teste #3 de §E.1 |

---

## K. RESUMO DE UMA LINHA

A `edgeTo` ganha **bloco de info fixo abaixo da fila** (0 colisões em 287 passos, contra 90/120),
a aba passa a ser **a estrutura escrita pela linha** (`edge_to`→`marcados`→`busca`, na ordem real
do 90/91/92 e do 95/96/97), a `busca` **perde os textos** `edgeTo`/`marcados`, a adição entra com
`FadeIn`+`Flash` e o `estado` da linha (não o `estado_pos`, que anda uma linha à frente) —
**99/74 trocas**, 16.90/14.40 min, paleta e legenda intactas.

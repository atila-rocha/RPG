# RELATÓRIO ALGORITMO — Fluxo Máximo (`tinyFN`)

Fase **ALGORITMO** da obra de Fluxo Máximo. Port fiel do `algs4-java` para `algs4-py`
(`FlowEdge`, `FlowNetwork`, `FordFulkerson`/BFS e `FordFulkersonDFS`/DFS), gravador de trace
multi-módulo (`src/flow_record.py`) e validador sem Manim (`validate_flow_scenes.py`).

## 0. Veredito

| item | estado |
|---|---|
| port `algs4-py` (4 arquivos) | valor 4.0, corte `[0, 2]`, fluxos finais conferidos |
| trace linha a linha | **1661** passos (BFS) / **1218** (DFS) — 3 módulos, 13/14 views |
| trace compacto (golden) | **11** passos nas duas variantes, assinaturas idênticas |
| `validate_flow_scenes.py` | **6/6 grupos ok** (entrada, golden, invariantes, determinismo, linha a linha, funções) |
| `validate_mst_scenes.py` / `validate_dijkstra_scenes.py` | ok (a correção em `linklist.py` não regrediu nada) |
| render / cenas | **não tocados** (nenhum `src/*_scene_new.py`, nenhum `media/`) |

`stages_fluxo.json` exportado por último com
`sha256 = 4428184ba0a5b6dcb68cce43a50ea9f073414e10bc2c3478f2182952acdc4d3d`.

## 1. Entrada — `dataset/tinyFN.txt`

Formato **`FlowNetwork`** (o mesmo do `FlowNetwork(In in)` do Java), declarado em
`flow_record.py` (`REDE_PADRAO`, override `FLUXO_GRAFO`, sem fallback embutido):

```
6          V
8          E
0 1 2.0    u w capacidade   (E linhas)
...
4 5 3.0
```

- CRLF, sem BOM, `utf-8-sig`; espaços/tabs arbitrários, linhas em branco e `#` ignorados.
- **O primeiro inteiro é `V`** (6) e o segundo é `E` (8) — diferente de `tinyUF` (`V` + pares) e
  `rs1423` (`N` = nº de pares). O papel está declarado no parser, nunca adivinhado.
- Leitura em **dois níveis**, ambos executados de verdade:
  1. `flow_record.ler_rede_txt` — valida para o painel: `0 <= u,w < V`, sem laço, sem aresta
     paralela (o estado indexa por `(u, w)`), `len(arestas) == E`, capacidade `float` (aceita
     `2`, `2.0`, `1.9E-4`); erro sempre com caminho + linha.
  2. `FlowNetwork._ler_arquivo` — o leitor real do port, token a token, com a **linha física**
     de cada token nas mensagens de erro.
- `s = 0`, `t = V - 1 = 5`, como no `main` do Java. Layout e textos derivam do arquivo.

Arestas (índice = ordem do arquivo = ordem de inserção = ordem da tabela do painel):

| # | aresta | capacidade | fluxo final |
|---|---|---|---|
| 0 | 0→1 | 2 | 2 |
| 1 | 0→2 | 3 | 2 |
| 2 | 1→3 | 3 | 1 |
| 3 | 1→4 | 1 | 1 |
| 4 | 2→3 | 1 | 1 |
| 5 | 2→4 | 1 | 1 |
| 6 | 3→5 | 2 | 2 |
| 7 | 4→5 | 3 | 2 |

## 2. O algoritmo (implementação real, não recriada)

### 2.1 `algs4/flow_edge.py`

`FlowEdge(v, w, capacity)` com atributos `v`, `w`, `capacity`, `flow` (sem acessores, como no
port). `from_()`, `to()`, `other(vertex)`, `residual_capacity_to(vertex)` (reverso = `flow`,
direto = `capacity - flow`) e `add_residual_flow_to(vertex, delta)` (satura em `capacity` e zera
resíduo numérico com `eps = 1e-10`). `raise` para vértice que não é extremo.

### 2.2 `algs4/flow_network.py`

`FlowNetwork(arquivo)` / `FlowNetwork(file=...)`; `self._adj` é uma `Bag` por vértice (`adj` é
método). `add_edge` insere a **mesma aresta** nas duas pontas (por isso `adj(v)` mostra arestas
incidentes, com fluxo nos dois sentidos).

> **Ordem importa:** `Bag.add` insere no **início**, então `adj(v)` devolve as arestas na ordem
> **reversa** de inserção. É essa ordem que escolhe o caminho aumentante; trocar por `append`
> muda o golden. (Correção necessária em `algs4/utils/linklist.py`: `LinkIterator.__iter__`,
> que o Python 3.13 exige para iterar a `Bag`.)

### 2.3 `algs4/ford_fulkerson.py` (Edmonds-Karp / BFS)

| função | papel |
|---|---|
| `__init__(g, s, t)` | valida `s`/`t`, zera `marked`/`edgeTo`/`value`, checa fluxo inicial viável, `value = excess(g, t)` e o laço `while has_augmenting_path(...)` |
| `has_augmenting_path(g, s, t)` | BFS na rede residual com `deque`; `while queue:` (fiel ao `while (!queue.isEmpty())` do Java), sem `break` em `t` |
| `excess(g, v)` | saldo de fluxo no vértice (`-` se a aresta sai, `+` se entra) |
| `is_feasible(g, s, t)` | capacidade em toda aresta, `|f| = excesso(s) = excesso(t)`, conservação nos internos |
| `in_cut(v)` / `check(g, s, t)` | corte `S = marked`; `mincut_value` e `|f| = capacidade do corte` |
| augmentação | `bottle = min(residual)` no 1º laço, `add_residual_flow_to` no 2º, `value += bottle` |

### 2.4 `algs4/ford_fulkerson_dfs.py` (Ford-Fulkerson / DFS)

Mesma classe, com `dfs(g, v, t)` recursiva e **retorno antecipado** ao alcançar `t`
(`has_augmenting_path` só marca `s`, chama `dfs` e devolve `marked[t]`). Resultado idêntico;
o caminho por iteração é o que muda.

## 3. Trace em passos

Gravador: `src/flow_record.py` (não implementa nada — roda o port sob `sys.settrace`).
`MODULOS_DETALHADO` = algoritmo + `flow_network` + `flow_edge`; cada função executada é uma
**view** de código (`FUNCOES_PAINEL`, derivada do `ast` do fonte real).

| | BFS (Edmonds-Karp) | DFS (Ford-Fulkerson) |
|---|---|---|
| passos linha a linha | **1661** | **1218** |
| passos compactos | **11** | **11** |
| views | 13 | 14 |
| módulos no trace | 910 + 554 + 197 | 697 + 344 + 177 |
| buscas / augmentações | 5 / 4 | 5 / 4 |
| inspeções de aresta | **69** = 16+16+16+16+5 | **27** = 3+4+7+8+5 |

`Step` é imutável: `linha, acao, destaque, estado, pausa, modulo, funcao`.
Pausas: 0,55 s (bookkeeping, 1174/853 passos), 1,0 s (decisão, 475/337), 1,7 s (fecho: 12/28).

### 3.1 Schema de `estado` (tudo lido do frame real)

`V, E, s, t, arestas, capacidades, fluxos, residual_direta, residual_reversa, marcados, edge_to,
caminho, gargalo, valor, fila (BFS), pilha (DFS), iteracao, augmentacoes, inspecoes, corte,
corte_capacidade, augmentando, v, w, e, bottle, vertex, delta, s_frame, t_frame, aux`.

### 3.2 Golden (`validate_flow_scenes.py`), idêntico nas duas variantes

```
inicio · (busca,nova) (valor) ×4 · (busca,fim) · (corte,fechado)      = 11 passos
```

- valor final **4**, corte **{0, 2}**, capacidade do corte **4**, `augmentacoes = 4`, `iteracao = 5`;
- caminhos: `0→2→4→5`, `0→2→3→5`, `0→1→4→5`, `0→1→3→5` — gargalo **1** nos quatro;
- fluxos finais da tabela §1 (BFS e DFS terminam com o mesmo `fluxos` e o mesmo `corte`);
- `stages_fluxo.json` (por índice de passo, nunca por timestamp) + SHA-256 acima;
  entrada diferente ⇒ `stages_fluxo_<stem>.json`, nunca sobrescreve o padrão.

## 4. Invariantes (cobradas em TODO passo, compacto e detalhado)

| invariante | verificação |
|---|---|
| capacidade | `0 - eps <= f <= C + eps` em toda aresta, em todo passo |
| resíduos | `res_direta = C - f`, `res_reversa = f` |
| caminho | começa em `s`, termina em `t`, arestas contíguas e existentes; durante a busca toda aresta do caminho tem residual `> 0` |
| marcados | únicos, dentro de `0..V-1`; `corte == marcados` |
| `edge_to` | só vértices válidos e arestas da rede |
| valor | `|f| = saída(s) = entrada(t)` e conservação nos internos |
| determinismo | duas gravações ⇒ mesma assinatura (destaque + valor + fluxos + fila/pilha + inspeções) |
| cobertura | toda view do painel executa; linhas obrigatórias por view; nenhum passo cai na rede de segurança de `_descrever` |

**Exceção declarada — janela de augmentação:** entre o `v = t` que prepara o 2º laço e o
`self.value += bottle`, o fluxo é atualizado **aresta por aresta**; nesse intervalo a conservação
e `|f| = saída(s)` ainda não valem (estado real do algoritmo). A janela é derivada do `ast`
(`_janela_augmentacao`), não digitada, e chega ao validador pelo campo `estado["augmentando"]`.

## 5. Pontos de destaque visual (`destaque` do `Step`)

| tipo | status | onde nasce | uso na cena |
|---|---|---|---|
| `inicio` | — | 1º passo (montagem da rede) | abertura |
| `busca` | `nova` / `fim` | `return marked[t]` da busca | fecha cada iteração: caminho + gargalo, ou "sem caminho" |
| `busca` | `olhando` / `examina` / `descoberto` | `w = e.other(v)`, `residual_capacity_to(w) > 0`, `edgeTo[w] = e` | aresta em exame e aresta de descoberta |
| `caminho` | `aumentante` | 1º laço (gargalo) | caminho `s→t` no grafo |
| `aumento` | `augmenta` | 2º laço (`add_residual_flow_to`) | empurra o gargalo, aresta por aresta |
| `valor` | — | `self.value += bottle` | `|f|` acumulado (4 passos) |
| `corte` | `cruza` / `lado_s` / `lado_t` / `fechado` | `check` e `in_cut` | min-cut = max-flow no fecho |
| `aresta` | `insere` | `FlowNetwork.__init__ → add_edge` | montagem da rede (8 passos) |

Distribuição dos destaques (BFS/DFS): `busca` 164/74, `corte` 31/31, `caminho` 12/12,
`aumento` 12/12, `aresta` 8/8, `valor` 4/4, `inicio` 1/1 — todo tipo aparece e é usado.

Sugestões para a fase visual (vindas do trace, não do gosto):
- **BFS**: a fila (`estado["fila"]`) é o painel natural; `while queue:` esvazia a fila inteira
  mesmo depois de alcançar `t` (16 inspeções por busca). **DFS**: `estado["pilha"]` é o caminho de
  recursão aberto; a busca para em `t` (3/4/7/8/5 inspeções). A diferença 69 × 27 é didática.
- A **tabela de arestas** (ordem do arquivo) com `f/C` e `res. direta`/`res. reversa` sustenta
  "saturada ⇒ bloqueia" e "0→2 termina 2/3 e não cruza o corte".
- O caminho aumentante muda a cada iteração (4 caminhos distintos de 3 arcos) — vale destacar
  `edgeTo` → `caminho` antes de empurrar o gargalo.

## 6. Desvios e decisões (para auditoria das próximas fases)

1. **BFS sem `break` em `t`** — o port segue o Java (`while queue:`); a primeira versão com
   `and not marked[t]` dava 49 inspeções e um caminho diferente. Golden 69/27 depende disso.
2. **Regra pré/pós-chamada** (`_linhas_pre_chamada`, derivada do `ast`): em teste de
   `if`/`while`/`assert` ou chamada solta de função com view, o passo usa o estado **anterior** à
   chamada (o pós é o resultado da chamada inteira e faria o filme voltar no tempo: inspeções de
   16→0, `marked` já completo antes da busca). Em `x = f(...)` vale o pós, porque o valor
   atribuído é o que interessa.
3. **Desfecho da busca no `return`**: a linha 46 (`while has_augmenting_path(...)`) é texto
   neutro; "achou caminho … (gargalo …)" / "sem caminho aumentante" é narrado no `return
   marked[t]` (EK 95 / DFS 83) — âncora do modo compacto.
4. **Colapso de continuação de comando** (`_faixas_simples`) e dedupe de eventos idênticos
   consecutivos (list comprehension do `FlowNetwork.__init__`: 7 eventos → 1 passo).
5. **`FlowNetwork.validate_vertex`, `from_`, `to`, `__str__`, `edges`** ficam fora das views
   (uma linha, não ensinam nada); as linhas que as chamam continuam visíveis.
6. `DESLOC_FUNCAO` mede no `ast` o deslocamento de `excess`/`is_feasible`/`check` entre a BFS e a
   DFS (+3 linhas) — nenhum número de linha é digitado à mão.

## 7. Pendências para as fases seguintes

- Painel de código: 13/14 views prontas (`funcoes_codigo`), com moldura fixa e troca
  fade-out → fade-in (ver `manim-codigo-dinamico`).
- Cena: consumir `coletar()` (compacto, 11 passos) ou `coletar_detalhado()` (1661/1218) —
  a projeção de estado é a mesma e o último estado coincide.
- QA visual: rótulo em todo nó, `f/C` em toda aresta, legenda cobrindo `busca`, `caminho`,
  `aumento`, `valor`, `corte` e `aresta`.

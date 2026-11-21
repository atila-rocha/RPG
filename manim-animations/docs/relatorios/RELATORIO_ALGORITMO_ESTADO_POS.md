# RELATÓRIO ALGORITMO — Estado pós-linha (`estado_pos` / `escrita`)

Fase **ALGORITMO** da obra de Fluxo Máximo (`dataset/tinyFN.txt`). Esta
entrega é **aditiva**: acrescenta ao trace o estado DEPOIS da linha e a aba
que a linha escreve, para a fase visual mostrar a escrita **na própria
linha** — sem alterar `estado`, `pausa`, `destaque`, cenas, `flow_common.py`
ou `algs4-py/`.

## 0. Veredito

| item | estado |
|---|---|
| `src/flow_record.py` | `Step.estado_pos` e `Step.escrita` aditivos (defaults `None`) |
| `validate_flow_scenes.py` | **8/8 grupos ok** (o 8º é o novo `estado pós-linha`) |
| `build/goldens/stages_fluxo.json` | **inalterado** — sha256 `c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a` |
| código antigo | cópia em `src/_snapshot_v3/flow_record_v3.py` |
| cenas / `flow_common.py` / `algs4-py/` | **não tocados** |

## 1. Contrato

`Step` continua `@dataclass(frozen=True)`; os campos antigos não mudaram de
posição nem de conteúdo. Os dois campos novos ficam no fim, com default:

```python
estado_pos: dict | None = None   # estado do painel DEPOIS da linha
escrita: str | None = None       # "edge_to" | "marcados" | "busca" | "adj" | "rede"
```

- `estado` **continua o estado do trace do evento** (o contrato antigo, o
  mesmo que o golden usa). Não foi redefinido.
- `estado_pos` é o **lookahead do próximo `estado`**: em
  `coletar_detalhado`, `passos[i].estado_pos = passos[i+1].estado` (o
  `estado` do passo seguinte, não uma projeção inventada). É `None` no
  **último passo**, que não tem passo seguinte.
- `escrita` é derivada do **AST da fonte real** (`mapa_escritas`, por
  `_no_funcao`/`arquivo_modulo`) e vale `None` em linhas que só leem estado
  (`validate`, `adj`, `other`, `residual_capacity_to`, `in_cut`, `validate`).
- `coletar()` simples é uma subseqüência do detalhado: pode carregar o
  `estado_pos` do detalhado; nada no golden/`stages` depende dele. O teste
  novo do Gate 0 valida o contrato no **modo detalhado**.
- O `stages` **não exporta** `estado_pos` nem `escrita`; por isso o sha
  permanece exatamente `c19ee...`.

## 2. Mapa AST (`mapa_escritas`)

Chave `(módulo, função qualificada, linha) -> (aba, tipo)`. Nenhum número de
linha é digitado: todos vêm do `lineno` do AST. `tipo` é interno do
validador (`reset`/`sub`, `init`/`append`/`popleft`/`dfs`/`return`,
`init`/`insert`/`e`, `value`/`flow`/`edge`).

### 2.1 Edmonds-Karp (BFS)

| módulo | função | linha | `escrita` | tipo |
|---|---|---|---:|---|
| `ford_fulkerson` | `FordFulkerson.__init__` | 38 | `marcados` | reset |
| `ford_fulkerson` | `FordFulkerson.__init__` | 39 | `edge_to` | reset |
| `ford_fulkerson` | `FordFulkerson.__init__` | 40 | `rede` | value |
| `ford_fulkerson` | `FordFulkerson.__init__` | 45 | `rede` | value |
| `ford_fulkerson` | `FordFulkerson.__init__` | 61 | `rede` | value (`+= bottle`) |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 75 | `edge_to` | reset |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 76 | `marcados` | reset |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 79 | `busca` | init (`queue = deque()`) |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 80 | `busca` | append (`s`) |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 81 | `marcados` | sub (`s`) |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 83 | `busca` | popleft |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 90 | `edge_to` | sub (`w`) |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 91 | `marcados` | sub (`w`) |
| `ford_fulkerson` | `FordFulkerson.has_augmenting_path` | 92 | `busca` | append (`w`) |

### 2.2 Ford-Fulkerson (DFS)

| módulo | função | linha | `escrita` | tipo |
|---|---|---|---:|---|
| `ford_fulkerson_dfs` | `FordFulkersonDFS.__init__` | 39 | `marcados` | reset |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.__init__` | 40 | `edge_to` | reset |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.__init__` | 41 | `rede` | value |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.__init__` | 46 | `rede` | value |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.__init__` | 62 | `rede` | value (`+= bottle`) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.has_augmenting_path` | 76 | `edge_to` | reset |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.has_augmenting_path` | 77 | `marcados` | reset |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.has_augmenting_path` | 80 | `marcados` | sub (`s`) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.has_augmenting_path` | 81 | `busca` | dfs (`s`, empilha) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.dfs` | 88 | `busca` | return (pop) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.dfs` | 95 | `edge_to` | sub (`w`) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.dfs` | 96 | `marcados` | sub (`w`) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.dfs` | 97 | `busca` | dfs (`w`, empilha) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.dfs` | 98 | `busca` | return (pop) |
| `ford_fulkerson_dfs` | `FordFulkersonDFS.dfs` | 99 | `busca` | return (pop) |

### 2.3 Estruturas (`flow_network` / `flow_edge`)

| módulo | função | linha | `escrita` | tipo | executa no `tinyFN`? |
|---|---|---|---:|---|---|
| `flow_network` | `FlowNetwork.__init__` | 129 | `adj` | init (`_adj`) | sim |
| `flow_network` | `FlowNetwork.__init__` | 137 | `adj` | init (`_adj`) | **não** (ramo aleatório) |
| `flow_network` | `FlowNetwork.add_edge` | 156 | `adj` | insert no início | sim |
| `flow_network` | `FlowNetwork.add_edge` | 157 | `adj` | insert no início | sim |
| `flow_network` | `FlowNetwork.add_edge` | 158 | `adj` | `E += 1` | sim |
| `flow_edge` | `FlowEdge.add_residual_flow_to` | 76 | `rede` | flow `-=` | **não** neste trace |
| `flow_edge` | `FlowEdge.add_residual_flow_to` | 78 | `rede` | flow `+=` | sim |
| `flow_edge` | `FlowEdge.add_residual_flow_to` | 83 | `rede` | flow `= 0.0` | **não** neste trace |
| `flow_edge` | `FlowEdge.add_residual_flow_to` | 85 | `rede` | flow `= capacity` | sim |
| `flow_edge` | `FlowEdge.__init__` | 29–32, 45–48 | `rede` | edge | **não** (sem view no painel) |

Não escrevem (ficam `None`): `FlowNetwork.validate_vertex`,
`FlowNetwork.adj`, `FlowEdge.other`, `FlowEdge.residual_capacity_to`,
`FordFulkerson.in_cut` e `FordFulkerson.validate`
(assim como os `return`s de `has_augmenting_path` e `check`).

### 2.4 Ordem real do BFS (90 → 91 → 92)

A ordem **não** foi reordenada para o exemplo do pedido: é a do fonte. O
`estado` (pós-linha) prova a seqüência no mesmo `w = 2` da 1ª busca:

| linha | comando | `estado` pós-linha | `estado_pos` (próximo passo) |
|---:|---|---|---|
| 90 | `self.edgeTo[w] = e` | `edge_to={2:(0,2)}`, `marcados=[0]`, `fila=[]` | `= estado` da linha 91 |
| 91 | `self.marked[w] = True` | `edge_to={2:(0,2)}`, `marcados=[0,2]`, `fila=[]` | `= estado` da linha 92 |
| 92 | `queue.append(w)` | `edge_to={2:(0,2)}`, `marcados=[0,2]`, `fila=[2]` | `= estado` do `while` (82) |

## 3. Números medidos

| medida | BFS (`edmonds_karp`) | DFS (`ford_fulkerson_dfs`) |
|---|---:|---:|
| passos detalhados | **1510** | **1281** |
| passos compactos (golden) | **11** | **11** |
| passos com `escrita` | **153** | **135** |
| linhas no `mapa_escritas` | **31** | **32** |
| linhas mapeadas executadas | **20** | **21** |
| `estado_pos` == `estado` do passo seguinte | **ok** (todos os passos com escrita, exceto o último) | **ok** |
| último passo | `FordFulkerson.check:157` | `FordFulkersonDFS.check:160` |
| `estado_pos` do último passo | `None` | `None` |
| Gate 0 | **8/8** | **8/8** |

Linhas executadas por estrutura (`escrita`):

| estrutura | BFS | DFS |
|---|---|---:|
| `edge_to` | 3 (`39, 75, 90`) | 3 (`40, 76, 95`) |
| `marcados` | 4 (`38, 76, 81, 91`) | 4 (`39, 77, 80, 96`) |
| `busca` | 4 (`79, 80, 83, 92`) | 5 (`81, 88, 97, 98, 99`) |
| `adj` | 4 (`129, 156, 157, 158`) | 4 (`129, 156, 157, 158`) |
| `rede` | 5 (`40, 45, 61` + `flow_edge:78, 85`) | 5 (`41, 46, 62` + `flow_edge:78, 85`) |

O teste novo (`testar_estado_pos`) verifica, para **todo** passo do modo
detalhado:

1. `passo.escrita` é igual ao valor de `mapa_escritas` **e** à classificação
   independente feita só com o AST naquele `(módulo, função, linha)`;
2. `passo.estado_pos == coletar_detalhado()[i+1].estado` (ou `None` no
   último);
3. o efeito está no estado: `edge_to[w]`, `marcados[w]`, `fila`/`pilha` com
   `w`, `adj` com a aresta, `fluxos`/`valor` com o fluxo;
4. o sha do `stages` continua `c19ee...` (o teste monta o texto e compara o
   sha; o arquivo só é gravado no fim, se todos os grupos passarem).

Comando executado (sem Manim):

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe validate_flow_scenes.py
# ok entrada .txt ... ok estado pós-linha (8/8)
# sha256 do stages: c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a
```

## 4. Limites e exceções (ditos explicitamente)

- **Último passo**: `estado_pos=None` por contrato (BFS `check:157`, DFS
  `check:160`). Não há "próximo evento".
- **`FlowEdge.__init__`**: as linhas 29–32/45–48 foram classificadas como
  `rede` no AST, mas a função **não tem view** em `FUNCOES_PAINEL` e nunca
  vira `Step`; portanto nenhum `Step.escrita` é emitido para elas. O efeito
  (capacidade/fluxo iniciais) existe em `estado["capacidades"]`/`fluxos`,
  mas fora do painel de código.
- **`FlowNetwork.__init__:137`**: init de `_adj` do ramo aleatório; não é
  executado quando a rede vem do arquivo. Está no mapa, sem passo.
- **`FlowEdge.add_residual_flow_to:76/83`**: mapeados, mas não executados
  no `tinyFN` (o trace só usa o sentido direto e não cai no arredondamento
  para zero). Os executados `78` e `85` foram validados.
- **Resets imediatamente sobrescritos**: no DFS, `self.marked = [False] * g.V`
  (77) é seguido de `self.marked[s] = True` (80); no BFS, `queue = deque()`
  (79) é seguido de `queue.append(s)` (80). O efeito do reset aparece no
  **`estado` pós-linha do próprio passo** — o `estado_pos` é o estado do
  passo seguinte, que já contém a escrita seguinte. O teste confere o reset
  em `estado` e a igualdade `estado_pos == próximo estado` separadamente.
- **`add_edge:158` (`self.E += 1`)**: o próximo evento já é do chamador e o
  `e` saiu do frame; o teste confere a aresta em `adj` usando o `e` do passo
  anterior (`insert`), que é o mesmo objeto. O `estado_pos` está preenchido.

## 5. Invariantes e pontos de destaque para a fase visual

- `estado`, `pausa` e `destaque` intactos: os 7 grupos antigos continuam
  verdes e o golden compacto (11 assinaturas) não mudou.
- `stages_fluxo.json` byte a byte igual (sha `c19ee...`); o QA de vídeo e o
  validador de layout podem continuar comparando por índice de passo.
- A fase visual pode escolher a aba por `passo.escrita` e animar a ação da
  linha com `passo.estado_pos`, sem esperar o próximo passo:
  - BFS: `edge_to` em 90, `marcados` em 91, `busca` (fila) em 92;
  - DFS: `edge_to` em 95, `marcados` em 96, `busca` (pilha) em 97;
  - `rede`: `flow` em 78/85 e `value` em 61/62 (BFS/DFS);
  - `adj`: 156/157/158 (e a init em 129).
- Determinismo preservado: o trace é o mesmo em duas gravações; a
  comparação continua por índice de passo, nunca por timestamp.
- Nenhum arquivo de cena, `flow_common.py` ou `algs4-py/` foi editado nesta
  fase; o código anterior do gravador está em
  `src/_snapshot_v3/flow_record_v3.py`.

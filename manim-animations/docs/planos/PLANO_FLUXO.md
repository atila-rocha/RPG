# Plano de produção — Fluxo Máximo (Ford-Fulkerson e Edmonds-Karp)

Status: **V4 480p APROVADA NO QA** (21/11/2026). Contrato visual: `PLANO_VISUAL_FLUXO_V4.md`
(revisão 4.1). Gate 0 verde (**8/8**; `stages` sha `c19ee524…7a3a`), portão de layout verde
(**277 verificações**, 0 falhas) e QA de vídeo **APROVADO**
(`docs/relatorios/QA_V4_480P.md`). 1080p60 segue **bloqueado** até aval explícito do usuário.

| cena | duração | alvo | frames | tamanho | status |
|---|---|---|---|---|---|
| `EdmondsKarpExecutionScene_new` (BFS) | **17,01 min** (1020,732 s) | 1020,6 s | 15 311 | 119,80 MB | APROVADO |
| `FordFulkersonExecutionScene_new` (DFS) | **14,52 min** (871,065 s) | 871,0 s | 13 066 | 100,20 MB | APROVADO |

Contrato visual vigente: `PLANO_VISUAL_FLUXO_V4.md` (V3 e V2 ficam como histórico).
O `exit=1` do DFS é o falso negativo conhecido do `modify_atime` do Manim **depois** do
`File ready`; o MP4 foi gravado e validado por decodificação (13 066 frames, 14,52 min).
Renders preservados: baseline V3 em `build/media-fluxo-v2/`, V4 em `build/media-fluxo-v4/`,
draft defeituoso 4.1 em `build/_draft_v41/`; código em `src/_snapshot_v3/` e `src/_snapshot_v4/`.
Orquestrador: sessão atual.
Log de render: `build/logs/render_fluxo_480_v4.log` · script: `render_fluxo_480_v4.ps1` ·
QA de vídeo: `build/logs/qa_flow_videos_v42.log`.

### O que mudou na V4 (feedback do usuário de 19/11)

| sintoma | causa | correção |
|---|---|---|
| `caminho`/`gargalo` colidiam com o 6º chip da `edgeTo` em 04:51 | bloco `caminho`+`b` em `X_INFO=X0+5,14`, sobre a fila | bloco **sempre abaixo da fila** (`X_INFO=X0=-5,00`, `Y_CAMINHO=-2,74`, `Y_GARGALO=-2,96`); 0 colisões em 146/141 passos |
| estruturas `edgeTo`/`marked` apareciam só como texto na aba `busca` | `aba_do_passo` mandava toda `has_augmenting_path` para `busca` | a aba é a **estrutura escrita pela linha** (`Step.escrita` derivado do AST); `fundir_runs` não funde run de 1 passo com escrita |
| adição do vértice não era vista na estrutura | conteúdo da aba vinha do estado antes da linha | conteúdo pós-linha (`Step.estado_pos`) + `Flash`/`Indicate` no elemento novo (70/55 adições; 12/12 resets só com fade) |
| troca de aba ficava ~1 s parada | `_estilo_abas` usava `_MethodAnimation` com `run_time` default 1,0 s | `animate(run_time=RITMO["fade"])` (0,1333 s) — devolveu 85,8 s (EK) e 64,1 s (DFS) |
| aba `busca` repetia `edgeTo`/`marcados` | texto duplicado na aba de fila/pilha | removidos; a aba mostra só chips, setas, `frente`/`fim` (BFS) ou `base`/`topo` (DFS) e `inspeções n` |

Ordem real que a animação segue: BFS `edgeTo` 90 → `marked` 91 → `fila` 92; DFS `edgeTo` 95 →
`marked` 96 → `dfs` 97. Trocas de aba: **99 (EK) / 74 (DFS)**, sem fantasma.

### Correções da V2 (bug de fantasma na troca de aba)

| sintoma | causa | correção |
|---|---|---|
| caption da aba anterior escrita por cima da nova | `sincronizar` recriava a caption, mas `todos()` devolvia o objeto antigo via `estaticos` | cada aba reporta a caption **viva** em `todos()`; caption fora de `estaticos` |
| rótulos de linha `0..4` da aba `edgeTo` sobreviviam à troca | `construir` montava o rótulo mas não o registrava em `todos()` | rótulo entra em `estaticos` |
| QA de vídeo acusava abas vazias | check 8 media cor de **conteúdo** no corpo (cor ausente em certos trechos, chips com 22 % de opacidade) | check 8 mede o fundo `COR_TAB_ATIVA` no **slot do trilho** (medido: 639–928 px na aba ativa, ≤16 px nas demais) |

### QA formal (13/11) — par 480p

- `qa` emitiu **APROVADO** para as duas cenas (frames reais de 10 trocas de aba no BFS e 6 no DFS).
- Ressalva inicial do `qa`: marcador `▸ continuação` não verificado por amostragem. **Fechada pelo
  orquestrador** com medição dirigida: comprimento da linha de cabeçalho ao longo dos dois vídeos,
  mais leitura do frame:
  - BFS, t≈1061 s → `FordFulkerson.check · ford_fulkerson.py:132–156 · p.2/2 · ▸ continuação da p.1/2`
  - DFS, t≈769 s → `FordFulkersonDFS.check · ford_fulkerson_dfs.py:135–159 · p.2/2 · ▸ continuação da p.1/2`
- Simulação do `CodePanel` sobre o trace: **1 troca adjacente de página por vídeo** (597 trocas de view
  no BFS, 419 no DFS). As demais `p.2/2` são alcançadas **direto** (sem página anterior adjacente) e por
  contrato mostram só `p.k/n` (§ `_rotulo`, "nunca inventamos marcador para uma página que não foi
  alcançada por troca"). Decisão de UX pendente com o usuário.

### O que mudou na V2 (pedido do usuário)

| item | V1 | V2 |
|---|---|---|
| ritmo por linha | 0,18 s de play, pausa 0,06–0,90 | **0,60–1,00 s por passo** (play 0,40 + pausa por tier) |
| fonte do código | 6,76 pt (escala 0,2815) | **11,06 pt** (escala 0,4608) |
| código longo | view única por função | **páginas** (≤23 linhas físicas, quebra em comando, 82 colunas) com `p.k/n · ▸ continuação da p.k-1/n` |
| abas de estrutura | 2 (`rede`, `busca`) | **5** (`rede`, `busca`, `marcados`, `edge_to`, `adj`) em trilho vertical |
| trace | `marcados`, `edge_to`, fila, pilha | + `adj` (Bag real LIFO) e `nivel` (profundidade derivada do edgeTo) |
| duração esperada | 10,6 / 8,0 min | **18,6 / 13,7 min** |

V1 preservado em `media_dev_fluxo/` (hashes em `media_antes/hashes_v1_480p.txt`) e em
`src/_snapshot_v1/`. 1080p continua bloqueado até validação explícita do usuário.

## Entradas

- Guia de estudo (fonte conceitual):
  `D:\atila\Documents\Documentos\obsidian-atila\atila-obsidian\faculdade\grafos\Guia de Estudo Completo Fluxo Máximo em Redes.md`
  (vault: `faculdade/grafos/Guia de Estudo Completo Fluxo Máximo em Redes.md`).
- Dados (fonte única, formato `FlowNetwork`): `dataset/tinyFN.txt`
  - V=6, E=8, arestas `u v capacidade`, origem s=0, sumidouro t=5.
  - override por env `FLUXO_GRAFO` (mesmo padrão de `MST_GRAFO`).
- Código real executado (fonte única da verdade): `algs4-py/algs4/`.

## Fonte canônica do código animado (definida pelo usuário)

Os quatro arquivos abaixo são a **fonte única da verdade** exibida e executada:

- `algs4-py/algs4/flow_edge.py`
- `algs4-py/algs4/flow_network.py`
- `algs4-py/algs4/ford_fulkerson.py`
- `algs4-py/algs4/ford_fulkerson_dfs.py`

O `flow_record.py` importa exatamente esses módulos (`algs4.flow_edge`,
`algs4.flow_network`, `algs4.ford_fulkerson`, `algs4.ford_fulkerson_dfs`) e o
painel de código lê as linhas reais desses mesmos arquivos (`ast` + fatiamento);
verificado em runtime em 12/11/2026 (todas as views apontam para
`C:\Users\atila\Documents\RPG\algs4-py\algs4\*.py`). O `algs4-java` é apenas
referência histórica; nada dele é executado nem exibido.

## Decisão sobre o código-fonte (registro)

O `algs4-java` possui
`FlowEdge.java`, `FlowNetwork.java` e `FordFulkerson.java` (este último usa BFS —
ou seja, já é a variante Edmonds-Karp). Para manter a regra do projeto (“o
código exibido é o código real executado, vindo do algs4-py”):

1. Portar fielmente do Java para `algs4-py/algs4/`:
   - `flow_edge.py` — `FlowEdge` (`from/to/capacity/flow/other/
     residualCapacityTo/addResidualFlowTo`, epsilon 1e-10).
   - `flow_network.py` — `FlowNetwork` (adj com Bag, `add_edge`, `adj`, `edges`,
     leitura de `In`/arquivo).
   - `ford_fulkerson.py` — `FordFulkerson` com `has_augmenting_path` por **BFS**
     (Edmonds-Karp), fiel ao Java.
2. Acrescentar a variante DFS exigida pelo briefing:
   - `ford_fulkerson_dfs.py` — `FordFulkersonDFS`, mesma API pública
     (`value()`, `in_cut()`), `has_augmenting_path` por **DFS** recursiva.
3. A animação **não** reimplementa nada: importa esses módulos e grava o trace
   real (`sys.settrace`), igual a `mst_record.py`/`dijkstra_record.py`.

Se a portabilidade exigir ajuste de nome (snake_case), o painel mostra o
arquivo e as linhas reais do `.py` — nunca uma cópia editada.

## Entregáveis

- `src/flow_record.py` — gravador multi-módulo (Step com `modulo`, estado:
  fluxos por aresta, capacidades residuais, valor, caminho aumentante, gargalo,
  fila BFS / pilha DFS, corte).
- `src/flow_common.py` — `FlowGraphView`, `CodePanel` (uma view por função,
  fade-out → fade-in em dois plays), `EstruturaPanel`, `GuiaVisual`,
  `FlowExecucaoBase` com `play_step` linha a linha.
- `src/edmonds_karp_scene_new.py` — intro + execução Edmonds-Karp (BFS).
- `src/ford_fulkerson_scene_new.py` — intro + execução Ford-Fulkerson (DFS).
- Validadores `validate_flow_scenes.py` / `validate_flow_videos.py`.

## Pipeline

- Render 480p: `render_fluxo_480_v4.ps1` → `build/media-fluxo-v4` (descartável). Baseline V3
  preservada em `build/media-fluxo-v2/`; draft defeituoso 4.1 em `build/_draft_v41/`.
- 1080p60: **bloqueado** até aval explícito do usuário.
- Entrega 480p: `entregas/tinyFN/{cenas,integrais}/`; receita em `entregas/README.md`.
- Preservação de versão: commit/branch do git + `src/_snapshot_v1/`, `_snapshot_v3/`,
  `_snapshot_v4/`. Nunca hash local como mecanismo de preservação.
- Nunca sobrescrever `src/*_new.py`/vídeos existentes de MST/Dijkstra/Fluxo.

## Regras de conteúdo

- Passo a passo **linha a linha**, toda função executada com view própria
  (inclusive `FlowEdge.residual_capacity_to`, `add_residual_flow_to`,
  `FlowNetwork.adj`, `excess`, `is_feasible`, `validate`, `dfs`).
- Painel de estrutura sempre visível: tabela `aresta | capacidade | fluxo |
  residual direta | residual reversa` + `valor do fluxo` + caminho/gargalo +
  fila BFS ou pilha DFS.
- Guia visual fiel: só cores usadas, todo item da legenda presente.
- Fidelidade: valores exibidos vêm do trace; goldens conferem valor final,
  cortes e sequência de caminhos.

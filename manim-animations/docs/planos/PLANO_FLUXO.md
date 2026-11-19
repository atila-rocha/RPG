# Plano de produção — Fluxo Máximo (Ford-Fulkerson e Edmonds-Karp)

Status: **V2 480p RENDERIZADA E VALIDADA** (13/11 00:20). Gate 0 verde (6/6; `stages` sha
`4428184b…4d3d`), portão de layout verde (168 verificações) e QA de vídeo **APROVADO nos
dois MP4** (`validate_v2_480.log`, `validate_v2_480_ford.log`). 1080p60 segue **bloqueado**
até aval explícito do usuário.

| cena | duração | alvo | frames | SHA-256 | status |
|---|---|---|---|---|---|
| `EdmondsKarpExecutionScene_new` (BFS) | **18,89 min** (101 %) | 18,70 | 16 999 | `94F24D94…B9B543` | APROVADO |
| `FordFulkersonExecutionScene_new` (DFS) | **14,01 min** (101 %) | 13,80 | 12 605 | `71A49587…9B59B6E` | APROVADO |

Contrato visual vigente: `PLANO_VISUAL_FLUXO_V2.md` (fontes, paginação, 5 abas, ritmo).
Renders 480p antigos (pré-correção) preservados em `media_dev_fluxo_v2_pre_ghostfix/`,
hashes em `media_antes/hashes_v2_obsoletos.txt`; hashes dos finais em
`media_antes/hashes_v2_finais_480p.txt`.
Orquestrador: sessão atual.
Log de render: `render_fluxo_480_v2.log` · script: `render_fluxo_480_v2.ps1`.

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

- Media de desenvolvimento: `media_dev_fluxo/` (480p15).
- Media final: `media_1080_fluxo/` (1080p60), só após validação do usuário.
- Snapshot de hashes dos vídeos antigos antes de qualquer render.
- Nunca sobrescrever `src/*_new.py`/vídeos existentes de MST/Dijkstra.

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

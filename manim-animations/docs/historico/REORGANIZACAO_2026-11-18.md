# Reorganização de 18/11/2026

Registro do que foi movido, do que foi descartado de propósito e de como reverter.
Todos os movimentos estão listados em `build/_arquivo/MANIFESTO_MOVES.md`.

## Contexto

O repositório tinha 29.301 arquivos / 8,07 GB, sendo 27.669 / 4,92 GB em `manim-animations/`,
100% fora do git. O `.git` ocupava 2,89 GB, dos quais 2,70 GB eram objetos soltos não alcançáveis.

## O que foi feito

| etapa | resultado |
|---|---|
| `git fsck` como retrato em `build/_fsck_antes.txt` | registro do que existia |
| backup de texto (`src`, `scripts`, configs) em `build/_backup_2026-11-18.zip` | 126 arquivos, 0,35 MB |
| expiração de reflog + `git prune --expire=now` | `.git` de 2,82 GB para 132 MB |
| entrega congelada em `entregas/tinyEWG/` | 7 mp4 1080p60, 1,21 GB, SHA-256 conferido na cópia |
| `.md` para `docs/{planos,relatorios,historico}` | 14 arquivos |
| `.log` para `build/logs/` | 47 arquivos, 82 MB |
| 75 scripts de diagnóstico para `build/_arquivo/experimentos/` | fora de `src/` |
| 40 diretórios `media_*` / `qa_*` para `build/_arquivo/renders/` | 4,57 GB |
| `media/` e `media_dev/` da raiz para `build/_arquivo/raiz/` | 29 MB |
| `.ps1` mantidos na raiz, caminho absoluto trocado por `$PSScriptRoot` | 7 scripts |
| `git prune` + commits iniciais | código das animações versionado pela primeira vez |

## O que foi descartado de propósito

O `reset --hard` de 16/11/2026 abandonou uma linhagem de 15 commits (23/10 a 16/11) que existia
**apenas no reflog**, incluindo `d791a99` ("entrega final 1080p60 dos dois grafos"). Esses commits
carregavam 2,81 GB de blobs de vídeo, todos byte-idênticos aos arquivos em disco — nenhum conteúdo
exclusivo. Por decisão do autor, a linhagem foi descartada em vez de resgatada.

Consequência: a linha do tempo das animações não tem mais histórico anterior a esta reorganização.
O estado a partir daqui é o primeiro commit versionado de `src/`, `docs/` e `entregas/README.md`.

## Como reverter

- Qualquer diretório de render: `move build\_arquivo\renders\<nome>` de volta para `manim-animations\`.
- Experimentos: `move build\_arquivo\experimentos\*` de volta para `manim-animations\src\`.
  48 deles importam `mst_common`/`flow_common`/`dijkstra_common`, então só funcionam dentro de `src/`.
- `.ps1` originais (com caminho absoluto): `build\_arquivo\ps1_antes\`.
- O histórico git descartado **não** é reversível.

## Padronização das fases (mesmo dia)

Depois da reorganização, o contrato de caminhos foi fechado em `manim-animations/README.md`
§ "Convenções de caminhos" e propagado para as skills `manim-*` e os subagentes
(`roteiro`, `algoritmo`, `visual`, `codificador`, `qa`, `pipeline`):

| mudança | antes | agora |
|---|---|---|
| render de trabalho | `media_dev/`, `media_corrigido/`, `media_1080*/` na raiz | `build/media/` e `build/media-<stem>/` |
| log de render | raiz de `manim-animations/` | `build/logs/` |
| golden de passos | `media_corrigido/stages*.json` | `build/goldens/stages*.json` |
| `.ps1` | caminho relativo ao CWD (`$py`, `$log`, `--media_dir`) | tudo por `$PSScriptRoot` |
| `MST_GRAFO` relativo | documentado como `..\dataset\...` | `dataset\...` (resolvido da raiz do repo) |
| frame de inspeção | `src/_layout_check.py` (sumira na quarentena) | restaurado em `src/` |

Correções de código que apareceram no caminho:

- `algs4-py/algs4/index_min_pq.py`: `swim`/`sink`/`del_min`/`delete` não atualizavam o índice reverso
  `qp`; a partir do commit `169bb03` (mesmo dia, 17:10), `contains` passou a ler `qp` e o trace do
  Prim Eager estourava `IndexError`. Corrigido mantendo `qp` nas trocas; Prim e Kruskal agora
  concordam (1,81 em tinyEWG, 13,0 em tinyMST6).
- `validate_mst_scenes.py`: `GOLDEN_EAGER` e a ordem de `del_min` estavam registrados com o
  comportamento defeituoso (`insert` duplicado, 5 antes de 3). Foram refeitos a partir do trace
  correto: `7, 1, 2, 3, 5, 4, 6`.
- A trilha de fluxo (`validate_flow_scenes.py`) continua com 2 falhas conhecidas — golden do modo
  compacto e a linha 131 de `FordFulkerson.is_feasible` sem texto declarado — herdadas do trabalho
  de fluxo em andamento, não relacionadas a esta padronização.

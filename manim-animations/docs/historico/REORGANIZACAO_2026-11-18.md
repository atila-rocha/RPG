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

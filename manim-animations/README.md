# manim-animations

Animações dos algoritmos de MST (Kruskal, Prim), fluxo máximo (Edmonds-Karp, Ford-Fulkerson)
e Dijkstra, usadas nas aulas de T290.

## Onde está o quê

| caminho | conteúdo | versionado |
|---|---|---|
| `src/` | código das cenas + módulos comuns (`*_common.py`, `*_record.py`) | sim |
| `docs/planos/` | planos visuais e briefing do codificador | sim |
| `docs/relatorios/` | relatórios das fases (algoritmo, roteiro, codificador) e QA | sim |
| `docs/historico/` | mapas de execução e histórico de reorganização | sim |
| `entregas/` | vídeos 1080p60 finais + receita de regeneração (`README.md`) | só o `README.md` |
| `build/` | render, logs, quarentena — **descartável** | não |
| `*.ps1` (raiz) | scripts de render, um por conjunto de cenas | sim |
| `validate_*.py` (raiz) | validação de cenas e de vídeos | sim |

Regra: **texto e código no git; vídeo, svg de cache, log e `partial_movie_files` nunca.**
`build/` pode ser apagado inteiro a qualquer momento.

## Convenções de caminhos (todas as fases)

Esta tabela é a fonte única: as skills `manim-*` e os subagentes `roteiro`, `algoritmo`,
`visual`, `codificador`, `qa` e `pipeline` escrevem exatamente aqui.

| artefato | destino | versionado |
|---|---|---|
| código da cena + módulos comuns | `src/` | sim |
| versão congelada antes de reescrever | `src/_snapshot_vN/` | sim |
| briefing da entrada (fase roteiro) | `docs/planos/BRIEFING_<TEMA>.md` | sim |
| plano visual (fase visual) | `docs/planos/PLANO_VISUAL_<TEMA>.md` | sim |
| relatório de fase | `docs/relatorios/RELATORIO_<FASE>_<TEMA>.md` | sim |
| veredito do QA | `docs/relatorios/QA_<TEMA>.md` | sim |
| golden de passos (`stages*.json`) | `build/goldens/` | não (regenerável) |
| render de trabalho (480p/1080p) | `build/media/` (entrada padrão) e `build/media-<stem>/` | não |
| log de render e de QA | `build/logs/` | não |
| vídeo final | `entregas/<entrada>/cenas/` e `entregas/<entrada>/integrais/` | não |
| receita, duração e hash da entrega | `entregas/README.md` | sim |

- `build/` é descartável: apagar inteiro não perde nada versionado.
- `entregas/` guarda só o vídeo final, com nome semântico e hash registrado no `README.md`.
- Nenhuma pasta `media_*`, `qa_*` ou `texts/` pode nascer na raiz de `manim-animations/`.
- Vídeo entregue **nunca é sobrescrito**: reentrega vira `-v2` no nome e entra como linha nova na
  tabela de `entregas/README.md`.

## Ambiente

```powershell
uv sync                       # recria .venv a partir de uv.lock
.\.venv\Scripts\python.exe -m manim --version
```

## Entrada de dados

As cenas MST leem um grafo de arquivo `.txt`, no formato `V` / `E` / `v w peso`
(padrão do catálogo `dataset/`, na raiz do repositório). Sem variável de ambiente, usa
`dataset/tinyEWG.txt`. `MST_GRAFO` relativo é resolvido a partir da **raiz do repositório**
(não do diretório atual):

```powershell
# grafo padrão (tinyEWG, 8 vértices / 16 arestas)
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -ql --media_dir build\media

# outro grafo
$env:MST_GRAFO = "dataset\tinyMST6.txt"
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -ql --media_dir build\media-tinyMST6
Remove-Item Env:MST_GRAFO
```

## Cenas

| módulo | cenas |
|---|---|
| `src/kruskal_mst_scene_new.py` | `MSTIntroScene_new`, `KruskalExecutionScene_new` |
| `src/prim_mst_scene_new.py` | `PrimIntroScene_new`, `PrimLazyScene_new`, `PrimEagerScene_new` |
| `src/edmonds_karp_scene_new.py` | `EdmondsKarpIntro_new`, `EdmondsKarpExecutionScene_new`, `FullEdmondsKarpVideo_new` |
| `src/ford_fulkerson_scene_new.py` | `FordFulkersonIntro_new`, `FordFulkersonExecutionScene_new`, `FullFordFulkersonVideo_new` |
| `src/dijkstra_scene_new.py` | `DijkstraExecutionScene_new` |

As intros de fluxo deixam a relação explícita: `EdmondsKarpIntro_new` mostra
`Edmonds-Karp = Ford-Fulkerson + BFS`; `FordFulkersonIntro_new` mostra que a
variante DFS é Ford-Fulkerson puro e **não** aplica Edmonds-Karp.

## Render de entrega

1080p60 em `build/media` (tempo medido: ≈ 3h50 para o conjunto tinyEWG):

```powershell
.\.venv\Scripts\python.exe -m manim render src\prim_mst_scene_new.py PrimLazyScene_new -qh --media_dir build\media --disable_caching
```

Detalhes, durações e comandos por cena: [`entregas/README.md`](entregas/README.md).

## Armadilhas conhecidas

- **Não rode o Manim de fora desta pasta.** Rodar da raiz do repositório cria `media/` e `media_dev/`
  órfãos na raiz (foi o que aconteceu antes da reorganização de 18/11/2026).
- Os módulos de `src/` são importados de forma plana (`from mst_common import ...`), então as cenas
  **precisam** ficar no mesmo diretório dos `*_common.py`. Não separe em subpastas sem ajustar `sys.path`.
- `--media_dir` é relativo à pasta onde o comando é executado; os `.ps1` usam `$PSScriptRoot`,
  mas os comandos digitados à mão não.
- `partial_movie_files/` é o cache de render por partes: apague se o vídeo sair com trechos antigos.

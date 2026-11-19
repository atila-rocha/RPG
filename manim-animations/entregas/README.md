# Entregas — animações de MST

Vídeos **não são versionados** (`*.mp4` está no `.gitignore`). O que fica versionado é este
documento: a receita para regenerá-los a partir de `src/` + `dataset/` + os scripts `.ps1`.

Grafo de referência: **tinyEWG** — 8 vértices, 16 arestas (padrão do projeto; `MST_GRAFO` não definida).
Intérprete: `.venv\Scripts\python.exe` na raiz de `manim-animations/`.
Render vai para `build/media` (descartável); só o vídeo final, renomeado, chega a `entregas/`.

## tinyEWG 1080p60

| arquivo | conteúdo | duração | tamanho |
|---|---|---|---|
| `tinyEWG/integrais/tinyEWG-kruskal-integral-1080p60.mp4` | intro + execução | 1239,1 s | 251,8 MB |
| `tinyEWG/integrais/tinyEWG-prim-integral-1080p60.mp4` | intro + lazy + eager | 1733,7 s | 353,7 MB |
| `tinyEWG/cenas/tinyEWG-kruskal-intro-1080p60.mp4` | `MSTIntroScene_new` | 8,1 s | 0,8 MB |
| `tinyEWG/cenas/tinyEWG-kruskal-execucao-1080p60.mp4` | `KruskalExecutionScene_new` | 1231,0 s | 251,0 MB |
| `tinyEWG/cenas/tinyEWG-prim-intro-1080p60.mp4` | `PrimIntroScene_new` | 7,6 s | 0,8 MB |
| `tinyEWG/cenas/tinyEWG-prim-lazy-1080p60.mp4` | `PrimLazyScene_new` | 1009,2 s | 204,2 MB |
| `tinyEWG/cenas/tinyEWG-prim-eager-1080p60.mp4` | `PrimEagerScene_new` | 716,9 s | 148,7 MB |

Os integrais são a concatenação exata das cenas (soma das durações confere).

## Como regenerar

```powershell
# 480p15 (QA local, minutos)
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -ql --media_dir build\media

# 1080p60 (entrega)
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -qh --media_dir build\media --disable_caching
.\.venv\Scripts\python.exe -m manim render src\prim_mst_scene_new.py   PrimLazyScene_new        -qh --media_dir build\media --disable_caching
.\.venv\Scripts\python.exe -m manim render src\prim_mst_scene_new.py   PrimEagerScene_new       -qh --media_dir build\media --disable_caching
```

Tempo medido de render 1080p60 (`render_1080p.log`, 16/11/2026):

| cena | tempo |
|---|---|
| `MSTIntroScene_new` | 32,1 s |
| `KruskalExecutionScene_new` | 5535,9 s (~1h32) |
| `PrimIntroScene_new` | 28,4 s |
| `PrimLazyScene_new` | 5110,0 s (~1h25) |
| `PrimEagerScene_new` | 3062,9 s (~51 min) |
| **total** | **≈ 3h50** |

Os integrais saem de `_concat_mp4.py` sobre as cenas renderizadas.

## Grafo antigo (tinyMST6) — arquivado

A entrega atual usa tinyEWG. O conjunto tinyMST6 (6 vértices, custo 13) foi movido para
`build/_arquivo/` e continua reproduzível:

```powershell
$env:MST_GRAFO = "dataset\tinyMST6.txt"   # relativo à raiz do repositório
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -qh --media_dir build\media-tinyMST6
```

Tempo medido do conjunto tinyMST6: ≈ 1h14 (1795 + 1437 + 1174 s).

## Regeração pelos `.ps1`

`render_1080p.ps1`, `render_1080p_resto.ps1`, `render_correcoes.ps1` e `render_dois_grafos.ps1`
continuam na raiz de `manim-animations/`, um por conjunto de cenas, e usam `$PSScriptRoot` em tudo
(python, cenas, `--media_dir` e logs) — funcionam de qualquer diretório. Gravam em `build\media`
(entrada padrão), `build\media-tinyMST6` (segunda entrada) e `build\logs\`. Nenhuma pasta
`media_*` nasce mais na raiz.

## Levar para a entrega

1. Render final em `build\media` (1080p60).
2. Conferir SHA-256 e duração do mp4.
3. Copiar com nome semântico para `entregas\<entrada>\cenas\` (ou `integrais\`, via `_concat_mp4.py`).
4. Registrar a linha nova (arquivo, duração, tamanho, hash) na tabela acima.

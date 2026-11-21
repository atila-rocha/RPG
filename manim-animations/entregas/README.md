# Entregas — animações de MST e Fluxo Máximo

Vídeos **não são versionados** (`*.mp4` está no `.gitignore`). O que fica versionado é este
documento: a receita para regenerá-los a partir de `src/` + `dataset/` + os scripts `.ps1`.

Grafos de referência:

- **MST → tinyEWG** — 8 vértices, 16 arestas (padrão do projeto; `MST_GRAFO` não definida).
- **Fluxo máximo → tinyFN** — `dataset/tinyFN.txt`, V=6, E=8, arestas `u v capacidade`,
  origem s=0, sumidouro t=5 (override por `FLUXO_GRAFO`).

Intérprete: `.venv\Scripts\python.exe` na raiz de `manim-animations/`.
Render vai para `build/media*` (descartável); só o vídeo final, renomeado, chega a `entregas/`.

Preservação de versão é por **commit/branch do git** (mais os snapshots de código em
`src/_snapshot_vN/`); **não** se registra hash local de mp4.

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

## tinyFN 480p15 (V4, rev. 4.1)

Aprovado no QA em 21/11/2026 (`docs/relatorios/QA_V4_480P.md`). Contrato visual:
`docs/planos/PLANO_VISUAL_FLUXO_V4.md`. Gate 0 8/8 (sha do `stages` `c19ee524…7a3a`) e portão
de layout com 277 verificações, 0 falhas.

| arquivo | conteúdo | duração | frames | tamanho |
|---|---|---|---|---|
| `tinyFN/integrais/tinyFN-edmonds-karp-integral-480p15.mp4` | intro + execução (BFS) | 1038,864 s | 15.583 | 120,26 MB |
| `tinyFN/integrais/tinyFN-ford-fulkerson-dfs-integral-480p15.mp4` | intro + execução (DFS) | 889,197 s | 13.338 | 100,65 MB |
| `tinyFN/cenas/tinyFN-edmonds-karp-intro-480p15.mp4` | `EdmondsKarpIntro_new` | 18,132 s | 272 | 0,42 MB |
| `tinyFN/cenas/tinyFN-edmonds-karp-execucao-480p15.mp4` | `EdmondsKarpExecutionScene_new` | 1020,732 s | 15.311 | 119,80 MB |
| `tinyFN/cenas/tinyFN-ford-fulkerson-dfs-intro-480p15.mp4` | `FordFulkersonIntro_new` | 18,132 s | 272 | 0,42 MB |
| `tinyFN/cenas/tinyFN-ford-fulkerson-dfs-execucao-480p15.mp4` | `FordFulkersonExecutionScene_new` | 871,065 s | 13.066 | 100,20 MB |

Os integrais são remux sem re-encode (`_concat_mp4.py`) e fecham **ao frame**:
272 + 15.311 = 15.583 e 272 + 13.066 = 13.338. A fronteira intro→execução foi conferida
pixel a pixel (`diff_medio = 0.000000` nos frames 271 e 272).

**1080p60 do fluxo** foi autorizado pelo usuário em 21/11/2026, renderizado
(`render_fluxo_1080.ps1` → `build\media-fluxo-1080`) em fila serial a partir do código do
commit `d46e0bd` e **aprovado no QA** (`docs/relatorios/QA_V4_1080P.md`); a promoção para
`entregas/` está na seção seguinte. Os achados cosméticos de severidade baixa do QA do 480p
(sobreposição de 1–2 frames nos slots do `StatePanel`, folga `guia`×contadores de ~3 px, caixa
do indicador de código) ficaram registrados para uma passada futura.

## tinyFN 1080p60 (V4, rev. 4.1)

Promovido em 21/11/2026 a partir de `build/media-fluxo-1080/videos/` (código `d46e0bd`,
inalterado desde o Gate 0). Aprovado no QA em 21/11/2026 (`docs/relatorios/QA_V4_1080P.md`).
O 480p acima continua intacto; o 1080p60 entra com sufixo `-1080p60`.

| arquivo | conteúdo | duração | frames | tamanho |
|---|---|---|---|---|
| `tinyFN/integrais/tinyFN-edmonds-karp-integral-1080p60.mp4` | intro + execução (BFS) | 1035,162 s | 62.131 | 343,15 MB |
| `tinyFN/integrais/tinyFN-ford-fulkerson-dfs-integral-1080p60.mp4` | intro + execução (DFS) | 885,898 s | 53.172 | 285,05 MB |
| `tinyFN/cenas/tinyFN-edmonds-karp-intro-1080p60.mp4` | `EdmondsKarpIntro_new` | 17,900 s | 1.074 | 1,22 MB |
| `tinyFN/cenas/tinyFN-edmonds-karp-execucao-1080p60.mp4` | `EdmondsKarpExecutionScene_new` | 1017,262 s | 61.057 | 341,74 MB |
| `tinyFN/cenas/tinyFN-ford-fulkerson-dfs-intro-1080p60.mp4` | `FordFulkersonIntro_new` | 17,900 s | 1.074 | 1,23 MB |
| `tinyFN/cenas/tinyFN-ford-fulkerson-dfs-execucao-1080p60.mp4` | `FordFulkersonExecutionScene_new` | 867,998 s | 52.098 | 283,64 MB |

Todos 1920×1080, h264 High/yuv420p, ~60 fps (média real 60,021 nas execuções), decodificados
integralmente na verificação pós-entrega (PyAV), com último frame não-preto. Os integrais são
remux sem re-encode (`_concat_mp4.py`, intro → execução) e fecham **ao frame**:
1.074 + 61.057 = 62.131 e 1.074 + 52.098 = 53.172, com as duas junções conferidas pixel a pixel
(`diff_medio = 0.000000` no último frame da intro e no primeiro da execução).

Nota de container: os MP4 de execução saem do render com 1.087 frames de duração de 251 ticks
(1/15360 s = 1/60 s) em vez de 256; por isso a duração de container fica ~0,35 s abaixo de
`frames/60` (EK: 1017,262 s × 61057/60 = 1017,617 s). É característica do arquivo de origem —
os 480p15, com time_base equivalente, fecham exatamente `frames/15` — e não do remux: a
concatenação reproduz os timestamps de origem sem deriva, e a duração do integral é a soma
exata das cenas (17,900 + 1017,262 = 1035,162 s).

## Como regenerar

```powershell
# 480p15 (QA local, minutos)
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -ql --media_dir build\media

# 1080p60 (entrega)
.\.venv\Scripts\python.exe -m manim render src\kruskal_mst_scene_new.py KruskalExecutionScene_new -qh --media_dir build\media --disable_caching
.\.venv\Scripts\python.exe -m manim render src\prim_mst_scene_new.py   PrimLazyScene_new        -qh --media_dir build\media --disable_caching
.\.venv\Scripts\python.exe -m manim render src\prim_mst_scene_new.py   PrimEagerScene_new       -qh --media_dir build\media --disable_caching
```

### Fluxo máximo (480p15)

```powershell
# Gate 0 antes de renderizar
.\.venv\Scripts\python.exe validate_flow_scenes.py     # 8/8 + sha do stages
.\.venv\Scripts\python.exe validate_flow_layout.py    # 277 verificacoes

# Fila serial EK -> DFS (a saida vai para build\media-fluxo-v4)
.\render_fluxo_480_v4.ps1

# ou cena a cena:
.\.venv\Scripts\python.exe -m manim -ql --media_dir build\media-fluxo-v4 src\edmonds_karp_scene_new.py EdmondsKarpExecutionScene_new
.\.venv\Scripts\python.exe -m manim -ql --media_dir build\media-fluxo-v4 src\ford_fulkerson_scene_new.py FordFulkersonExecutionScene_new

# integrais (remux sem re-encode)
.\.venv\Scripts\python.exe _concat_mp4.py entregas\tinyFN\integrais\tinyFN-edmonds-karp-integral-480p15.mp4 entregas\tinyFN\cenas\tinyFN-edmonds-karp-intro-480p15.mp4 entregas\tinyFN\cenas\tinyFN-edmonds-karp-execucao-480p15.mp4
.\.venv\Scripts\python.exe _concat_mp4.py entregas\tinyFN\integrais\tinyFN-ford-fulkerson-dfs-integral-480p15.mp4 entregas\tinyFN\cenas\tinyFN-ford-fulkerson-dfs-intro-480p15.mp4 entregas\tinyFN\cenas\tinyFN-ford-fulkerson-dfs-execucao-480p15.mp4
```

### Fluxo máximo (1080p60)

```powershell
# Fila serial EK -> DFS (a saida vai para build\media-fluxo-1080)
.\render_fluxo_1080.ps1
```

As 4 cenas entram em fila serial: `EdmondsKarpIntro_new`, `EdmondsKarpExecutionScene_new`,
`FordFulkersonIntro_new`, `FordFulkersonExecutionScene_new`. Log em
`build\logs\render_fluxo_1080.log`. Tempo medido (21/11/2026): **5 h 16 m 03 s** de parede no
total — intro EK 62 s, execução EK 2 h 51 m 39 s, intro DFS 51 s, execução DFS 2 h 22 m 24 s.
O custo é dominado por overhead por animação, não por pixels: só ~1,35× o parede do 480p15.

```powershell
# integrais 1080p60 (remux sem re-encode, intro -> execucao)
.\.venv\Scripts\python.exe _concat_mp4.py entregas\tinyFN\integrais\tinyFN-edmonds-karp-integral-1080p60.mp4 entregas\tinyFN\cenas\tinyFN-edmonds-karp-intro-1080p60.mp4 entregas\tinyFN\cenas\tinyFN-edmonds-karp-execucao-1080p60.mp4
.\.venv\Scripts\python.exe _concat_mp4.py entregas\tinyFN\integrais\tinyFN-ford-fulkerson-dfs-integral-1080p60.mp4 entregas\tinyFN\cenas\tinyFN-ford-fulkerson-dfs-intro-1080p60.mp4 entregas\tinyFN\cenas\tinyFN-ford-fulkerson-dfs-execucao-1080p60.mp4
```

Tempo medido do 480p15 (21/11/2026): EK 2h06m48s (15.311 frames) e DFS 1h41m57s (13.066 frames).
O `exit=1` do DFS é o falso negativo conhecido do `modify_atime`, que ocorre **depois** do
`File ready` — valide o mp4 por decodificação, nunca pelo exit code.

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

1. Render na qualidade da entrega em `build\media*` (o 1080p60 só com aval explícito do usuário).
2. Conferir duração, frames e que a versão do código está **commitada** (preservação é por
   git/snapshot, não por hash local).
3. Copiar com nome semântico para `entregas\<entrada>\cenas\` (ou `integrais\`, via `_concat_mp4.py`).
4. Registrar a linha nova (arquivo, duração, frames, tamanho) na tabela acima.
5. Nada de `*.mp4` entra no git: só este README e os scripts são versionados.

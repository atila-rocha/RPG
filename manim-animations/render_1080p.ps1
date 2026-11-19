# Renderiza os dois conjuntos (tinyEWG e tinyMST6) em 1080p60, medindo o tempo
# de cada cena. Uso: .\render_1080p.ps1 (de qualquer diretório)
# Saída: build\media (tinyEWG) e build\media-tinyMST6; logs em build\logs.
$ErrorActionPreference = "Continue"
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$raiz = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $PSScriptRoot 'build\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'render_1080p.log'
if (Test-Path $log) { Remove-Item $log }

function Render($rotulo, $grafo, $media, $arquivo, $cena) {
    if ($grafo) {
        $env:MST_GRAFO = Join-Path $raiz $grafo
    } else {
        Remove-Item Env:MST_GRAFO -ErrorAction SilentlyContinue
    }
    $mediaTag = ($media -split '[\\/]')[-1]
    $inicio = Get-Date
    & $py -m manim render (Join-Path $PSScriptRoot $arquivo) $cena -qh --media_dir (Join-Path $PSScriptRoot $media) --disable_caching 2>&1 |
        Out-File (Join-Path $logDir "${mediaTag}_$cena.log") -Encoding utf8
    $dur = ((Get-Date) - $inicio).TotalSeconds
    $linha = "{0,-10} | {1,-16} | {2,-26} | {3,7:F1} s" -f $rotulo, $media, $cena, $dur
    Add-Content $log $linha
    Write-Output $linha
}

# --- grafo padrão: tinyEWG (8 vértices, 16 arestas) ---
Render "tinyEWG" "" "build\media" "src\kruskal_mst_scene_new.py" "MSTIntroScene_new"
Render "tinyEWG" "" "build\media" "src\kruskal_mst_scene_new.py" "KruskalExecutionScene_new"
Render "tinyEWG" "" "build\media" "src\prim_mst_scene_new.py" "PrimIntroScene_new"
Render "tinyEWG" "" "build\media" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyEWG" "" "build\media" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

# --- grafo anterior: tinyMST6 (6 vértices, 8 arestas, custo 13) ---
Render "tinyMST6" "dataset\tinyMST6.txt" "build\media-tinyMST6" "src\kruskal_mst_scene_new.py" "MSTIntroScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "build\media-tinyMST6" "src\kruskal_mst_scene_new.py" "KruskalExecutionScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "build\media-tinyMST6" "src\prim_mst_scene_new.py" "PrimIntroScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "build\media-tinyMST6" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "build\media-tinyMST6" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

Write-Output "FIM"
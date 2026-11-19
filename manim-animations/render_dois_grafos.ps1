# Renderiza os dois conjuntos (tinyEWG e tinyMST6) em 480p, medindo o tempo
# de cada cena. Uso: .\render_dois_grafos.ps1
$ErrorActionPreference = "Continue"
$py = ".\.venv\Scripts\python.exe"
$raiz = Split-Path $PSScriptRoot -Parent
$log = "render_dois_grafos.log"
if (Test-Path $log) { Remove-Item $log }

function Render($rotulo, $grafo, $media, $arquivo, $cena) {
    if ($grafo) {
        $env:MST_GRAFO = Join-Path $raiz $grafo
    } else {
        Remove-Item Env:MST_GRAFO -ErrorAction SilentlyContinue
    }
    $inicio = Get-Date
    & $py -m manim render $arquivo $cena -ql --media_dir $media --disable_caching 2>&1 |
        Out-File "$media`_$cena.log" -Encoding utf8
    $dur = ((Get-Date) - $inicio).TotalSeconds
    $linha = "{0,-10} | {1,-10} | {2,-26} | {3,7:F1} s" -f $rotulo, $media, $cena, $dur
    Add-Content $log $linha
    Write-Output $linha
}

# --- grafo padrão: tinyEWG (8 vértices, 16 arestas) ---
Render "tinyEWG" "" "media_dev" "src\kruskal_mst_scene_new.py" "MSTIntroScene_new"
Render "tinyEWG" "" "media_dev" "src\kruskal_mst_scene_new.py" "KruskalExecutionScene_new"
Render "tinyEWG" "" "media_dev" "src\prim_mst_scene_new.py" "PrimIntroScene_new"
Render "tinyEWG" "" "media_dev" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyEWG" "" "media_dev" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

# --- grafo anterior: tinyMST6 (6 vértices, 8 arestas, custo 13) ---
Render "tinyMST6" "dataset\tinyMST6.txt" "media_dev_mst6" "src\kruskal_mst_scene_new.py" "MSTIntroScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_dev_mst6" "src\kruskal_mst_scene_new.py" "KruskalExecutionScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_dev_mst6" "src\prim_mst_scene_new.py" "PrimIntroScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_dev_mst6" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_dev_mst6" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

Write-Output "FIM"

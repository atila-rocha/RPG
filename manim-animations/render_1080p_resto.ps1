# Continuacao do render 1080p60: cenas restantes apos timeout.
# tinyEWG: Lazy, Eager. tinyMST6: todas as 5.
$ErrorActionPreference = "Continue"
$py = ".\.venv\Scripts\python.exe"
$raiz = Split-Path $PSScriptRoot -Parent
$log = "render_1080p.log"

function Render($rotulo, $grafo, $media, $arquivo, $cena) {
    if ($grafo) {
        $env:MST_GRAFO = Join-Path $raiz $grafo
    } else {
        Remove-Item Env:MST_GRAFO -ErrorAction SilentlyContinue
    }
    $inicio = Get-Date
    & $py -m manim render $arquivo $cena -qh --media_dir $media --disable_caching 2>&1 |
        Out-File "${media}_$cena.log" -Encoding utf8
    $dur = ((Get-Date) - $inicio).TotalSeconds
    $linha = "{0,-10} | {1,-16} | {2,-26} | {3,7:F1} s" -f $rotulo, $media, $cena, $dur
    Add-Content $log $linha
    Write-Output $linha
}

# --- tinyEWG restantes ---
Render "tinyEWG" "" "media_1080" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyEWG" "" "media_1080" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

# --- tinyMST6 (todas) ---
Render "tinyMST6" "dataset\tinyMST6.txt" "media_1080_mst6" "src\kruskal_mst_scene_new.py" "MSTIntroScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_1080_mst6" "src\kruskal_mst_scene_new.py" "KruskalExecutionScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_1080_mst6" "src\prim_mst_scene_new.py" "PrimIntroScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_1080_mst6" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_1080_mst6" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

Write-Output "FIM"

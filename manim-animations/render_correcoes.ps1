# Re-render das cenas afetadas pelas correções (480p15).
# tinyEWG: Lazy (legenda) e Eager (anotação/marcador do heap).
# tinyMST6: Eager (mesma mudança de anotação/marcador).
$ErrorActionPreference = "Continue"
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$raiz = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $PSScriptRoot 'build\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'render_correcoes.log'
if (Test-Path $log) { Remove-Item $log }

function Render($rotulo, $grafo, $media, $arquivo, $cena) {
    if ($grafo) {
        $env:MST_GRAFO = Join-Path $raiz $grafo
    } else {
        Remove-Item Env:MST_GRAFO -ErrorAction SilentlyContinue
    }
    $mediaTag = ($media -split '[\\/]')[-1]
    $inicio = Get-Date
    & $py -m manim render (Join-Path $PSScriptRoot $arquivo) $cena -ql --media_dir (Join-Path $PSScriptRoot $media) --disable_caching 2>&1 |
        Out-File (Join-Path $logDir "${mediaTag}_$cena.log") -Encoding utf8
    $dur = ((Get-Date) - $inicio).TotalSeconds
    $linha = "{0,-9} | {1,-16} | {2,-26} | {3,7:F1} s" -f $rotulo, $media, $cena, $dur
    Add-Content $log $linha
    Write-Output $linha
}

Render "tinyEWG" "" "build\media" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyEWG" "" "build\media" "src\prim_mst_scene_new.py" "PrimEagerScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "build\media-tinyMST6" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

Write-Output "FIM"

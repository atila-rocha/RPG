# Re-render das cenas afetadas pelas correções (480p15).
# tinyEWG: Lazy (legenda) e Eager (anotação/marcador do heap).
# tinyMST6: Eager (mesma mudança de anotação/marcador).
$ErrorActionPreference = "Continue"
$py = ".\.venv\Scripts\python.exe"
$raiz = Split-Path $PSScriptRoot -Parent
$log = "render_correcoes.log"
if (Test-Path $log) { Remove-Item $log }

function Render($rotulo, $grafo, $media, $arquivo, $cena) {
    if ($grafo) {
        $env:MST_GRAFO = Join-Path $raiz $grafo
    } else {
        Remove-Item Env:MST_GRAFO -ErrorAction SilentlyContinue
    }
    $inicio = Get-Date
    & $py -m manim render $arquivo $cena -ql --media_dir $media --disable_caching 2>&1 |
        Out-File "${media}_$cena.log" -Encoding utf8
    $dur = ((Get-Date) - $inicio).TotalSeconds
    $linha = "{0,-9} | {1,-16} | {2,-26} | {3,7:F1} s" -f $rotulo, $media, $cena, $dur
    Add-Content $log $linha
    Write-Output $linha
}

Render "tinyEWG" "" "media_dev" "src\prim_mst_scene_new.py" "PrimLazyScene_new"
Render "tinyEWG" "" "media_dev" "src\prim_mst_scene_new.py" "PrimEagerScene_new"
Render "tinyMST6" "dataset\tinyMST6.txt" "media_dev_mst6" "src\prim_mst_scene_new.py" "PrimEagerScene_new"

Write-Output "FIM"

# Render 480p serial das cenas de Fluxo Máximo (Edmonds-Karp e Ford-Fulkerson/DFS).
# Saída: build\media-fluxo; log em build\logs\render_fluxo_480.log.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$py = '.\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'build\logs' | Out-Null

$log = 'build\logs\render_fluxo_480.log'
"[$(Get-Date -Format s)] INICIO" | Out-File -FilePath $log -Encoding utf8

$tarefas = @(
    @{ Arquivo = 'src\edmonds_karp_scene_new.py';    Cena = 'EdmondsKarpExecutionScene_new' },
    @{ Arquivo = 'src\ford_fulkerson_scene_new.py';  Cena = 'FordFulkersonExecutionScene_new' },
    @{ Arquivo = 'src\edmonds_karp_scene_new.py';    Cena = 'EdmondsKarpIntro_new' },
    @{ Arquivo = 'src\ford_fulkerson_scene_new.py';  Cena = 'FordFulkersonIntro_new' }
)

foreach ($t in $tarefas) {
    "[$(Get-Date -Format s)] RENDER $($t.Cena)" | Out-File -FilePath $log -Append -Encoding utf8
    & $py -m manim -ql --media_dir build\media-fluxo $t.Arquivo $t.Cena *>> $log
    "[$(Get-Date -Format s)] FIM $($t.Cena) exit=$LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
}

"[$(Get-Date -Format s)] CONCLUIDO" | Out-File -FilePath $log -Append -Encoding utf8

# Render 480p serial das cenas de Fluxo Maximo V2 (fonte maior + paginacao + 5 abas).
# Saída: build\media-fluxo-v2; log em build\logs\render_fluxo_480_v2.log.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$py = '.\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'build\logs' | Out-Null

$log = 'build\logs\render_fluxo_480_v2.log'
"[$(Get-Date -Format s)] INICIO V2" | Out-File -FilePath $log -Encoding utf8

$tarefas = @(
    @{ Arquivo = 'src\edmonds_karp_scene_new.py';   Cena = 'EdmondsKarpExecutionScene_new' },
    @{ Arquivo = 'src\ford_fulkerson_scene_new.py'; Cena = 'FordFulkersonExecutionScene_new' }
)

foreach ($t in $tarefas) {
    "[$(Get-Date -Format s)] RENDER $($t.Cena)" | Out-File -FilePath $log -Append -Encoding utf8
    # Saida do manim: capturada e gravada em UTF-8 puro. `*>>` no PowerShell
    # 5.1 grava UTF-16 e, misturado com os `Out-File -Encoding utf8` dos
    # marcadores, tornava o log ilegivel (os marcadores sumiam no meio do
    # texto). Buffer inteiro em memoria: 17 MB e barato.
    $saida = & $py -m manim -ql --media_dir build\media-fluxo-v2 $t.Arquivo $t.Cena 2>&1
    $exit = $LASTEXITCODE
    $saida | Out-File -FilePath $log -Append -Encoding utf8
    $mp4 = Get-ChildItem "build\media-fluxo-v2\videos\$(([IO.Path]::GetFileNameWithoutExtension($t.Arquivo)))\480p15\$($t.Cena).mp4" -ErrorAction SilentlyContinue
    if ($mp4) {
        "[$(Get-Date -Format s)] FIM $($t.Cena) exit=$exit | $([math]::Round($mp4.Length/1MB,1)) MB" | Out-File -FilePath $log -Append -Encoding utf8
        $sha = (Get-FileHash $mp4.FullName -Algorithm SHA256).Hash
        "[$(Get-Date -Format s)] SHA256 $($t.Cena) $sha" | Out-File -FilePath $log -Append -Encoding utf8
    } else {
        "[$(Get-Date -Format s)] FIM $($t.Cena) exit=$exit | MP4 AUSENTE" | Out-File -FilePath $log -Append -Encoding utf8
    }
}

"[$(Get-Date -Format s)] CONCLUIDO V2" | Out-File -FilePath $log -Append -Encoding utf8

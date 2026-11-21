# Render 1080p60 serial das 4 cenas de Fluxo Maximo V4 (rev. 4.1):
#   2 intros + 2 execucoes (Edmonds-Karp/BFS e Ford-Fulkerson/DFS).
# Saida: build\media-fluxo-1080; log em build\logs\render_fluxo_1080.log.
#
# Derivado de render_fluxo_480_v4.ps1 com duas diferencas:
#   1. Qualidade final: -qh (1920x1080 @ 60 fps) em vez de -ql (480p15).
#   2. Inclui as duas intros, que no 480p ja estavam congeladas em
#      build\media-fluxo-v4 / entregues em entregas\tinyFN.
# Sem SHA256: a preservacao de versao e por git + src\_snapshot_vN.
# O log guarda tamanho, duracao de parede e exit code por cena.
#
# Serial: um render por vez (dois processos Manim colidem no cache media\texts).
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$py = '.\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path 'build\logs' | Out-Null

$media = 'build\media-fluxo-1080'
$log = 'build\logs\render_fluxo_1080.log'
"[$(Get-Date -Format s)] INICIO V4 1080p60 (rev 4.1) | media $media" | Out-File -FilePath $log -Encoding utf8

$tarefas = @(
    @{ Arquivo = 'src\edmonds_karp_scene_new.py';   Cena = 'EdmondsKarpIntro_new';              Alvo = 18.13 },
    @{ Arquivo = 'src\edmonds_karp_scene_new.py';   Cena = 'EdmondsKarpExecutionScene_new';     Alvo = 1013.9 },
    @{ Arquivo = 'src\ford_fulkerson_scene_new.py'; Cena = 'FordFulkersonIntro_new';            Alvo = 18.13 },
    @{ Arquivo = 'src\ford_fulkerson_scene_new.py'; Cena = 'FordFulkersonExecutionScene_new';   Alvo = 864.3 }
)

foreach ($t in $tarefas) {
    "[$(Get-Date -Format s)] RENDER $($t.Cena) | modelo $($t.Alvo) s" | Out-File -FilePath $log -Append -Encoding utf8
    # Saida do manim capturada e gravada em UTF-8 puro (`*>>` no PowerShell 5.1
    # grava UTF-16 e mistura os marcadores).
    $cron = [Diagnostics.Stopwatch]::StartNew()
    $saida = & $py -m manim -qh --media_dir $media $t.Arquivo $t.Cena 2>&1
    $exit = $LASTEXITCODE
    $cron.Stop()
    $parede = [math]::Round($cron.Elapsed.TotalSeconds, 1)
    $saida | Out-File -FilePath $log -Append -Encoding utf8
    $mp4 = Get-ChildItem "$media\videos\$(([IO.Path]::GetFileNameWithoutExtension($t.Arquivo)))\1080p60\$($t.Cena).mp4" -ErrorAction SilentlyContinue
    if ($mp4) {
        "[$(Get-Date -Format s)] FIM $($t.Cena) exit=$exit | $([math]::Round($mp4.Length/1MB,2)) MB | parede $parede s | $($mp4.FullName)" | Out-File -FilePath $log -Append -Encoding utf8
    } else {
        "[$(Get-Date -Format s)] FIM $($t.Cena) exit=$exit | MP4 AUSENTE | parede $parede s" | Out-File -FilePath $log -Append -Encoding utf8
    }
}

"[$(Get-Date -Format s)] CONCLUIDO V4 1080p60" | Out-File -FilePath $log -Append -Encoding utf8

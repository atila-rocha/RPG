$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
$py = '.\.venv\Scripts\python.exe'

# fila SERIAL: um render por vez (CPU-bound)
$scenes = @(
  @('src\edmonds_karp_scene_new.py',  'EdmondsKarpExecutionScene_new',  'edmonds_karp_scene_new',  '_render_ek_exec.log'),
  @('src\ford_fulkerson_scene_new.py','FordFulkersonExecutionScene_new','ford_fulkerson_scene_new','_render_ff_exec.log'),
  @('src\edmonds_karp_scene_new.py',  'EdmondsKarpIntro_new',           'edmonds_karp_scene_new',  '_render_ek_intro.log'),
  @('src\ford_fulkerson_scene_new.py','FordFulkersonIntro_new',         'ford_fulkerson_scene_new','_render_ff_intro.log')
)

"inicio`t$(Get-Date -Format o)" | Set-Content _render_fluxo_summary.txt -Encoding utf8

foreach ($s in $scenes) {
  $t0 = Get-Date
  & $py -m manim -ql --media_dir media_dev_fluxo $s[0] $s[1] *>&1 | Out-File -FilePath $s[3] -Encoding utf8
  $code = $LASTEXITCODE
  $t1 = Get-Date
  $mp4 = "media_dev_fluxo\videos\$($s[2])\480p15\$($s[1]).mp4"
  if (Test-Path $mp4) {
    $f = Get-Item $mp4
    $line = "$($s[1])`tOK`texit=$code`t$([int]($t1-$t0).TotalMinutes)min`t$($f.Length)`t$($f.LastWriteTime.ToString('o'))`t$mp4"
  } else {
    $line = "$($s[1])`tFALTA_MP4`texit=$code`t$([int]($t1-$t0).TotalMinutes)min"
  }
  Add-Content -Path _render_fluxo_summary.txt -Value $line -Encoding utf8
  Write-Output $line
}
"fim`t$(Get-Date -Format o)" | Add-Content _render_fluxo_summary.txt -Encoding utf8

$ErrorActionPreference = 'Stop'

$workerDirectory = $PSScriptRoot
$repositoryDirectory = Split-Path -Parent (Split-Path -Parent $workerDirectory)
$environmentFile = Join-Path $repositoryDirectory '.env'
$outputDirectory = Join-Path $repositoryDirectory 'benchmarks\studios\hybrid-generation\qualification-smoke-20260914'
$python = Join-Path $workerDirectory '.venv\Scripts\python.exe'

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$tokenLine = Get-Content -LiteralPath $environmentFile |
    Where-Object { $_ -match '^STUDIO_LOCAL_DIFFUSION_TOKEN=' } |
    Select-Object -First 1
if (-not $tokenLine) {
    throw 'STUDIO_LOCAL_DIFFUSION_TOKEN is not configured'
}
$env:RES_LOCAL_DIFFUSION_TOKEN = $tokenLine.Substring($tokenLine.IndexOf('=') + 1).Trim().Trim('"').Trim("'")

$process = Start-Process `
    -FilePath $python `
    -ArgumentList @(
        (Join-Path $workerDirectory 'wait_for_qualification.py'),
        '--output', $outputDirectory,
        '--maximum-wait-seconds', '3600',
        '--poll-seconds', '10',
        '--maximum-samples', '1'
    ) `
    -WorkingDirectory $workerDirectory `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outputDirectory 'watch.stdout.log') `
    -RedirectStandardError (Join-Path $outputDirectory 'watch.stderr.log') `
    -Wait `
    -PassThru

exit $process.ExitCode

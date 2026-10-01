$ErrorActionPreference = 'Stop'

$workerDirectory = $PSScriptRoot
$repositoryDirectory = Split-Path -Parent (Split-Path -Parent $workerDirectory)
$environmentFile = Join-Path $repositoryDirectory '.env'
$runsDirectory = Join-Path $workerDirectory '.runs'
$python = Join-Path $workerDirectory '.venv\Scripts\python.exe'

New-Item -ItemType Directory -Force -Path $runsDirectory | Out-Null

$existingListener = Get-NetTCPConnection -LocalPort 8094 -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    exit 0
}

$tokenLine = Get-Content -LiteralPath $environmentFile |
    Where-Object { $_ -match '^STUDIO_LOCAL_DIFFUSION_TOKEN=' } |
    Select-Object -First 1
if (-not $tokenLine) {
    throw 'STUDIO_LOCAL_DIFFUSION_TOKEN is not configured'
}

$env:RES_LOCAL_DIFFUSION_TOKEN = $tokenLine.Substring($tokenLine.IndexOf('=') + 1).Trim().Trim('"').Trim("'")
Set-Location -LiteralPath $workerDirectory

$process = Start-Process `
    -FilePath $python `
    -ArgumentList @('-m', 'uvicorn', 'api:app', '--host', '127.0.0.1', '--port', '8094') `
    -WorkingDirectory $workerDirectory `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $runsDirectory 'service.stdout.log') `
    -RedirectStandardError (Join-Path $runsDirectory 'service.stderr.log') `
    -Wait `
    -PassThru

exit $process.ExitCode

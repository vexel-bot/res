param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$workerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$preflightRaw = & $Python "$workerRoot\preflight.py" --profile-id animatediff-lightning-sd15-a-v1 --phase install
if ($LASTEXITCODE -ne 0) { throw "local diffusion install preflight failed" }
$preflight = $preflightRaw | ConvertFrom-Json
if ($preflight.status -ne "admitted") { throw "installation resources are not admitted: $($preflight.reasons -join ', ')" }
$preflight | ConvertTo-Json -Depth 8 | Out-Host
$lockTools = Join-Path $workerRoot ".lock-tools"
if (-not (Test-Path -LiteralPath $lockTools)) { & $Python -m venv $lockTools }
if ($LASTEXITCODE -ne 0) { throw "lock tools environment creation failed" }
$lockPython = Join-Path $lockTools "Scripts\python.exe"
& $lockPython -m pip install "pip-tools==7.5.2"
if ($LASTEXITCODE -ne 0) { throw "pip-tools installation failed" }
& $lockPython -m piptools compile "$workerRoot\requirements.in" --generate-hashes --resolver backtracking --output-file "$workerRoot\requirements.generated.lock"
if ($LASTEXITCODE -ne 0) { throw "dependency resolution failed" }
Write-Host "Review requirements.generated.lock and run the CUDA smoke test before marking it qualified."

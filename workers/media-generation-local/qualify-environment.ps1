param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$workerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$generated = Join-Path $workerRoot "requirements.generated.lock"
$environment = Join-Path $workerRoot ".venv"
if (-not (Test-Path -LiteralPath $generated)) { throw "requirements.generated.lock is missing" }
& $Python -m venv $environment
if ($LASTEXITCODE -ne 0) { throw "virtual environment creation failed" }
$workerPython = Join-Path $environment "Scripts\python.exe"
& $workerPython -m pip install --require-hashes -r $generated
if ($LASTEXITCODE -ne 0) { throw "locked dependency installation failed" }
& $workerPython -c "import torch; assert torch.cuda.is_available(); x=torch.ones((64,64),device='cuda',dtype=torch.float16); print(torch.__version__, torch.version.cuda, x.sum().item())"
if ($LASTEXITCODE -ne 0) { throw "CUDA smoke test failed" }
$content = Get-Content -LiteralPath $generated -Raw
Set-Content -LiteralPath (Join-Path $workerRoot "requirements.lock") -Value ("# lockStatus: qualified`r`n" + $content) -Encoding utf8
Write-Host "Qualified. Run worker commands with $workerPython"

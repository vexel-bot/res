param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 18080,
    [switch]$Detach,
    [switch]$AllowNetworkExposure
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$assetRoot = Join-Path $repositoryRoot ".candidate-build\model-assets"
$manifestPath = Join-Path $repositoryRoot "workers\local-evaluation\self-hosted-model-assets.v1.json"
$modelPath = Join-Path $assetRoot "qwen3-4b-q4-k-m\Qwen3-4B-Q4_K_M.gguf"
$runtimeRoot = Join-Path $assetRoot "runtimes\llama.cpp-b10675-vulkan"
$runtimeArchive = Join-Path $runtimeRoot "llama-b10675-bin-win-vulkan-x64.zip"
$runtimeBin = Join-Path $runtimeRoot "bin"
$serverPath = Join-Path $runtimeBin "llama-server.exe"
$logRoot = Join-Path $assetRoot "logs"
$envPath = Join-Path $repositoryRoot ".env"

if ($HostAddress -notin @("127.0.0.1", "localhost", "::1") -and -not $AllowNetworkExposure) {
    throw "Network exposure requires the explicit -AllowNetworkExposure switch and a separate security review."
}

& python (Join-Path $repositoryRoot "backend\scripts\materialize_self_hosted_assets.py") `
    $manifestPath --group qwen3-4b-q4-k-m --output-root $assetRoot
if ($LASTEXITCODE -ne 0) {
    throw "Frozen Qwen assets failed verification."
}

if (-not (Test-Path -LiteralPath $serverPath)) {
    New-Item -ItemType Directory -Path $runtimeBin -Force | Out-Null
    Expand-Archive -LiteralPath $runtimeArchive -DestinationPath $runtimeBin -Force
}

$keyLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^AI_API_KEY=' } | Select-Object -First 1
if (-not $keyLine) {
    throw "AI_API_KEY is missing from .env."
}
$apiKey = ($keyLine -split '=', 2)[1].Trim().Trim('"')
if ($apiKey.Length -lt 32) {
    throw "AI_API_KEY must contain at least 32 characters."
}

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$arguments = @(
    "-m", $modelPath,
    "-a", "clicko-qwen3-4b-q4-k-m",
    "-ngl", "99",
    "-c", "2048",
    "--parallel", "1",
    "--host", $HostAddress,
    "--port", "$Port",
    "--no-webui",
    "--metrics",
    "--reasoning", "off"
)

$env:LLAMA_API_KEY = $apiKey
try {
    if ($Detach) {
        $process = Start-Process -FilePath $serverPath -ArgumentList $arguments `
            -WorkingDirectory $runtimeBin `
            -RedirectStandardOutput (Join-Path $logRoot "qwen-server.out.log") `
            -RedirectStandardError (Join-Path $logRoot "qwen-server.err.log") `
            -WindowStyle Hidden -PassThru
        [pscustomobject]@{
            status = "starting"
            pid = $process.Id
            baseUrl = "http://${HostAddress}:$Port/v1"
            model = "clicko-qwen3-4b-q4-k-m"
            apiKeySource = ".env:AI_API_KEY"
            apiKeyExposed = $false
        } | ConvertTo-Json -Compress
    }
    else {
        & $serverPath @arguments
    }
}
finally {
    Remove-Item Env:LLAMA_API_KEY -ErrorAction SilentlyContinue
}

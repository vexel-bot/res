param(
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Continue'

$repositoryDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repositoryDirectory 'benchmarks\studios\hybrid-generation\qualification-20260914'
}
$statusPath = Join-Path $OutputDirectory 'watch-status.json'
$cleanupLog = Join-Path $OutputDirectory 'host-cleanup.log'
$deadline = (Get-Date).AddMinutes(35)
$applicationNames = @(
    'ChatGPT',
    'chrome',
    'RobloxPlayerBeta',
    'OneDrive',
    'OneDrive.Sync.Service',
    'SystemSettings',
    'SnippingTool',
    'BatteryWidgetHost',
    'SearchHost',
    'TextInputHost'
)

while ((Get-Date) -lt $deadline) {
    $status = $null
    if (Test-Path -LiteralPath $statusPath) {
        try {
            $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
        }
        catch {
            $status = $null
        }
    }
    if ($status -and $status.status -eq 'completed') {
        break
    }

    $closed = @()
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $applicationNames -contains $_.ProcessName } |
        ForEach-Object {
            $closed += "$($_.ProcessName):$($_.Id)"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    $memory = Get-CimInstance Win32_OperatingSystem
    $entry = "$(Get-Date -Format o) freeMiB=$([math]::Round($memory.FreePhysicalMemory / 1024, 0)) closed=$($closed -join ',')"
    Add-Content -LiteralPath $cleanupLog -Value $entry -Encoding UTF8
    Start-Sleep -Seconds 20
}

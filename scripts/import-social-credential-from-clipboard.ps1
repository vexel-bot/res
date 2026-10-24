param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    'META_APP_ID', 'META_APP_SECRET',
    'TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET',
    'LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET',
    'THREADS_APP_ID', 'THREADS_APP_SECRET',
    'PINTEREST_APP_ID', 'PINTEREST_APP_SECRET',
    'X_CLIENT_ID', 'X_CLIENT_SECRET'
  )]
  [string]$Name
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
$value = (Get-Clipboard -Raw).Trim()

if ([string]::IsNullOrWhiteSpace($value)) {
  throw 'A area de transferencia nao contem uma credencial valida.'
}

if ($value -match "[`r`n]") {
  throw 'A credencial deve ocupar uma unica linha.'
}

$lines = [System.Collections.Generic.List[string]]::new()
if (Test-Path -LiteralPath $envPath) {
  foreach ($line in (Get-Content -LiteralPath $envPath)) {
    $lines.Add([string]$line)
  }
}

$replacement = "$Name=$value"
$updated = $false
for ($index = 0; $index -lt $lines.Count; $index += 1) {
  if ($lines[$index] -match "^$([regex]::Escape($Name))=") {
    $lines[$index] = $replacement
    $updated = $true
    break
  }
}

if (-not $updated) {
  $lines.Add($replacement)
}

[System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
Set-Clipboard -Value ' '
Write-Output "Credencial $Name importada com seguranca."

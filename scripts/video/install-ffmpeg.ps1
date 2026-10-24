param([string]$Destination)
$ErrorActionPreference = 'Stop'
$videoRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if (-not $Destination) { $Destination = Join-Path $videoRepo '.codex-runtime/ffmpeg' }
$Destination = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$videoPackage = 'ffmpeg-n9.0.2-28-g669f5ab083-win64-lgpl-shared-9.0.zip'
$videoArchive = Join-Path $Destination $videoPackage
$videoUrl = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-17-20-51/' + $videoPackage
if (-not (Test-Path -LiteralPath $videoArchive)) {
    Invoke-WebRequest -Uri $videoUrl -OutFile $videoArchive
}
$videoDigest = (Get-FileHash -LiteralPath $videoArchive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($videoDigest -ne '00ab3bc8fe02554bd0fffac9968bba498d1ab7e899a4871b85fbba828a50bfcc') {
    throw 'FFMPEG_CHECKSUM_MISMATCH: o pacote não foi extraído.'
}
$videoInstalled = Join-Path $Destination ([IO.Path]::GetFileNameWithoutExtension($videoPackage))
if (-not (Test-Path -LiteralPath $videoInstalled)) { Expand-Archive -LiteralPath $videoArchive -DestinationPath $Destination }
$videoExecutable = Join-Path $videoInstalled 'bin/ffmpeg.exe'
& $videoExecutable -version | Select-Object -First 1
Write-Output 'Pacote LGPL verificado; licença, documentação e DLLs preservadas. Nenhuma variável global foi alterada.'

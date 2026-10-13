$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$toolRoot = Join-Path $workspace '.tools'
$ffmpegRoot = Join-Path $toolRoot 'ffmpeg'
New-Item -ItemType Directory -Force -Path $toolRoot | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $ffmpegRoot 'bin\ffmpeg.exe')) -or
    -not (Test-Path -LiteralPath (Join-Path $ffmpegRoot 'bin\ffprobe.exe'))) {
    $archive = Join-Path $toolRoot 'ffmpeg-release-essentials.zip'
    $unpackRoot = Join-Path $toolRoot 'ffmpeg-download'
    Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $unpackRoot -Force
    $downloaded = Get-ChildItem -LiteralPath $unpackRoot -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'bin\ffmpeg.exe') } |
        Select-Object -First 1
    if (-not $downloaded) { throw 'Downloaded archive does not contain FFmpeg.' }
    New-Item -ItemType Directory -Force -Path $ffmpegRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $downloaded.FullName 'bin') -Destination $ffmpegRoot -Recurse -Force
}
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    $venvPython = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Create the backend virtual environment first with setup.ps1.' }
& $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
& (Join-Path $ffmpegRoot 'bin\ffmpeg.exe') -version
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg verification failed.' }
& (Join-Path $ffmpegRoot 'bin\ffprobe.exe') -version
if ($LASTEXITCODE -ne 0) { throw 'ffprobe verification failed.' }
Write-Output 'MP4/M4A conversion is ready. Restart the backend using this virtual environment.'

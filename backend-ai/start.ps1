$ErrorActionPreference = 'Stop'
$backendPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $backendPython)) {
    $backendPython = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $backendPython)) {
    throw 'Create the backend virtual environment first with setup.ps1.'
}
Push-Location $PSScriptRoot
try {
    & $backendPython -m uvicorn main:app --host 0.0.0.0 --port 8000
    if ($LASTEXITCODE -ne 0) { throw 'Backend failed to start. Check whether port 8000 is already in use.' }
} finally {
    Pop-Location
}

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $candidate = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
        if (Test-Path -LiteralPath $candidate) {
            & $candidate -m venv .venv
        } else {
            py -3.11 -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment. Install Python 3.11+ and retry.' }
    }
    $wheelCache = Join-Path (Split-Path $PSScriptRoot -Parent) '.cache\wheels'
    if (Test-Path -LiteralPath $wheelCache) {
        & $venvPython -m pip install --no-index --find-links $wheelCache -r requirements-dev.txt
    } else {
        & $venvPython -m pip install -r requirements-dev.txt
    }
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check internet access and pip package index settings, then retry.' }
    Write-Output 'Ready. Run: .\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000'
} finally {
    Pop-Location
}

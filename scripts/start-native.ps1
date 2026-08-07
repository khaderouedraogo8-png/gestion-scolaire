# Demarrage dev natif (sans Docker)
# Usage : .\scripts\start-native.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# GTK + PostgreSQL dans le PATH (WeasyPrint, psql)
$extraPaths = @(
    "C:\msys64\mingw64\bin",
    "C:\Program Files\Gtk-Runtime\bin",
    "C:\Program Files\PostgreSQL\17\bin"
)
foreach ($p in $extraPaths) {
    if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) {
        $env:Path = "$p;$env:Path"
    }
}

$venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Lancez d'abord : .\scripts\install-native.ps1" -ForegroundColor Red
    exit 1
}

# Charger .env backend
Get-Content (Join-Path $Root "backend\.env") | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

Write-Host "Demarrage backend Flask :5000 …" -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($Root, $venvPython, $extraPaths)
    foreach ($p in $extraPaths) {
        if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) {
            $env:Path = "$p;$env:Path"
        }
    }
    Set-Location (Join-Path $Root "backend")
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    $env:FLASK_APP = "run.py"
    & $venvPython -m flask run --host 0.0.0.0 --port 5000
} -ArgumentList $Root, $venvPython, $extraPaths

Start-Sleep -Seconds 4

Write-Host "Demarrage frontend Vite :5173 …" -ForegroundColor Cyan
Write-Host ""
Write-Host "  App      : http://localhost:5173" -ForegroundColor Green
Write-Host "  API      : http://localhost:5000/api/health" -ForegroundColor Green
Write-Host "  Ctrl+C pour arreter" -ForegroundColor Yellow
Write-Host ""

try {
    Set-Location (Join-Path $Root "frontend")
    npm run dev
} finally {
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
}

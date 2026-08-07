# Validation mode natif (sans Docker)
# Usage: .\scripts\validate-native.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$passed = 0
$failed = 0

$pgBin = "C:\Program Files\PostgreSQL\17\bin"
$gtkBin = "C:\Program Files\Gtk-Runtime\bin"
foreach ($p in @($pgBin, $gtkBin)) {
    if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) { $env:Path = "$p;$env:Path" }
}

$venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Lancez d'abord : .\scripts\install-native.ps1" -ForegroundColor Red
    exit 1
}

Get-Content (Join-Path $Root "backend\.env") | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

function Step($label, [scriptblock]$action) {
    Write-Host ""
    Write-Host "==> $label" -ForegroundColor Cyan
    try {
        & $action
        Write-Host "[OK] $label" -ForegroundColor Green
        $script:passed++
    } catch {
        Write-Host "[FAIL] $label - $_" -ForegroundColor Red
        $script:failed++
    }
}

Step "PostgreSQL actif" {
    $svc = Get-Service postgresql-x64-17 -ErrorAction SilentlyContinue
    if (-not $svc -or $svc.Status -ne "Running") { throw "Service postgresql-x64-17 absent ou arrêté" }
}

Step "Health API port 5000" {
    $r = Invoke-RestMethod http://localhost:5000/api/health
    if ($r.status -ne "ok") { throw "status not ok" }
}

Step "Login admin" {
    $body = '{"email":"admin@ecole.local","password":"Admin123!"}'
    $r = Invoke-RestMethod -Uri http://localhost:5000/api/login -Method Post -Body $body -ContentType "application/json"
    if (-not $r.access_token) { throw "pas de token" }
}

Step "Pytest integration (natif)" {
    Push-Location (Join-Path $Root "backend")
    & $venvPython -m pytest tests/integration/ -q --tb=no
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
    Pop-Location
}

Step "E2E API 13 modules" {
    Push-Location (Join-Path $Root "backend")
    & $venvPython scripts/e2e_api_validation.py
    if ($LASTEXITCODE -ne 0) { throw "e2e api failed" }
    Pop-Location
}

Step "Tests unitaires frontend" {
    Push-Location (Join-Path $Root "frontend")
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    npm run test -- --run 2>&1 | Write-Host
    $ErrorActionPreference = $prev
    if ($LASTEXITCODE -ne 0) { throw "vitest failed" }
    Pop-Location
}

Step "Generation PDF (WeasyPrint)" {
    $msys = "C:\msys64\mingw64\bin"
    if (-not (Test-Path $msys)) { throw "MSYS2 Pango absent - relancez install-native.ps1" }
    $env:WEASYPRINT_DLL_DIRECTORIES = $msys
    $env:Path = "$msys;$env:Path"
    Push-Location (Join-Path $Root "backend")
    & $venvPython -c "import os,tempfile; from app.services.pdf_render import html_to_pdf; p=os.path.join(tempfile.gettempdir(),'validate.pdf'); html_to_pdf('<html><body><h1>OK</h1></body></html>', p); assert os.path.getsize(p)>500; print('PDF OK')"
    if ($LASTEXITCODE -ne 0) { throw "PDF generation failed" }
    Pop-Location
}

Step "Playwright smoke dev" {
    & "$Root\scripts\reset-admin.ps1" -Target native
    Remove-Item (Join-Path $Root "frontend\e2e\.auth\admin.json") -ErrorAction SilentlyContinue
    Push-Location (Join-Path $Root "frontend")
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    npx playwright test 2>&1 | Write-Host
    $ErrorActionPreference = $prev
    if ($LASTEXITCODE -ne 0) { throw "playwright failed" }
    Pop-Location
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Validation native : $passed OK, $failed FAIL" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
if ($failed -gt 0) { exit 1 }

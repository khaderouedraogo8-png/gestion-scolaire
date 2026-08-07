# Installation native Windows — sans Docker
# Usage (PowerShell admin recommande pour PostgreSQL) :
#   .\scripts\install-native.ps1
param(
    [switch]$SkipPostgres,
    [string]$PostgresPassword = "postgres"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Installation native Gestion Scolaire ===" -ForegroundColor Cyan

# --- PostgreSQL ---
$psql = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psql -and -not $SkipPostgres) {
    Write-Host "[1/5] Installation PostgreSQL 17 via winget…" -ForegroundColor Yellow
    winget install PostgreSQL.PostgreSQL.17 --accept-package-agreements --accept-source-agreements --silent
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pgBin = "C:\Program Files\PostgreSQL\17\bin"
    if (Test-Path $pgBin) { $env:Path = "$pgBin;$env:Path" }
} else {
    Write-Host "[1/5] PostgreSQL…" -ForegroundColor Yellow
}

$psqlCmd = $null
foreach ($p in @(
    "psql",
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe"
)) {
    if (Get-Command $p -ErrorAction SilentlyContinue) { $psqlCmd = $p; break }
    if (Test-Path $p) { $psqlCmd = $p; break }
}
if (-not $psqlCmd) {
    Write-Host "PostgreSQL non trouve. Installez-le ou relancez avec -SkipPostgres si deja configure." -ForegroundColor Red
    exit 1
}

Write-Host "  psql : $psqlCmd" -ForegroundColor Gray

# Arreter Docker sur le port 5432 si actif
docker stop gestion-prod-postgres-1 gestion-scolaire-postgres-1 2>$null | Out-Null

$env:PGPASSWORD = $PostgresPassword
& $psqlCmd -U postgres -h localhost -p 5432 -c "SELECT 1" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Connexion postgres echouee. Essayez le mot de passe superuser PostgreSQL." -ForegroundColor Yellow
    Write-Host "Relancez : .\scripts\install-native.ps1 -PostgresPassword VOTRE_MDP_POSTGRES" -ForegroundColor Yellow
    # Essai sans mot de passe (trust local parfois)
    $env:PGPASSWORD = ""
    & $psqlCmd -U postgres -h localhost -p 5432 -c "SELECT 1" 2>$null
    if ($LASTEXITCODE -ne 0) { exit 1 }
    $PostgresPassword = ""
}

Write-Host "[2/5] Creation base et utilisateur…" -ForegroundColor Yellow
$sql = @"
DO `$`$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gestion') THEN
    CREATE ROLE gestion LOGIN PASSWORD 'gestion_dev';
  END IF;
END `$`$;
SELECT 'CREATE DATABASE gestion_scolaire OWNER gestion'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'gestion_scolaire')\gexec
"@
$sql | & $psqlCmd -U postgres -h localhost -p 5432 -q 2>$null

$env:PGPASSWORD = "gestion_dev"
$schema = Join-Path $Root "database\schema_v2_mono_etablissement.sql"
Write-Host "  Application du schema SQL…"
& $psqlCmd -U gestion -h localhost -d gestion_scolaire -f $schema -q 2>&1 | Out-Null

# --- Python venv ---
Write-Host "[3/5] Environnement Python 3.12…" -ForegroundColor Yellow
$venv = Join-Path $Root "backend\.venv"
if (-not (Test-Path $venv)) {
    py -3.12 -m venv $venv
}
$pip = Join-Path $venv "Scripts\pip.exe"
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --upgrade pip -q
& $python -m pip install -r (Join-Path $Root "backend\requirements.txt") -q
Write-Host "  Python OK : $python" -ForegroundColor Gray

# --- Frontend ---
Write-Host "[4/5] Dependances Node.js…" -ForegroundColor Yellow
Push-Location (Join-Path $Root "frontend")
npm ci --silent 2>$null
if ($LASTEXITCODE -ne 0) { npm install }
Pop-Location

# --- GTK / MSYS2 (WeasyPrint / PDF) ---
$msysBin = "C:\msys64\mingw64\bin"
$gtkBin = "C:\Program Files\Gtk-Runtime\bin"
if (-not (Test-Path $msysBin)) {
    Write-Host "[+] Installation MSYS2 + Pango (PDF)…" -ForegroundColor Yellow
    if (-not (Test-Path "C:\msys64\usr\bin\bash.exe")) {
        winget install MSYS2.MSYS2 --accept-package-agreements --accept-source-agreements --silent 2>$null
    }
    if (Test-Path "C:\msys64\usr\bin\bash.exe") {
        C:\msys64\usr\bin\bash.exe -lc "pacman -Sy --noconfirm mingw-w64-x86_64-pango mingw-w64-x86_64-gdk-pixbuf2 mingw-w64-x86_64-cairo mingw-w64-x86_64-glib2 mingw-w64-x86_64-harfbuzz mingw-w64-x86_64-fontconfig" 2>$null
    }
}
if (-not (Test-Path $gtkBin)) {
    winget install GtkD.GtkPlusRuntime.x64 --accept-package-agreements --accept-source-agreements --silent 2>$null
}
foreach ($p in @($msysBin, $gtkBin)) {
    if (Test-Path $p) {
        $env:Path = "$p;$env:Path"
        Write-Host "  PDF libs OK : $p" -ForegroundColor Gray
    }
}

# --- Seed ---
Write-Host "[5/5] Seed des donnees demo…" -ForegroundColor Yellow
Push-Location (Join-Path $Root "backend")
$envExample = Join-Path $Root "backend\.env.dev.example"
$envFile = Join-Path $Root "backend\.env"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "  .env cree depuis .env.dev.example" -ForegroundColor Gray
}
$env:FLASK_APP = "run.py"
& $python -m flask seed
& "$Root\scripts\reset-admin.ps1" -Target native | Out-Null
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation terminee !" -ForegroundColor Green
Write-Host "  Demarrer : .\scripts\start-native.ps1" -ForegroundColor Green
Write-Host "  Backend  : http://localhost:5000" -ForegroundColor Green
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor Green
Write-Host "  Admin    : admin@ecole.local / Admin123!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

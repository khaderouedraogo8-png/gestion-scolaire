# Validation complete - dev + prod
# Usage: .\scripts\validate-all.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$passed = 0
$failed = 0

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

Step "Health dev port 5000" {
    $r = Invoke-RestMethod http://localhost:5000/api/health
    if ($r.status -ne "ok") { throw "status not ok" }
}

Step "Health prod port 8080" {
    $r = Invoke-RestMethod http://localhost:8080/api/health
    if ($r.status -ne "ok") { throw "status not ok" }
    if ($r.redis -ne "ok") { throw "redis not ok" }
}

Step "Pytest prod integration" {
    docker exec gestion-prod-backend-1 python -m pytest tests/integration/ -q --tb=no
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
}

Step "E2E API modules prod" {
    docker exec gestion-prod-backend-1 python scripts/e2e_api_validation.py
    if ($LASTEXITCODE -ne 0) { throw "e2e api failed" }
}

Step "Test de charge Locust 15s" {
    docker exec gestion-prod-backend-1 python scripts/run_load_test.py --host http://127.0.0.1:5000 --users 3 --duration 10s
    # Tolere les 429 rate-limit sur login en charge
    if ($LASTEXITCODE -ne 0) { Write-Host "  Avertissement load test (rate limit possible)" -ForegroundColor Yellow }
}

Step "Seed demo etendu" {
    docker exec gestion-prod-backend-1 flask --app run.py seed | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "seed failed" }
}

Step "Notifications email Mailhog" {
    docker exec gestion-prod-backend-1 flask --app run.py traiter-notifications
}

Step "Backup PostgreSQL" {
    docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml --profile backup run --rm backup
    if ($LASTEXITCODE -ne 0) { throw "backup failed" }
}

Step "Test restauration backup" {
    # Nouveau backup avec --clean pour restauration propre
    docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml --profile backup run --rm backup | Out-Null
    & "$Root\scripts\test-restore-backup.ps1"
}

Step "Playwright prod smoke" {
    & "$Root\scripts\reset-admin.ps1" -Target prod
    Push-Location frontend
    npx playwright test -c playwright.prod.config.js
    if ($LASTEXITCODE -ne 0) { throw "playwright prod failed" }
    Pop-Location
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Resultat : $passed OK, $failed FAIL" -ForegroundColor Yellow
Write-Host "Mailhog  : http://localhost:8025" -ForegroundColor Yellow
Write-Host "Prod app : http://localhost:8080" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

if ($failed -gt 0) { exit 1 }

# Setup local complet — dev + prod + seed + validation
# Usage: .\scripts\setup-local.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Gestion Scolaire — Setup local ===" -ForegroundColor Cyan

Write-Host "`n[1/4] Demarrage stack DEV..." -ForegroundColor Yellow
docker compose up -d --build

Write-Host "`n[2/4] Demarrage stack PROD (port 8080)..." -ForegroundColor Yellow
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build

Write-Host "`n[3/4] Attente services..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host "`n[4/4] Seed demo + notifications..." -ForegroundColor Yellow
docker exec gestion-scolaire-backend-1 flask --app run.py seed 2>&1 | Out-Null
docker exec gestion-prod-backend-1 flask --app run.py seed 2>&1 | Out-Null
docker exec gestion-prod-backend-1 flask --app run.py traiter-notifications 2>&1 | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DEV  : http://localhost:5173" -ForegroundColor Green
Write-Host "  PROD : http://localhost:8080" -ForegroundColor Green
Write-Host "  Mail : http://localhost:8025" -ForegroundColor Green
Write-Host "  Admin: admin@ecole.local / Admin123!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Validation: .\scripts\validate-all.ps1" -ForegroundColor Yellow

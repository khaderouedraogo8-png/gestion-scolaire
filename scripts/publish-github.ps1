# Publie le projet sur GitHub (depot prive)
# Usage : .\scripts\publish-github.ps1 [-RepoName gestion-scolaire]
param(
    [string]$RepoName = "gestion-scolaire",
    [string]$Description = "Plateforme de gestion scolaire - Flask + React + PostgreSQL"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI absent. Installez : winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

function Test-GhAuth {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    gh auth status 2>$null | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

if (-not (Test-GhAuth)) {
    Write-Host "Connexion GitHub requise..." -ForegroundColor Yellow
    Write-Host '  Un navigateur va souvrir - suivez les instructions.' -ForegroundColor Gray
    gh auth login -h github.com -p https -w
    if (-not (Test-GhAuth)) {
        Write-Host "Connexion GitHub echouee ou annulee." -ForegroundColor Red
        exit 1
    }
    Write-Host "Connecte a GitHub." -ForegroundColor Green
}

if (-not (Test-Path ".git")) {
    Write-Host "Depot git introuvable." -ForegroundColor Red
    exit 1
}

$status = git status --porcelain
if ($status) {
    Write-Host "Commit des changements en cours..." -ForegroundColor Yellow
    git add -A
    git commit -m "chore: prepare publish to GitHub"
}

Write-Host "Creation du depot prive GitHub : $RepoName" -ForegroundColor Cyan
gh repo create $RepoName --private --source=. --remote=origin --description $Description --push

if ($LASTEXITCODE -eq 0) {
    $url = gh repo view --json url -q .url
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Depot prive cree et pousse !" -ForegroundColor Green
    Write-Host "  $url" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Inviter un testeur :" -ForegroundColor Yellow
    Write-Host "  gh repo edit --add-collaborator EMAIL" -ForegroundColor Gray
    Write-Host '  (ou GitHub - Settings - Collaborators)' -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Guide testeur : docs/INSTALL-TESTEUR.md" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "Echec creation depot. Verifiez : gh auth status" -ForegroundColor Red
    exit 1
}

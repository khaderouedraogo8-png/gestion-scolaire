# Deploiement VPS depuis Windows — prepare le package et affiche la commande SSH
# Usage: .\scripts\deploy-vps.ps1 -Domain ecole.example.fr -Email admin@example.fr -Server user@1.2.3.4
param(
    [Parameter(Mandatory=$true)][string]$Domain,
    [Parameter(Mandatory=$true)][string]$Email,
    [string]$Server = "",
    [string]$AppDir = "/opt/gestion-scolaire"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Preparation deploiement VPS ===" -ForegroundColor Cyan

# Archive du projet (sans node_modules, backups, .env)
$Archive = Join-Path $env:TEMP "gestion-scolaire-deploy.tar.gz"
Write-Host "Creation archive…" -ForegroundColor Yellow

if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar --exclude=node_modules --exclude=frontend/node_modules --exclude=backups `
        --exclude=deploy/.env.prod --exclude=.git -czf $Archive .
    Write-Host "Archive : $Archive" -ForegroundColor Green
} else {
    Write-Host "tar non disponible — utilisez git clone sur le VPS" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== ETAPES SUR LE VPS (Ubuntu 22.04+) ===" -ForegroundColor Cyan
Write-Host @"

# 1. Connexion SSH
ssh root@VOTRE_IP

# 2. Option A — git clone (recommande)
apt update && apt install -y git
git clone VOTRE_REPO_URL $AppDir
cd $AppDir

# 2. Option B — copier l'archive
# scp $Archive root@VOTRE_IP:/tmp/
# ssh root@VOTRE_IP "mkdir -p $AppDir && tar -xzf /tmp/gestion-scolaire-deploy.tar.gz -C $AppDir"

# 3. Installation automatique (Docker + app + SSL + cron)
chmod +x scripts/install-vps.sh
sudo ./scripts/install-vps.sh $Domain $Email

"@ -ForegroundColor White

if ($Server) {
    Write-Host "=== Deploiement automatique vers $Server ===" -ForegroundColor Cyan
    if ($Archive -and (Test-Path $Archive)) {
        scp $Archive "${Server}:/tmp/gestion-scolaire.tar.gz"
        ssh $Server @"
mkdir -p $AppDir && tar -xzf /tmp/gestion-scolaire.tar.gz -C $AppDir
cd $AppDir && chmod +x scripts/install-vps.sh && sudo ./scripts/install-vps.sh $Domain $Email
"@
    } else {
        ssh $Server "cd $AppDir && git pull && sudo ./scripts/install-vps.sh $Domain $Email"
    }
}

Write-Host "Site final : https://$Domain" -ForegroundColor Green

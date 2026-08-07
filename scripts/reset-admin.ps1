# Reset compte admin pour tests / apres restauration
# Usage: .\scripts\reset-admin.ps1 [dev|prod|native]
param([ValidateSet("dev", "prod", "native")][string]$Target = "native")

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = @"
from app import create_app
from app.extensions import get_db
from app.models import Utilisateur
from app.auth.jwt_handler import hash_password
app = create_app()
with app.app_context():
    db = get_db()
    u = db.query(Utilisateur).filter_by(email='admin@ecole.local').first()
    if u:
        u.mot_de_passe_hash = hash_password('Admin123!')
        u.doit_changer_mdp = False
        u.tentatives_echouees = 0
        u.verrouille_jusqu_a = None
        db.commit()
        print('Admin reset OK')
    else:
        print('Admin introuvable')
"@

if ($Target -eq "native") {
    $venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) { Write-Host "Venv introuvable - lancez install-native.ps1" -ForegroundColor Red; exit 1 }
    Get-Content (Join-Path $Root "backend\.env") | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    Push-Location (Join-Path $Root "backend")
    & $venvPython -c $script
    Pop-Location
} else {
    $container = if ($Target -eq "dev") { "gestion-scolaire-backend-1" } else { "gestion-prod-backend-1" }
    docker exec $container python -c $script
}

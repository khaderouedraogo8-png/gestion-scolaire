# Test restauration backup sans interaction
# Usage: .\scripts\test-restore-backup.ps1 [fichier.sql.gz]
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Dump = $args[0]
if (-not $Dump) {
    $latest = Get-ChildItem backups\gestion_scolaire_*.sql.gz -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latest) { $Dump = $latest.FullName }
}
if (-not $Dump -or -not (Test-Path $Dump)) {
    throw "Aucun backup trouve dans backups/"
}

$DumpName = Split-Path $Dump -Leaf
Write-Host "Test restauration depuis $DumpName"

docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml stop backend | Out-Null

# Recree la base proprement avant restauration
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml exec -T postgres psql -U gestion -d postgres -q -c `
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'gestion_scolaire' AND pid <> pg_backend_pid();"
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml exec -T postgres psql -U gestion -d postgres -q -c `
    "DROP DATABASE IF EXISTS gestion_scolaire;"
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml exec -T postgres psql -U gestion -d postgres -q -c `
    "CREATE DATABASE gestion_scolaire OWNER gestion;"

docker run --rm -i `
    -v "${Root}/backups:/backups:ro" `
    --network gestion-prod_internal `
    alpine sh -c "apk add -q gzip postgresql-client && gzip -dc /backups/$DumpName" |
    docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml exec -T postgres psql -U gestion -d gestion_scolaire -q

docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml start backend | Out-Null
Start-Sleep -Seconds 8

& "$Root\scripts\reset-admin.ps1" -Target prod

for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-RestMethod http://localhost:8080/api/health
        if ($r.status -eq "ok") {
            Write-Host "Restauration OK - health check passed" -ForegroundColor Green
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 2
}
throw "Backend non disponible apres restauration"

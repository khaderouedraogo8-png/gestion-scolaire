# Expose la prod locale (8080) sur Internet via Cloudflare Tunnel — sans VPS
# Usage: .\scripts\tunnel-public.ps1
# Resultat: URL https://xxxx.trycloudflare.com accessible publiquement
$ErrorActionPreference = "Stop"

# Verifier que prod tourne
try {
    $h = Invoke-RestMethod http://localhost:8080/api/health -TimeoutSec 5
    if ($h.status -ne "ok") { throw "prod down" }
} catch {
    Write-Host "Demarrez d'abord la stack prod:" -ForegroundColor Red
    Write-Host "  docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up -d" -ForegroundColor Yellow
    exit 1
}

# Telecharger cloudflared si absent
$cf = Join-Path $env:LOCALAPPDATA "cloudflared.exe"
if (-not (Test-Path $cf)) {
    Write-Host "Telechargement cloudflared…" -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $cf
}

Write-Host ""
Write-Host "Lancement tunnel public vers http://localhost:8080 …" -ForegroundColor Cyan
Write-Host "Copiez l'URL https://….trycloudflare.com affichee ci-dessous" -ForegroundColor Yellow
Write-Host ""

& $cf tunnel --url http://localhost:8080

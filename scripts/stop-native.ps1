# Arrete backend + frontend natifs (ports 5000 et 5173)
$ports = @(5000, 5173)
foreach ($port in $ports) {
    $conns = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $conns) {
        $pid = ($line -split '\s+')[-1]
        if ($pid -match '^\d+$') {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "Arrete PID $pid (port $port)" -ForegroundColor Yellow
        }
    }
}
Write-Host "Services natifs arretes." -ForegroundColor Green

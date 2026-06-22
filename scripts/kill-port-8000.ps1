param([int]$Port = 8000)

Write-Host "[Starfall] Checking port $Port..." -ForegroundColor Cyan

$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue

if (-not $connections) {
    Write-Host "[Starfall] Port $Port is already free." -ForegroundColor Green
    exit 0
}

$pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique

foreach ($processId in $pids) {
    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    $name = if ($proc) { $proc.ProcessName } else { "unknown" }
    Write-Host "[Starfall] Stopping $name (PID $processId) on port $Port..." -ForegroundColor Yellow
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

Write-Host "[Starfall] Port $Port is ready." -ForegroundColor Green

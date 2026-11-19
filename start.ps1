# CiteVerify Unified Server Startup Script (Windows PowerShell 5.1+ Compatible)
# Launches both FastAPI Python Backend and Vite React Frontend with process supervision

# 1. Discover Project Root using $PSScriptRoot and absolute path
$projectRoot = $PSScriptRoot
if (-not $projectRoot) {
    $projectRoot = (Get-Item -Path ".").FullName
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CiteVerify — Verify the Science. Trust the Evidence.     " -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 2. Use Join-Path and absolute paths throughout
$backendDir = Join-Path -Path $projectRoot -ChildPath "citeverify-backend"
$frontendParentDir = Join-Path -Path $projectRoot -ChildPath "citeverify-frontend"
$frontendDir = Join-Path -Path $frontendParentDir -ChildPath "citeverify_frontend"
$frontendPackageJson = Join-Path -Path $frontendDir -ChildPath "package.json"

# 3. Verify that both project directories exist
if (-not (Test-Path -Path $backendDir -PathType Container)) {
    Write-Error "[ERROR] Backend directory does not exist: $backendDir"
    exit 1
}

if (-not (Test-Path -Path $frontendDir -PathType Container)) {
    Write-Error "[ERROR] Frontend directory does not exist: $frontendDir"
    exit 1
}

# 4. Verify frontend package.json exists
if (-not (Test-Path -Path $frontendPackageJson -PathType Leaf)) {
    Write-Error "[ERROR] Frontend package.json does not exist: $frontendPackageJson"
    exit 1
}

# 5. Detect Python virtual environment (root .venv -> backend .venv -> system Python)
$pythonExe = $null

$rootVenv = Join-Path -Path (Join-Path -Path $projectRoot -ChildPath ".venv") -ChildPath "Scripts\python.exe"
$backendVenv = Join-Path -Path (Join-Path -Path $backendDir -ChildPath ".venv") -ChildPath "Scripts\python.exe"

if (Test-Path -Path $rootVenv -PathType Leaf) {
    $pythonExe = $rootVenv
    Write-Host "[INFO] Detected Python virtual environment (root): $pythonExe" -ForegroundColor Cyan
}
elseif (Test-Path -Path $backendVenv -PathType Leaf) {
    $pythonExe = $backendVenv
    Write-Host "[INFO] Detected Python virtual environment (backend): $pythonExe" -ForegroundColor Cyan
}
else {
    $systemPythonCmd = Get-Command -Name "python.exe" -ErrorAction SilentlyContinue
    if (-not $systemPythonCmd) {
        $systemPythonCmd = Get-Command -Name "python" -ErrorAction SilentlyContinue
    }
    if ($systemPythonCmd) {
        $pythonExe = $systemPythonCmd.Source
        Write-Host "[WARNING] No virtual environment detected. Falling back to system Python: $pythonExe" -ForegroundColor Yellow
    }
    else {
        Write-Error "[ERROR] Python executable not found. Please install Python or configure a virtual environment."
        exit 1
    }
}

# Set PYTHONPATH environment variable so app.main:app imports cleanly
$env:PYTHONPATH = $backendDir

# Helper function to terminate process trees using taskkill /T /F
function Stop-ServerProcessTree([int]$targetPid, [string]$serverName) {
    if ($targetPid -gt 0) {
        $procExists = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($procExists) {
            Write-Host "Stopping $serverName (PID: $targetPid)..." -ForegroundColor Yellow
            & taskkill.exe /PID $targetPid /T /F 2>&1 | Out-Null
        }
    }
}

$backendProc = $null
$frontendProc = $null

# Register process cleanup trap
trap {
    Write-Host ""
    Write-Host "[TRAP] Interruption received. Cleaning up processes..." -ForegroundColor Red
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-ServerProcessTree $backendProc.Id "Backend"
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-ServerProcessTree $frontendProc.Id "Frontend"
    }
    exit 0
}

try {
    Write-Host "Starting servers..." -ForegroundColor Cyan

    # 6. Start Backend: Python uvicorn app.main:app --host 127.0.0.1 --port 8000
    # 8. Use Start-Process with explicit WorkingDirectory and PassThru
    # 9. Display outputs directly in the terminal via -NoNewWindow
    # 13. Paths containing spaces are passed directly without fragile string splitting
    $backendArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")
    $backendProc = Start-Process -FilePath $pythonExe `
                                 -ArgumentList $backendArgs `
                                 -WorkingDirectory $backendDir `
                                 -NoNewWindow `
                                 -PassThru

    if (-not $backendProc -or $backendProc.HasExited) {
        Write-Error "[ERROR] Failed to start backend server."
        exit 1
    }

    # 7. Start Frontend: cmd.exe /c npm run dev -- --host 127.0.0.1 with WorkingDirectory = $frontendDir
    # 8. Use Start-Process with explicit WorkingDirectory and PassThru
    $frontendArgs = @("/c", "npm run dev -- --host 127.0.0.1")
    $frontendProc = Start-Process -FilePath "cmd.exe" `
                                  -ArgumentList $frontendArgs `
                                  -WorkingDirectory $frontendDir `
                                  -NoNewWindow `
                                  -PassThru

    if (-not $frontendProc -or $frontendProc.HasExited) {
        Write-Error "[ERROR] Failed to start frontend server."
        if ($backendProc -and -not $backendProc.HasExited) {
            Stop-ServerProcessTree $backendProc.Id "Backend"
        }
        exit 1
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " CiteVerify Stack Running Successfully:" -ForegroundColor White
    Write-Host "   -> Backend:  http://127.0.0.1:8000  (API Docs: http://127.0.0.1:8000/docs)" -ForegroundColor Cyan
    Write-Host "   -> Frontend: http://127.0.0.1:5173" -ForegroundColor Magenta
    Write-Host "   -> Backend PID:  $($backendProc.Id)" -ForegroundColor Gray
    Write-Host "   -> Frontend PID: $($frontendProc.Id)" -ForegroundColor Gray
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "Press Ctrl+C to cleanly stop both servers." -ForegroundColor Gray
    Write-Host ""

    # 10. Keep both servers running while the script is active
    # 11. If either server exits unexpectedly, stop the other server
    while (-not $backendProc.HasExited -and -not $frontendProc.HasExited) {
        Start-Sleep -Milliseconds 500
    }

    if ($backendProc.HasExited -and -not $frontendProc.HasExited) {
        Write-Host ""
        Write-Host "[ALERT] Backend process terminated unexpectedly (Exit code: $($backendProc.ExitCode))." -ForegroundColor Red
    }
    elseif ($frontendProc.HasExited -and -not $backendProc.HasExited) {
        Write-Host ""
        Write-Host "[ALERT] Frontend process terminated unexpectedly (Exit code: $($frontendProc.ExitCode))." -ForegroundColor Red
    }
}
finally {
    # 12. On exit / Ctrl+C, terminate both process trees using taskkill /T and /F
    Write-Host ""
    Write-Host "Shutting down CiteVerify server processes..." -ForegroundColor Yellow
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-ServerProcessTree $backendProc.Id "Backend"
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-ServerProcessTree $frontendProc.Id "Frontend"
    }
    Write-Host "All CiteVerify servers stopped cleanly." -ForegroundColor Green
}

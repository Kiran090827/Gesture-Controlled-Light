$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$exitCode = 0

try {
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw 'Python 3.12 is required. Install 64-bit Python with the Python launcher, then run this script again.'
        }
        & $launcher.Source -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw 'Could not create the project virtual environment.'
        }
    }

    & $pythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw 'Dependency installation failed. Check your internet connection and try again.'
    }

    Write-Host "`nStarting Gesture-Controlled Phone Light...`n"
    & $pythonExe main.py
    if ($LASTEXITCODE -ne 0) {
        $exitCode = $LASTEXITCODE
        Write-Host "`nThe app exited with code $exitCode. Review the error above."
    }
}
catch {
    $exitCode = 1
    Write-Host "`nError: $($_.Exception.Message)" -ForegroundColor Red
}

Read-Host 'Press Enter to close this window'
exit $exitCode

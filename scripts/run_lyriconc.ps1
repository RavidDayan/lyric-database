$ErrorActionPreference = "Stop"

try {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    Set-Location $projectRoot

    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    $venvPythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Host "Preparing LyriConc for first use..."
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            & $pyLauncher.Source -3 -m venv .venv
        }
        else {
            $python = Get-Command python -ErrorAction SilentlyContinue
            if (-not $python) {
                throw "Python 3.11 or newer is required. Install Python from https://www.python.org/downloads/ and run this file again."
            }
            & $python.Source -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create the Python virtual environment."
        }
    }

    & $venvPython -c "import PySide6, lyriconc" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing LyriConc and its required packages..."
        & $venvPython -m pip install -e $projectRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Could not install LyriConc. Check the messages above and your internet connection."
        }
    }

    if (-not (Test-Path $venvPythonw)) {
        throw "The virtual environment does not contain pythonw.exe."
    }

    Write-Host "Opening LyriConc..."
    Start-Process -FilePath $venvPythonw -ArgumentList "-m", "lyriconc" -WorkingDirectory $projectRoot
}
catch {
    Write-Host ""
    Write-Host "LyriConc could not start:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
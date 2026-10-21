$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    Write-Host "`n[1/5] Verification du fichier de verrouillage" -ForegroundColor Cyan
    & uv lock --check

    if ($LASTEXITCODE -ne 0) {
        throw "uv.lock ne correspond pas au projet."
    }

    Write-Host "`n[2/5] Verification du formatage" -ForegroundColor Cyan
    & uv run ruff format --check src streamlit_app tests main.py

    if ($LASTEXITCODE -ne 0) {
        throw "Le formatage doit etre corrige."
    }

    Write-Host "`n[3/5] Analyse Ruff" -ForegroundColor Cyan
    & uv run ruff check src streamlit_app tests main.py

    if ($LASTEXITCODE -ne 0) {
        throw "Ruff signale des erreurs."
    }

    Write-Host "`n[4/5] Tests" -ForegroundColor Cyan
    & uv run pytest -q

    if ($LASTEXITCODE -ne 0) {
        throw "Des tests ont echoue."
    }

    Write-Host "`n[5/5] Construction" -ForegroundColor Cyan
    & uv build

    if ($LASTEXITCODE -ne 0) {
        throw "La construction a echoue."
    }

    Write-Host "`nToutes les verifications ont reussi." -ForegroundColor Green
}
finally {
    Pop-Location
}
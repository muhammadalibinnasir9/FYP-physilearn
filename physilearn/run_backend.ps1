$venvPath = "..\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    . $venvPath
    python manage.py migrate
    python manage.py runserver
} else {
    Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
}

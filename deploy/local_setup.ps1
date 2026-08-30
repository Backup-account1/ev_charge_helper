param([switch]$RunTests)
$ErrorActionPreference = "Stop"
Write-Host "EV Charge Agent - Windows local setup"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.11+ and reopen Cursor."
}
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created. Add TELEGRAM_BOT_TOKEN before running."
}
if ($RunTests) {
    & ".\.venv\Scripts\python.exe" -m pytest -q
    & ".\.venv\Scripts\python.exe" -m compileall app scripts
}
Write-Host "Setup complete."
Write-Host "Run: python -m app.main"

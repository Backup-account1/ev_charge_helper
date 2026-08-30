# Cursor local deployment instructions

Open this repository in Cursor on Windows.

GOAL:
Make the EV Charge Agent run locally first. Do NOT deploy to Google Cloud yet.

1. Inspect the entire repository before changing anything.
2. Create a Python virtual environment:
   python -m venv .venv
3. Install:
   python -m pip install --upgrade pip
   pip install -r requirements.txt
4. Install Chromium:
   playwright install chromium
5. Ensure `.env` exists; if absent, copy `.env.example` to `.env`.
6. Never commit or display `.env`, provider authentication state, cookies, tokens,
   private keys, or database files.
7. Run `pytest -q` and `python -m compileall app scripts`.
8. Fix all errors found.
9. Run the Telegram bot locally with `python -m app.main`.
10. Do not claim Malanka/Evika extraction works until their authenticated pages
    have actually been inspected.
11. Keep this demo minimal: no Docker, cloud deployment, Groq/LLM, PostgreSQL,
    Redis, ML, or vehicle recognition.
12. Never ask the user to put provider passwords in source code.
13. If TELEGRAM_BOT_TOKEN is missing, explain how to add it to `.env`; never invent it.
14. Re-run tests after fixes and report exact results.

WINDOWS:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

If PowerShell blocks activation:
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1

MALANKA AUTH:
Only after the application passes tests:
python scripts/login_malanka.py
This opens Chromium and the user logs in manually. The state is saved to
data/auth/malanka.json. Treat it as a credential and never print/commit it.

EVIKA AUTH:
python scripts/login_evika.py

DO NOT DEPLOY TO GOOGLE CLOUD IN THIS TASK.

At the end report:
- files changed
- tests and exact result
- successful commands
- remaining provider-specific TODOs
- exact command to start the local bot

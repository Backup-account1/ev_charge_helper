# Windows / Cursor local-first deployment

Run the first demo locally before using any cloud VM.

See `CURSOR_LOCAL_DEPLOY.md` for the exact Cursor task.

Quick setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
pytest -q
python -m compileall app scripts
python -m app.main
```

Automated setup:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\local_setup.ps1 -RunTests
```

Keep `.env` and `data/auth/` private.


# EV Charge Agent — Belarus

A provider-based EV charging monitor designed for Telegram. The MVP supports:

- Telegram bot setup wizard.
- Vehicle connector profiles: CHAdeMO, Type 1, GB/T DC, GB/T AC, CCS, Type 2.
- Station search by location + radius.
- Provider adapters for Malanka and Evika.
- Authenticated browser sessions through Playwright `storage_state` (no password stored in the application).
- Current charging-session monitoring: SOC, kW, status.
- Historical time-series storage in SQLite.
- Charging-time estimation with a simple adaptive taper model.
- Vehicle/battery-profile support.
- Optional vehicle-photo recognition interface, deliberately isolated from the core charging logic.
- Automated tests for the estimator and provider normalization.

## Important

The Malanka and Evika web/mobile systems are authenticated and their private APIs/selectors can change. This repository therefore does **not** invent or hard-code undocumented private API endpoints. Provider adapters are written so that the real selectors/API calls can be plugged in after inspecting an authenticated session.

Evika's public app description confirms station discovery, charging-session tracking, power graphs and session details. See the project notes in `docs/providers.md`.

## Quick start

### 1. Requirements

- Python 3.11+
- Telegram bot token
- Chromium installed by Playwright

### 2. Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 3. Configure

Copy `.env.example` to `.env` and set:

```text
TELEGRAM_BOT_TOKEN=...
DATABASE_URL=sqlite:///data/evcharge.db
POLL_SECONDS=60
DEFAULT_RADIUS_KM=2
```

### 4. Create authenticated browser states

Run:

```bash
python scripts/login_malanka.py
python scripts/login_evika.py
```

Each script opens Chromium. Log in yourself. The script saves only Playwright browser state locally under `data/auth/`.

Do not commit these files. They are credentials equivalent to an active browser session.

### 5. Run

```bash
python -m app.main
```

The bot will offer:

- `/start`
- `/settings`
- `/nearby`
- `/status`
- `/watch`
- `/stop`

## Telegram flow

`/start`

1. Select vehicle.
2. Select supported connectors.
3. Select default radius.
4. Share location when searching.
5. Select providers.
6. Request nearby stations.

Example:

> `/nearby`

Then share a Telegram location. The bot returns compatible stations within the configured radius.

## Architecture

```text
Telegram
   |
   v
Bot handlers
   |
   +---- User/vehicle settings
   |
   +---- Nearby station search
   |
   v
ProviderRegistry
   +---- MalankaProvider
   +---- EvikaProvider
   +---- future providers
   |
   v
Normalized Station / Session models
   |
   +---- HistoryStore (SQLite)
   |
   +---- ChargingEstimator
   |
   v
Telegram notification
```

The provider interface is intentionally small. A new provider should implement:

- `list_stations()`
- `get_active_session()`

and return normalized models.

## Authentication

Use Playwright `storage_state`, not copied cookies.

Why:

- keeps login inside your browser;
- preserves cookies/local storage;
- avoids putting passwords in code;
- can be renewed by logging in again;
- works with sites that use modern authentication.

The saved state should be treated as a secret.

## Estimation model

The MVP estimator uses recent observations:

```text
timestamp, SOC %, power kW
```

It estimates the average SOC gain per minute and detects tapering.

For a known vehicle/battery profile, a profile can specify:

- usable battery kWh;
- nominal DC power;
- taper start SOC;
- taper floor;
- taper exponent.

The estimator uses observed data when available and falls back to the profile.

This is intentionally not presented as an exact battery/BMS simulator. It is an operational estimate that improves as historical data accumulates.

## Historical learning

Each observation is stored with:

- provider
- station
- connector
- vehicle profile
- battery chemistry
- timestamp
- SOC
- power
- optional voltage/current
- optional vehicle recognition result

Later, a model can be trained from these sessions without changing the provider layer.

## Vehicle recognition

The repository includes a clean interface:

```text
photo -> VehicleRecognizer -> make/model/confidence
```

A production implementation can use a vision model. The charging estimator should never require recognition: recognition is a confidence-weighted enhancement.

## Security

Never commit:

- `.env`
- `data/auth/*`
- database files
- Telegram bot tokens
- photos containing sensitive information

The `.gitignore` covers these paths.

## Disclaimer

This project monitors information visible to the authenticated account you control. Respect provider terms, rate limits, and applicable law. Prefer an official API when a provider makes one available.

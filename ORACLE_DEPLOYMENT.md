# Oracle Cloud Always-Free demo deployment (no Docker)

## 1. Create the VM

Create an Oracle Cloud Always Free compute VM using an Ubuntu image. Prefer an Always Free shape that is actually available in your tenancy/region. Oracle's free availability and quotas can change, so verify the current Console quota before creating it.

Open SSH (TCP/22) only from your own IP if possible.

## 2. Install Python and Playwright

SSH to the VM:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git unzip
mkdir -p ~/ev-charge-agent
cd ~/ev-charge-agent
```

Copy the project here, then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
```

## 3. Configure Telegram

```bash
cp .env.example .env
nano .env
```

Set `TELEGRAM_BOT_TOKEN` and keep `.env` private.

## 4. Authentication: do this on your PC

Do NOT put your provider password in the project.

The login scripts open a visible browser, so the simplest demo workflow is:

1. Run the provider login script on your own PC.
2. Log in manually.
3. The script writes `data/auth/malanka.json` or `data/auth/evika.json`.
4. Transfer that file securely to the Oracle VM.

Playwright's `storage_state` contains cookies/local storage and may contain credentials usable to impersonate the session. Keep these files secret and never commit them.

Example using SCP from Windows PowerShell:

```powershell
scp .\data\auth\malanka.json ubuntu@YOUR_SERVER_IP:/home/ubuntu/ev-charge-agent/data/auth/
scp .\data\auth\evika.json ubuntu@YOUR_SERVER_IP:/home/ubuntu/ev-charge-agent/data/auth/
```

Adjust the remote username/path to your VM.

## 5. Initialize and test

```bash
cd ~/ev-charge-agent
source .venv/bin/activate
python -m app.main
```

Send `/start` to the Telegram bot.

## 6. Run continuously with systemd

Create:

```bash
sudo nano /etc/systemd/system/ev-charge-agent.service
```

Use:

```ini
[Unit]
Description=EV Charge Telegram Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ev-charge-agent
EnvironmentFile=/home/ubuntu/ev-charge-agent/.env
ExecStart=/home/ubuntu/ev-charge-agent/.venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ev-charge-agent
sudo systemctl status ev-charge-agent
journalctl -u ev-charge-agent -f
```

## 7. Updating

Stop the service, update files, run tests, then restart:

```bash
sudo systemctl stop ev-charge-agent
source .venv/bin/activate
pytest -q
sudo systemctl start ev-charge-agent
```

## Important provider limitation

The repository intentionally does not invent private Malanka/Evika API endpoints or selectors. After authentication works, inspect the actual authenticated pages/network calls and implement the provider-specific extraction. Prefer an official API if the provider supplies one.

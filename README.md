# PriorityMail AI

PriorityMail AI fetches Gmail messages, classifies them, tracks career-related emails, and creates high-priority alerts. Optional WhatsApp delivery is available through Twilio.

## Automation Worker

Run one automation cycle:

```powershell
python worker.py --once
```

Keep the worker running continuously:

```powershell
python worker.py
```

Each cycle fetches Gmail messages, saves classifications, rebuilds career records, rebuilds alerts, and sends unsent WhatsApp alerts only when `PMA_AUTO_SEND_WHATSAPP=true` and all Twilio variables are configured.

## Windows Scheduling

For unattended local runs, register a Windows Task Scheduler job:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_worker_task.ps1
```

Use a custom interval in minutes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_worker_task.ps1 -IntervalMinutes 10
```

The scheduled task calls `scripts/run_worker_once.ps1`, which runs `python worker.py --once` from the project folder. This avoids leaving a long-running terminal open.

Check scheduled-task status and recent worker logs:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_worker_status.ps1
```

Worker output is appended to `logs/worker.log`, which is ignored by Git.

## Mobile Access

Start the dashboard on your PC:

```powershell
streamlit run app.py
```

Connect your phone to the same Wi-Fi network, then open:

```text
http://YOUR_PC_WIFI_IP:8501
```

On this PC, the current Wi-Fi URL is:

```text
http://10.90.98.226:8501
```

If the page does not load on mobile, allow Python or Streamlit through Windows Firewall for private networks.

## Configuration

Copy `.env.example` to `.env`, then fill in any values you need:

```dotenv
PMA_FETCH_INTERVAL_SECONDS=300
PMA_FETCH_MAX_RESULTS=10
PMA_AUTO_SEND_WHATSAPP=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX
```

Leave `PMA_AUTO_SEND_WHATSAPP=false` until Twilio WhatsApp credentials are ready.

Check WhatsApp readiness without sending a message:

```powershell
python .\scripts\check_whatsapp.py
```

Set up Twilio WhatsApp credentials interactively:

```powershell
python .\scripts\setup_whatsapp.py
```

After Twilio credentials are configured, send one test message:

```powershell
python .\scripts\check_whatsapp.py --send-test
```

After the test message succeeds, enable automatic WhatsApp alert delivery:

```powershell
python .\scripts\enable_whatsapp_autosend.py
```

## Tests

Run the local test suite with:

```powershell
python -m unittest discover
```

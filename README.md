# uvr2mqtt
Read UVR (TA-Designer / CMI) data and publish it to MQTT with Home Assistant discovery, plus built‑in monitoring.

## Overview
- Polls UVR/CMI HTML using the TA-Designer schema (`Neu.xml`).
- Publishes Home Assistant MQTT discovery and state topics.
- Runs continuously by default (`uvr.py`).
- Optional monitoring: hourly metrics log and Uptime Kuma push.

## Configuration
Create `config.json` in the repo root. Example:

```json
{
  "mqtt": {
    "broker": "192.168.177.152",
    "port": 1883,
    "user": "your_user",
    "password": "your_password"
  },
  "uvr": {
    "xml_filename": "Neu.xml",
    "ip": "192.168.177.5",
    "user": "user",
    "password": "pass"
  },
  "device": { "name": "UVR" },
  "loop": { "interval_seconds": 60 },
  "monitoring": {
    "interval_seconds": 300,
    "uptime_kuma_url": "http://your-uptime-kuma:3001/api/push/xxxxx",
    "metrics_log_file": "uvr_metrics.log"
  }
}
```

Notes:
- `loop.interval_seconds`: how often data is fetched and MQTT states are published.
- `monitoring.interval_seconds`: how often an “up” ping is sent to Uptime Kuma (failures send “down” immediately).
- If `config.json` is missing, environment variables can be used instead (see below).

## Running
Foreground run with logs:

```powershell
python uvr.py
```

What it does:
- Connects to MQTT and publishes discovery once.
- Enters a loop: fetch UVR values, publish to MQTT, optionally push Uptime Kuma.
- Writes metrics to `uvr_metrics.log` hourly and on shutdown.

Legacy sender:
- `send_uvr_mqtt.py` provides a similar loop focused on MQTT only; prefer `uvr.py` for integrated monitoring.

## Monitoring & Metrics
- Hourly metrics file: counts of cycles, successes/partials/failures, pages fetched/failed, MQTT publish stats, average fetch time, uptime.
- Uptime Kuma push (optional):
  - Success: “up” sent at `monitoring.interval_seconds` cadence.
  - Failure: “down” sent immediately with an error summary.

Monitoring is optional and configured via the `monitoring.*` keys.

## Environment variables
- `UVR_INTERVAL` — loop interval override (seconds).
- `UPTIME_KUMA_URL` — Uptime Kuma push URL.
- `METRICS_LOG_FILE` — path to metrics log file.
- `KUMA_INTERVAL_SECONDS` — Kuma success push cadence (seconds).

## Troubleshooting
- Home Assistant shows `unknown`: ensure the loop is running; state topics are not retained and must be published live.
- Discovery missing: verify retained discovery JSON exists under `homeassistant/.../config` topics.
- Duplicate/stale entities: remove old entries from HA’s Entity Registry if device IDs changed.

Quick checks:
- Publish availability: `python scripts/publish_availability.py`
- List retained discovery: `python scripts/check_uvr_discovery_now.py`

Developer notes and testing tips: see `README_DEVELOPERS.md`.

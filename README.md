# uvr2mqtt

Read UVR (TA-Designer / C.M.I.) data and publish it to MQTT with automatic Home Assistant Discovery, robust HTML/XML schema mapping, and built-in monitoring.

---

## Features

- **Schema-driven:** Reads the TA-Designer schema export (`Neu.xml`) to dynamically discover and map all inputs, outputs, and heat meters.
- **Deterministic HTML/XML Mapping:** Resilient parser matching TA-Designer's DIV layout (`pos0`, `pos1`, ...), correctly deferring link buttons (`CMILinkObj`) and skipping purely visual images (`Pic_Obj`).
- **Entity Deduplication:** Seamlessly deduplicates multiple visual references to the same CAN sensor on the schema canvas, and disambiguates true name collisions.
- **Home Assistant Auto-Discovery:** Publishes MQTT discovery configs with accurate units (`°C`, `l/h`, `W/m²`, `kWh`, `kW`, `%`), device classes, and availability timeouts (`expire_after: 600`).
- **Fail-Safe Invariants:** Detects schema-mismatches between XML and live HTML; aborts cleanly on structural mismatch to prevent wrong state assignments.
- **Integrated Monitoring:** Optional hourly metrics JSON logging and [Uptime Kuma](https://github.com/louislam/uptime-kuma) push heartbeat.
- **Self-contained Docker:** Ready-to-use Docker image (`henfri/uvr2mqtt`).

---

## Architecture & Modules

- **`uvr.py`**: Service entry point, main loop, loop scheduler, metrics collection, and Uptime Kuma monitoring.
- **`uvr_parse.py`**: XML parsing (`Neu.xml`) and BeautifulSoup HTML parsing (`schematic_files/*.cgi`), value extraction, and unit normalization.
- **`uvr_fetch.py`**: Resilient HTTP fetcher with retry logic for the C.M.I. web server.
- **`uvr_mqtt.py`**: MQTT client connection, Home Assistant discovery payload generation, and state publishing.

---

## Configuration

Create `config.json` in the project root (or mount it into `/app/config.json`). See [`config.example.json`](config.example.json):

```json
{
  "mqtt": {
    "broker": "192.168.1.100",
    "port": 1883,
    "user": "your_mqtt_user",
    "password": "your_mqtt_password"
  },
  "uvr": {
    "xml_filename": "Neu.xml",
    "ip": "192.168.1.50",
    "user": "your_cmi_user",
    "password": "your_cmi_password"
  },
  "device": {
    "name": "UVR"
  },
  "loop": {
    "interval_seconds": 60
  },
  "monitoring": {
    "interval_seconds": 300,
    "uptime_kuma_url": "http://your-uptime-kuma:3001/api/push/xxxxx",
    "metrics_log_file": "uvr_metrics.log",
    "kuma_interval_seconds": 300
  },
  "logging": {
    "debug": false
  }
}
```

### Configuration Parameters
- `loop.interval_seconds`: Interval in seconds for polling UVR data and publishing MQTT state updates (default: `60`).
- `device.name`: Base name used for Home Assistant MQTT discovery prefix and device naming (default: `UVR`).
- `monitoring.interval_seconds`: Interval in seconds for successful Uptime Kuma push pings (failures trigger immediate push).
- `logging.debug`: Set to `true` for verbose diagnostic logs across all modules.

If `config.json` is omitted, credentials can also be passed via environment variables (`MQTT_BROKER`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`, `UVR_IP`, `UVR_USER`, `UVR_PASSWORD`, etc.).

---

## Running

### Option A: Docker Compose (Recommended)

Using the existing [`docker-compose.yml`](docker-compose.yml):

```yaml
services:
  uvr2mqtt:
    image: henfri/uvr2mqtt:latest
    container_name: uvr2mqtt
    restart: unless-stopped
    volumes:
      - /path/to/config.json:/app/config.json:ro
      - /path/to/Neu.xml:/app/Neu.xml:ro
```

Run with:
```bash
docker compose up -d
```

### Option B: Local Python Runtime

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place `config.json` and your TA-Designer XML export (e.g. `Neu.xml`) in the directory.
3. Start the service:
   ```bash
   python uvr.py
   ```

---

## Monitoring & Metrics

- **Hourly Metrics Log:** Aggregates cycle counts, successes, partials, fetch errors, MQTT publish stats, average fetch latency, and process uptime into `uvr_metrics.log`.
- **Uptime Kuma Integration:** Sends periodic "up" heartbeats and reports immediate "down" states with error summaries on communication faults.

For complete monitoring details and log format specifications, see [`MONITORING.md`](MONITORING.md).

---

## Troubleshooting & Utilities

- **Home Assistant entities show `unavailable`:** Normal behavior during startup or after 10 minutes without updates (`expire_after: 600`). Verify `uvr.py` is actively running and reaching the C.M.I.
- **Inspect retained discovery topics:**
  ```bash
  python scripts/check_uvr_discovery_now.py
  ```
- **Publish retained availability:**
  ```bash
  python scripts/publish_availability.py
  ```

For testing commands and developer guidelines, see [`README_DEVELOPERS.md`](README_DEVELOPERS.md).

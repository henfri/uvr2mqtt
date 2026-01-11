# UVR Monitoring & Metrics

## Features

### 1. Metrics Logging
The script automatically tracks operational metrics and writes them to a log file once per hour:

- Total cycles executed
- Successful/partial/failed cycles
- Pages fetched vs failed
- MQTT publish success/failure counts
- Average fetch time
- Uptime

**Configuration:**
```json
{
  "monitoring": {
    "metrics_log_file": "uvr_metrics.log"
  }
}
```

**Log Format:**
Each line is a JSON object with timestamp and metrics:
```json
{
  "timestamp": "2026-01-08T19:05:01.822258",
  "uptime_seconds": 3600,
  "metrics": {
    "total_cycles": 60,
    "successful_cycles": 58,
    "partial_success_cycles": 2,
    "failed_cycles": 0,
    "total_pages_fetched": 180,
    "total_pages_failed": 0,
    "mqtt_publish_success": 60,
    "mqtt_publish_failure": 0,
    "average_fetch_time_seconds": 4.52
  }
}
```

### 2. Uptime Kuma Integration
The script can push status updates to [Uptime Kuma](https://github.com/louislam/uptime-kuma) push monitors.

**Setup in Uptime Kuma:**
1. Create a new monitor
2. Select "Push" as monitor type
3. Copy the push URL (e.g., `http://your-uptime-kuma:3001/api/push/xxxxx`)
4. Add to config.json

**Configuration:**
```json
{
  "monitoring": {
    "uptime_kuma_url": "http://your-uptime-kuma:3001/api/push/xxxxx"
  }
}
```

**Behavior:**
- ✅ **Success**: Pushes "up" status with fetch time and page count after each successful cycle
- ❌ **Failure**: Pushes "down" status with error message when cycle fails
- 📊 **Ping**: Reports fetch duration in milliseconds

### 3. Configurable Polling Interval
Control how often the UVR data is fetched and published.

**Configuration:**
```json
{
  "monitoring": {
    "interval": 60
  }
}
```

Or via environment variable:
```bash
export UVR_INTERVAL=60
```

Default: 60 seconds

## Complete Configuration Example

```json
{
  "mqtt": {
    "broker": "192.168.1.100",
    "port": 1883,
    "user": "mqtt_user",
    "password": "mqtt_password"
  },
  "uvr": {
    "xml_filename": "Neu.xml",
    "ip": "192.168.1.5",
    "user": "user",
    "password": "password"
  },
  "device": {
    "name": "UVR"
  },
  "monitoring": {
    "interval": 60,
    "uptime_kuma_url": "http://192.168.1.200:3001/api/push/abcd1234",
    "metrics_log_file": "uvr_metrics.log"
  }
}
```

## Environment Variables

Alternative to config.json:

- `UVR_INTERVAL` - Polling interval in seconds
- `UPTIME_KUMA_URL` - Uptime Kuma push monitor URL
- `METRICS_LOG_FILE` - Path to metrics log file

## Running

```bash
python uvr.py
```

The script will:
1. Connect to MQTT broker
2. Send discovery configuration
3. Start continuous loop:
   - Fetch UVR data every `interval` seconds
   - Publish to MQTT
   - Push status to Uptime Kuma (if configured)
   - Write metrics to log file (every hour)
4. On shutdown, write final metrics

## Log Output Example

```
2026-01-08 19:06:06,242 [INFO] Connected to MQTT broker 192.168.177.152
2026-01-08 19:06:06,243 [INFO] Metrics logging to: uvr_metrics.log (written hourly)
2026-01-08 19:06:06,243 [INFO] Uptime Kuma push enabled: http://192.168.1.200:3001/...
2026-01-08 19:06:06,243 [INFO] Starting UVR loop: interval=60s, mqtt=enabled
2026-01-08 19:06:06,243 [INFO] === Cycle 1: Starting data fetch ===
2026-01-08 19:06:10,510 [INFO] ✓ Successfully fetched 3/3 pages (4.27s)
2026-01-08 19:06:10,535 [INFO] ✓ Successfully published values to MQTT
2026-01-08 19:06:10,536 [INFO] === Cycle 1: Complete. Waiting 60s until next cycle ===
```

## Monitoring Dashboard

You can parse the metrics log file to create dashboards showing:
- Success rate over time
- Fetch performance trends  
- MQTT reliability
- Page fetch failures

Example parsing with `jq`:
```bash
# Get latest metrics
tail -1 uvr_metrics.log | jq .

# Get average fetch times from last 24 hours
grep "$(date -d '24 hours ago' +%Y-%m-%d)" uvr_metrics.log | \
  jq -r '.metrics.average_fetch_time_seconds'
```

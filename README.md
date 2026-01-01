# uvr2mqtt
Tool to read UVR (TA-Designer / CMI) data and publish it to MQTT using Home Assistant MQTT discovery.

## Introduction
This project polls the CMI/TA-Designer XML export and publishes per-sensor discovery and state topics to an MQTT broker so Home Assistant can automatically create entities.

## Configuration
Create a `config.json` in the repository root with your MQTT and UVR credentials. Example:

```
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
    "device": { "name": "UVR" }
}
```

The script falls back to environment variables if `config.json` is missing.

## Quick start (foreground)
Run the sender in the foreground to see logs and errors:

```powershell
$env:PYTHONPATH = "X:\uvr"  # optional if running from repo root
python send_uvr_mqtt.py
```

Press Ctrl+C to stop. Running in the foreground is the best way to catch parsing errors, connection problems, and other runtime issues.
# uvr2mqtt — quick user guide

uvr2mqtt polls a UVR (TA-Designer / CMI) controller and publishes sensors to an MQTT broker using Home Assistant MQTT Discovery.

Prerequisites
- A working MQTT broker with Home Assistant MQTT integration.
- The UVR/C.M.I. device accessible on your network and the exported schema/XML uploaded to the CMI.

Configuration
1. Create `config.json` in the repository root (example):

```json
{
  "mqtt": { "broker": "192.168.177.152", "port": 1883, "user": "your_user", "password": "your_password" },
  "uvr": { "xml_filename": "Neu.xml", "ip": "192.168.177.5", "user": "user", "password": "pass" },
  "device": { "name": "UVR" }
}
```

2. The script falls back to environment variables if `config.json` is missing.

Running the sender (foreground)
Run in foreground to see logs and parsing details:

```powershell
python send_uvr_mqtt.py
```

Press Ctrl+C to stop. Foreground runs are helpful for debugging.
# uvr2mqtt
Tool to read UVR (TA-Designer / CMI) data and publish it to MQTT using Home Assistant MQTT discovery.

## Introduction
This project polls the CMI/TA-Designer XML export and publishes per-sensor discovery and state topics to an MQTT broker so Home Assistant can automatically create entities.

## Configuration
Create a `config.json` in the repository root with your MQTT and UVR credentials. Example:

```
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
    "device": { "name": "UVR" }
}
```

The script falls back to environment variables if `config.json` is missing.

## Quick start (foreground)
Run the sender in the foreground to see logs and errors:

```powershell
$env:PYTHONPATH = "X:\uvr"  # optional if running from repo root
python send_uvr_mqtt.py
```

Press Ctrl+C to stop. Running in the foreground is the best way to catch parsing errors, connection problems, and other runtime issues.

## uvr2mqtt — quick user guide

uvr2mqtt polls a UVR (TA-Designer / CMI) controller and publishes sensors to an MQTT broker using Home Assistant MQTT Discovery.

Prerequisites
- A working MQTT broker with Home Assistant MQTT integration.
- The UVR/C.M.I. device accessible on your network and the exported schema/XML uploaded to the CMI.

Configuration
1. Create `config.json` in the repository root (example):

```json
{
  "mqtt": { "broker": "192.168.177.152", "port": 1883, "user": "your_user", "password": "your_password" },
  "uvr": { "xml_filename": "Neu.xml", "ip": "192.168.177.5", "user": "user", "password": "pass" },
  "device": { "name": "UVR" }
}
```

2. The script falls back to environment variables if `config.json` is missing.

Running the sender (foreground)
Run in foreground to see logs and parsing details:

```powershell
python send_uvr_mqtt.py
```

Press Ctrl+C to stop. Foreground runs are helpful for debugging.

Useful quick checks
- Publish retained availability: `python scripts/publish_availability.py`
- List retained discovery topics: `python scripts/check_uvr_discovery_now.py`

If Home Assistant shows `unknown` values
- Ensure the sender is running and publishing state messages (not retained) while HA is active.
- Confirm retained discovery JSON exists for `homeassistant/.../uvr_.../config` topics.
- Remove stale/duplicate entities from the HA Entity Registry if discovery changed device ids in the past.

For developer notes, testing and debugging tips, see `README_DEVELOPERS.md`.

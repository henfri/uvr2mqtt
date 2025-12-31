UVR Dashboard

This repository includes a ready-to-use Lovelace YAML dashboard for Home Assistant at `dashboards/uvr_dashboard.yaml`.

Install/import options

- Option A — Add as a YAML dashboard file:
  1. Copy `dashboards/uvr_dashboard.yaml` to your Home Assistant `config` folder (for example `config/lovelace/uvr_dashboard.yaml`).
  2. In `configuration.yaml` enable the YAML dashboard or include it via `lovelace:` configuration per HA docs.

- Option B — Paste into the UI Raw Editor:
  1. In Home Assistant go to `Overview` → the three-dot menu → `Edit Dashboard` → `Raw configuration editor`.
  2. Paste the contents of `dashboards/uvr_dashboard.yaml` into the editor and save.

Entity mapping

The dashboard expects entities published by `send_uvr_mqtt.py` using the sanitized names. Example entity ids used:

- `sensor.uvr_t_speicher_1_wert`
- `sensor.uvr_t_speicher_2_wert`
- `sensor.uvr_t_speicher_3_wert`
- `sensor.uvr_t_speicher_4_wert`
- `sensor.uvr_t_kollektor_wert`
- `sensor.uvr_temp_aussen_wert`
- `sensor.uvr_ww_anf_solltemperatur`
- `binary_sensor.uvr_vergl_2_status_wa_wb_diff`

If you renamed `device.name` in `config.json`, update the entity ids accordingly (the dashboard uses `uvr` as the device id). To discover the exact entity ids on your MQTT broker, use MQTT Explorer or run `mosquitto_sub -h <broker> -t 'homeassistant/#' -v`.

Troubleshooting

- If values show as `unknown` in the dashboard, ensure `send_uvr_mqtt.py` is running and publishing the non-retained state messages while Home Assistant is running, or restart HA after importing the dashboard and confirming retained discovery `config` topics exist for the device.
- If you see duplicate or stale entities in HA, clean up the HA Entity Registry for the old device ids and restart HA.

If you want, I can adapt the dashboard layout (graphs, gauges, auto-refresh cards) or create a custom Lovelace card bundle — tell me which widgets you prefer.
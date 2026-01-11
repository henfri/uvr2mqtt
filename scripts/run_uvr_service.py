"""Run UVR fetch->MQTT loop using config.json.

- Loads MQTT/UVR credentials from config.json
- Publishes Home Assistant discovery once
- Sends state updates in a loop
- Honors RUN_DURATION_SECONDS env var for bounded runs (useful for CI/tests)
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

from uvr import read_data, filter_empty_values
from uvr_mqtt import (
    configure_logging,
    build_mqtt_client,
    check_mqtt_connection,
    send_values,
    create_config,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOG = logging.getLogger("uvr_service")


def load_config() -> dict:
    cfg_path = Path("config.json")
    if not cfg_path.exists():
        raise FileNotFoundError("config.json not found; please provide credentials")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def main():
    cfg = load_config()
    loop_cfg = cfg.get("loop", {})
    interval = int(loop_cfg.get("interval_seconds", 60))
    run_for = int(os.environ.get("RUN_DURATION_SECONDS", 0))  # 0 means run forever

    configure_logging(debug=bool(os.environ.get("UVR_DEBUG")))

    mqtt_cfg = cfg.get("mqtt", {})
    device_name = cfg.get("device", {}).get("name", "UVR")

    LOG.info("Connecting to MQTT broker %s", mqtt_cfg.get("broker"))
    client = build_mqtt_client(mqtt_cfg)

    # Publish discovery once
    values, status = read_data(cfg.get("uvr", {}))
    values = filter_empty_values(values)
    create_config(client, device_name, values)

    start = time.time()
    cycle = 0
    while True:
        cycle += 1
        LOG.info("Cycle %d: fetching/publishing", cycle)
        try:
            if not check_mqtt_connection(client):
                raise ConnectionError("MQTT not connected")
            values, status = read_data(cfg.get("uvr", {}))
            values = filter_empty_values(values)
            send_values(client, device_name, values)
            LOG.debug("Status: %s", status)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("Cycle %d failed: %s", cycle, exc)
        time.sleep(interval)
        if run_for and (time.time() - start) >= run_for:
            LOG.info("Run duration reached; exiting")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOG.info("Interrupted; exiting")
        sys.exit(0)

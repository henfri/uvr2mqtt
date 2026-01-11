"""UVR2MQTT runtime and helpers.

- Facade functions for reading UVR data (`read_data`) delegating to uvr_fetch/uvr_parse.
- Runtime loop with MQTT discovery/state publishing, metrics logging, and optional Uptime Kuma push.
"""
from typing import Any, Dict, Optional, List
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging
from pathlib import Path
import os
import json
import time
import requests

from uvr_fetch import read_html
from uvr_parse import (
    combine_html_xml,
    MyHTMLParser,
    read_xml,
    separate,
    extract_entity_data,
    filter_empty_values,
)
from uvr_mqtt import (
    build_mqtt_client,
    create_config,
    send_values,
    sanitize_name,
    check_mqtt_connection,
)

logger = logging.getLogger(__name__)


# ------------------------ Core data read facade ------------------------

def _read_data(xml: str, ip: str, user: str, password: str):
    """Read UVR data from all pages. Returns (combined_dict, success_status_dict)."""
    try:
        tree = ET.parse(xml)
        root = tree.getroot()
    except Exception as e:  # noqa: BLE001
        logger.error('[UVR] Failed to parse XML file %s: %s', xml, e)
        return [], {'xml_error': str(e), 'pages_attempted': 0, 'pages_successful': 0, 'pages_failed': 0}

    Seiten = range(0, len(root.findall('./Seiten/')))
    combined_dict = []
    pages_attempted = len(Seiten)
    pages_successful = 0
    pages_failed = 0
    failed_pages: List[int] = []

    for Seite in Seiten:
        try:
            beschreibung, id_conf, xml_dict = read_xml(root, Seite)
            html = read_html(ip, Seite, user, password)
            if html is not None and html is not False:
                combined_dict.append(combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html))
                pages_successful += 1
            else:
                logger.error('[UVR] Page %d: HTML could not be loaded', Seite)
                pages_failed += 1
                failed_pages.append(Seite)
        except Exception as e:  # noqa: BLE001
            logger.exception('[UVR] Page %d: Exception during processing: %s', Seite, e)
            pages_failed += 1
            failed_pages.append(Seite)

    status = {
        'pages_attempted': pages_attempted,
        'pages_successful': pages_successful,
        'pages_failed': pages_failed,
        'failed_pages': failed_pages,
        'all_successful': pages_failed == 0
    }
    return combined_dict, status


def read_data(credentials: Dict[str, Any]):
    """Read UVR data. Returns (combined_dict, status_dict)."""
    return _read_data(credentials['xml_filename'], credentials['ip'], credentials['user'], credentials['password'])


def print_data(combined_dict, filter_unit=None):
    for page_values in combined_dict:
        logger.debug('[UVR] Page values: %s', page_values)
        logger.debug(extract_entity_data(page_values, unit=filter_unit))


# ------------------------ Metrics tracking ------------------------

class MetricsTracker:
    """Track operational metrics and write to log file hourly."""

    def __init__(self, log_file_path: str):
        self.log_file = Path(log_file_path)
        self.cycle_count = 0
        self.success_count = 0
        self.partial_success_count = 0
        self.failure_count = 0
        self.total_pages_fetched = 0
        self.total_pages_failed = 0
        self.mqtt_publish_success = 0
        self.mqtt_publish_failure = 0
        self.total_fetch_time = 0.0
        self.last_log_time = datetime.now()
        self.start_time = datetime.now()

    def record_cycle(self, fetch_status: Dict, fetch_duration: float, mqtt_success: bool = False):
        self.cycle_count += 1
        self.total_fetch_time += fetch_duration

        if fetch_status.get('all_successful'):
            self.success_count += 1
        elif fetch_status.get('pages_successful', 0) > 0:
            self.partial_success_count += 1
        else:
            self.failure_count += 1

        self.total_pages_fetched += fetch_status.get('pages_successful', 0)
        self.total_pages_failed += fetch_status.get('pages_failed', 0)

        if mqtt_success:
            self.mqtt_publish_success += 1
        else:
            self.mqtt_publish_failure += 1

    def should_write_log(self) -> bool:
        return (datetime.now() - self.last_log_time) >= timedelta(hours=1)

    def write_log(self):
        now = datetime.now()
        uptime = now - self.start_time
        avg_fetch_time = self.total_fetch_time / self.cycle_count if self.cycle_count > 0 else 0
        log_entry = {
            "timestamp": now.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "metrics": {
                "total_cycles": self.cycle_count,
                "successful_cycles": self.success_count,
                "partial_success_cycles": self.partial_success_count,
                "failed_cycles": self.failure_count,
                "total_pages_fetched": self.total_pages_fetched,
                "total_pages_failed": self.total_pages_failed,
                "mqtt_publish_success": self.mqtt_publish_success,
                "mqtt_publish_failure": self.mqtt_publish_failure,
                "average_fetch_time_seconds": round(avg_fetch_time, 2),
            },
        }
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            logger.info("Metrics written to %s", self.log_file)
            self.last_log_time = now
        except Exception:  # noqa: BLE001
            logger.exception("Failed to write metrics log")

    def get_summary(self) -> str:
        uptime = datetime.now() - self.start_time
        return (
            f"Uptime: {int(uptime.total_seconds())}s | "
            f"Cycles: {self.cycle_count} | "
            f"Success: {self.success_count} | "
            f"Partial: {self.partial_success_count} | "
            f"Failed: {self.failure_count}"
        )


# ------------------------ Uptime Kuma ------------------------

def push_uptime_kuma(url: str, status: str = "up", msg: str = "", ping: Optional[float] = None):
    if not url:
        return
    try:
        params = {"status": status}
        if msg:
            params["msg"] = msg
        if ping is not None:
            params["ping"] = int(ping)
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        logger.debug("Uptime Kuma push successful")
    except Exception:  # noqa: BLE001
        logger.debug("Failed to push to Uptime Kuma", exc_info=True)


# ------------------------ Runtime entrypoint ------------------------

__all__ = [
    'read_data',
    'combine_html_xml',
    'MyHTMLParser',
    'separate',
    'extract_entity_data',
    'filter_empty_values',
]


if __name__ == "__main__":
    import sys as _sys

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(_sys.stdout)], force=True)
    logger.setLevel(logging.INFO)
    logging.getLogger('uvr_fetch').setLevel(logging.INFO)
    logging.getLogger('uvr_parse').setLevel(logging.INFO)
    logging.getLogger('uvr_mqtt').setLevel(logging.INFO)

    cfg = {}
    cfg_path = Path.cwd() / "config.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load config.json")
            cfg = {}

    uvr_cfg = cfg.get("uvr", {})
    mqtt_cfg = cfg.get("mqtt", {})
    device_cfg = cfg.get("device", {})
    monitoring_cfg = cfg.get("monitoring", {})
    loop_cfg = cfg.get("loop", {})

    xml_file = uvr_cfg.get("xml_filename", os.environ.get("UVR_XML", "Neu.xml"))
    ip = uvr_cfg.get("ip", os.environ.get("UVR_IP", "192.168.177.5"))
    user = uvr_cfg.get("user", os.environ.get("UVR_USER", "user"))
    password = uvr_cfg.get("password", os.environ.get("UVR_PASSWORD", ""))

    try:
        loop_interval = int(loop_cfg.get("interval_seconds", os.environ.get("UVR_INTERVAL", 60)))
    except Exception:
        loop_interval = 60

    try:
        run_duration_seconds = int(os.environ.get("RUN_DURATION_SECONDS", 0))
    except Exception:
        run_duration_seconds = 0

    uptime_kuma_url = monitoring_cfg.get("uptime_kuma_url", os.environ.get("UPTIME_KUMA_URL", ""))
    metrics_log_file = monitoring_cfg.get("metrics_log_file", os.environ.get("METRICS_LOG_FILE", "uvr_metrics.log"))
    try:
        kuma_interval_seconds = int(monitoring_cfg.get("interval_seconds", monitoring_cfg.get("kuma_interval_seconds", os.environ.get("KUMA_INTERVAL_SECONDS", loop_interval))))
    except Exception:
        kuma_interval_seconds = loop_interval

    broker = mqtt_cfg.get("broker", os.environ.get("MQTT_BROKER"))
    port = int(mqtt_cfg.get("port", os.environ.get("MQTT_PORT", 1883)))
    mqtt_user = mqtt_cfg.get("user", os.environ.get("MQTT_USER", ""))
    mqtt_password = mqtt_cfg.get("password", os.environ.get("MQTT_PASSWORD", ""))
    device_name = device_cfg.get("name", os.environ.get("DEVICE_NAME", "UVR_TADesigner"))

    mqtt_client = None
    availability_topic = None
    try:
        if broker:
            mqtt_client = build_mqtt_client({"broker": broker, "port": port, "user": mqtt_user, "password": mqtt_password})
            device_id = sanitize_name(device_name)
            availability_topic = f"homeassistant/{device_id}/availability"
            mqtt_client.publish(availability_topic, "online", retain=True)
            try:
                logger.info("Sending initial discovery config to MQTT...")
                initial_data, initial_status = _read_data(xml_file, ip, user, password)
                if initial_status.get('pages_successful', 0) > 0:
                    initial_values = filter_empty_values(initial_data)
                    create_config(mqtt_client, device_name, initial_values)
                    logger.info("Discovery config sent successfully")
                else:
                    logger.warning("Skipping discovery config - no pages fetched successfully")
            except Exception:  # noqa: BLE001
                logger.exception("Failed to publish discovery config - will continue without it")
    except Exception:  # noqa: BLE001
        logger.exception("MQTT setup failed; continuing without MQTT publishing")
        mqtt_client = None

    metrics = MetricsTracker(metrics_log_file)
    logger.info("Metrics logging to: %s (written hourly)", metrics_log_file)
    last_kuma_push = datetime.now() - timedelta(seconds=kuma_interval_seconds)

    logger.info("Starting UVR loop: interval=%ss, mqtt=%s", loop_interval, ("enabled" if mqtt_client else "disabled"))
    cycle_num = 0
    start_time = time.time()
    try:
        while True:
            if run_duration_seconds and (time.time() - start_time) >= run_duration_seconds:
                logger.info("Run duration reached; exiting")
                break
            cycle_num += 1
            try:
                logger.info("=== Cycle %d: Starting data fetch ===", cycle_num)
                fetch_start = time.time()
                combined_data, fetch_status = _read_data(xml_file, ip, user, password)
                page_values = filter_empty_values(combined_data)
                fetch_duration = time.time() - fetch_start

                mqtt_success = False
                if fetch_status.get('all_successful'):
                    logger.info("Successfully fetched %d/%d pages (%.2fs)", fetch_status['pages_successful'], fetch_status['pages_attempted'], fetch_duration)
                else:
                    logger.warning("Partial success: fetched %d/%d pages (failed: %s)", fetch_status['pages_successful'], fetch_status['pages_attempted'], fetch_status.get('failed_pages', []))
                    if fetch_status['pages_successful'] == 0:
                        logger.error("All pages failed to fetch")
                        raise Exception("All pages failed")

                if mqtt_client:
                    try:
                        if not check_mqtt_connection(mqtt_client):
                            logger.error("MQTT connection unavailable; skipping publish")
                        else:
                            send_values(mqtt_client, device_name, page_values)
                            logger.info("Successfully published values to MQTT")
                            mqtt_success = True
                    except Exception:  # noqa: BLE001
                        logger.exception("Failed to publish MQTT values")

                metrics.record_cycle(fetch_status, fetch_duration, mqtt_success)

                if uptime_kuma_url:
                    now_ts = datetime.now()
                    if (now_ts - last_kuma_push).total_seconds() >= kuma_interval_seconds:
                        status_msg = f"Cycle {cycle_num}: {fetch_status['pages_successful']}/{fetch_status['pages_attempted']} pages"
                        push_uptime_kuma(uptime_kuma_url, status="up", msg=status_msg, ping=fetch_duration * 1000)
                        last_kuma_push = now_ts

                if metrics.should_write_log():
                    metrics.write_log()

                logger.info("=== Cycle %d: Complete. Waiting %ds until next cycle ===", cycle_num, loop_interval)
                time.sleep(loop_interval)
            except KeyboardInterrupt:
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception("Error during polling cycle: %s", e)
                if uptime_kuma_url:
                    push_uptime_kuma(uptime_kuma_url, status="down", msg=f"Cycle {cycle_num} failed: {str(e)[:100]}")
                time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Stopping UVR loop (KeyboardInterrupt)")
    finally:
        try:
            metrics.write_log()
            logger.info("Final metrics: %s", metrics.get_summary())
        except Exception:  # noqa: BLE001
            logger.debug("Could not write final metrics")

        try:
            if mqtt_client and availability_topic:
                try:
                    mqtt_client.publish(availability_topic, "offline", retain=True)
                except Exception:
                    pass
                try:
                    mqtt_client.loop_stop()
                except Exception:
                    pass
                try:
                    mqtt_client.disconnect()
                except Exception:
                    pass
        except Exception:  # noqa: BLE001
            logger.exception("Error during MQTT shutdown")

import json
import logging
import pprint
import re
import random
import time
from typing import Any, Dict, Optional, Tuple

import paho.mqtt.client as mqtt

logger = logging.getLogger("UVR2MQTT")


def _reason_code_value(reason_code: Any) -> int:
    """Normalize paho reason code objects/ints to an integer value."""
    if isinstance(reason_code, int):
        return reason_code
    try:
        return int(getattr(reason_code, "value", reason_code))
    except Exception:
        return -1


def _on_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
    rc_value = _reason_code_value(reason_code)
    if rc_value == 0:
        logger.info("MQTT connected (reason=%s)", reason_code)
    else:
        logger.warning("MQTT connect callback indicates failure (reason=%s)", reason_code)


def _on_disconnect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
    rc_value = _reason_code_value(reason_code)
    if rc_value == 0:
        logger.info("MQTT disconnected cleanly")
    else:
        logger.warning("MQTT disconnected unexpectedly (reason=%s)", reason_code)


def _publish_with_diagnostics(client: mqtt.Client, topic: str, payload: Any, retain: bool = False) -> None:
    info = client.publish(topic, payload, retain=retain)
    rc = getattr(info, "rc", None)
    mid = getattr(info, "mid", None)
    if rc in (None, mqtt.MQTT_ERR_SUCCESS, 0):
        logger.debug("MQTT publish queued/accepted: topic=%s mid=%s retain=%s", topic, mid, retain)
        return
    logger.warning("MQTT publish returned rc=%s for topic=%s mid=%s retain=%s", rc, topic, mid, retain)


def configure_logging(debug: bool = False) -> None:
    """Configure logging level for UVR2MQTT logger and related modules."""
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    # Also configure related module loggers
    logging.getLogger('uvr_fetch').setLevel(level)
    logging.getLogger('uvr_parse').setLevel(level)
    logging.getLogger('uvr').setLevel(level)


def sanitize_name(name: Any) -> str:
    if not isinstance(name, str):
        return str(name)
    s = re.sub(r"\([^)]*/[^)]*\)", "", name)
    s = s.replace('(', '').replace(')', '')
    replacements = {
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue', 'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = re.sub(r"[^0-9A-Za-z]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip('_')
    return s.lower()


def get_device_class(unit: Optional[str], t: str) -> Tuple[Optional[str], str, Optional[str]]:
    device_class = None
    entity_type = "sensor"
    unit_of_measurement = None
    if unit is None:
        return device_class, entity_type, unit_of_measurement
    if unit == "°C":
        return "temperature", "sensor", "°C"
    if unit == "l/h":
        return None, "sensor", "l/h"
    if unit in ("W/m²", "W/m2", "W/m°²"):
        return "irradiance", "sensor", "W/m²"
    if unit == "W":
        return "power", "sensor", "W"
    if unit == "kWh":
        return "energy", "sensor", "kWh"
    if unit == "kW":
        return "power", "sensor", "kW"
    if unit == "min":
        return "duration", "sensor", "min"
    if unit == "%":
        return None, "sensor", "%"
    if unit == "switch":
        return "running", "binary_sensor", None
    if unit == "OutputMode":
        return None, "sensor", None
    return None, "sensor", unit


def build_mqtt_client(mqtt_cfg: Dict[str, Any]) -> mqtt.Client:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    if mqtt_cfg.get("user") and mqtt_cfg.get("password"):
        client.username_pw_set(mqtt_cfg.get("user"), mqtt_cfg.get("password"))

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            broker = mqtt_cfg["broker"]
            port = int(mqtt_cfg.get("port", 1883))
            logger.info("Connecting to MQTT broker %s:%s (attempt %s/%s)", broker, port, attempt, max_attempts)
            client.connect(broker, port, keepalive=300)
            client.loop_start()
            time.sleep(1)
            if client.is_connected():
                logger.info("Connected to MQTT broker %s:%s", broker, port)
                return client
            logger.warning("MQTT connect attempt %s did not establish a session", attempt)
        except Exception:
            wait = min(2 ** attempt + random.uniform(0, 1), 30)
            logger.warning("MQTT connect attempt %s failed; retrying in %.1f seconds...", attempt, wait)
            time.sleep(wait)
    raise ConnectionError(f"Failed to connect to MQTT broker {mqtt_cfg.get('broker')}")


def check_mqtt_connection(client: mqtt.Client) -> bool:
    if client.is_connected():
        logger.debug("MQTT Connection active")
        return True
    logger.warning("MQTT connection lost; attempting reconnect")
    max_retries = 6
    for attempt in range(1, max_retries + 1):
        try:
            client.reconnect()
            wait = min(2 ** attempt + random.uniform(0, 1), 30)
            time.sleep(wait)
            if client.is_connected():
                logger.info("MQTT reconnected on attempt %s", attempt)
                return True
        except Exception:
            logger.warning("MQTT reconnect attempt %s failed", attempt)
            time.sleep(min(2 ** attempt, 30))
    logger.error("MQTT reconnection exhausted")
    return False


def send_config(mqtt_client: mqtt.Client, mqtt_device_name: str, entity_name: str, unit: Optional[str], friendly_name: Optional[str] = None) -> None:
    device_class, entity_type, unit_of_measurement = get_device_class(unit, entity_name)
    device_id = sanitize_name(mqtt_device_name)
    object_id = entity_name
    config_topic = f"{device_id}_{entity_type}_{object_id}"
    topic_str = "state_topic"
    config_payload = {
        "name": (friendly_name if friendly_name is not None else entity_name),
        topic_str: f"homeassistant/{entity_type}/{device_id}/{object_id}/state",
        "unique_id": f"{device_id}_{object_id}".lower(),
        "device": {
            "identifiers": [f"{device_id}"],
            "name": mqtt_device_name,
            "manufacturer": "UVR",
            "model": "UVR-TADesigner",
        },
    }
    if unit_of_measurement is not None:
        config_payload["unit_of_measurement"] = unit_of_measurement
    if device_class:
        config_payload["device_class"] = device_class
    availability_topic = f"homeassistant/{device_id}/availability"
    config_payload["availability_topic"] = availability_topic
    config_payload["payload_available"] = "online"
    config_payload["payload_not_available"] = "offline"
    config_payload["expire_after"] = 600
    
    # Set state_class only for numeric sensors with a valid unit of measurement.
    # Text/status/mode sensors (such as OutputMode, *_mode, or unitless sensors)
    # must NEVER receive a state_class, as non-numeric values ('AUTO', 'HAND', etc.)
    # cause Home Assistant to raise an unhandled ValueError.
    is_mode_sensor = (
        entity_name.endswith("_mode")
        or (friendly_name is not None and friendly_name.endswith("_mode"))
        or unit == "OutputMode"
    )
    if entity_type == "sensor" and not is_mode_sensor and unit_of_measurement is not None:
        if device_class == "energy":
            config_payload["state_class"] = "total_increasing"
        else:
            config_payload["state_class"] = "measurement"
    mqtt_message = json.dumps(config_payload)
    mqtt_topic = f"homeassistant/{entity_type}/{config_topic}/config"
    logger.debug("send_config -> topic: %s payload: %s", mqtt_topic, mqtt_message)
    _publish_with_diagnostics(mqtt_client, mqtt_topic, mqtt_message, retain=True)


def bool_to_on_off(v: Any, n: str) -> str:
    try:
        if float(v) == 1.0:
            return "ON"
        if float(v) == 0.0:
            return "OFF"
    except Exception:
        logger.warning("Unexpected value %s in bool_to_on_off for %s", v, n)
    return "OFF"


def send_values(client: mqtt.Client, device_name: str, values: Any, retain_state: bool = True) -> None:
    logger.debug("send_values for device %s", device_name)
    device_id = sanitize_name(device_name)
    for entry in values:
        for sensor_name, data in entry.items():
            device_class, entity_type, unit_of_measurement = get_device_class(data.get("unit"), sensor_name)
            object_id = sanitize_name(sensor_name)
            state_topic = f"homeassistant/{entity_type}/{device_id}/{object_id}/state"
            if sensor_name.endswith("_mode") or data.get("unit") == "OutputMode":
                mode_val = data.get('value')
                payload = 'AUTO' if mode_val == 1 or str(mode_val).lower() == '1' else ('HAND' if mode_val == 0 or str(mode_val).lower() == '0' else str(mode_val))
            elif sensor_name.endswith("_percent"):
                payload = float(data.get('value')) if data.get('value') is not None else None
            else:
                if entity_type == "binary_sensor":
                    payload = bool_to_on_off(float(data.get('value')) if data.get('value') is not None else 0, sensor_name)
                else:
                    try:
                        payload = float(data.get('value')) if data.get('value') is not None else None
                    except Exception:
                        payload = str(data.get('value'))
            try:
                if isinstance(payload, str):
                    _publish_with_diagnostics(client, state_topic, payload, retain=retain_state)
                else:
                    _publish_with_diagnostics(client, state_topic, json.dumps(payload), retain=retain_state)
                logger.debug("Published %s -> %s", state_topic, payload)
            except Exception:
                logger.exception("Failed to publish %s", state_topic)


def create_config(mqtt_client: mqtt.Client, mqtt_device_name: str, values: Any) -> None:
    for entry in values:
        for name, data in entry.items():
            entity_name = sanitize_name(name)
            send_config(mqtt_client, mqtt_device_name, entity_name, data.get("unit"), friendly_name=name)

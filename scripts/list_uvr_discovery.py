"""Subscribe to homeassistant/# briefly and list retained discovery topics
that mention 'uvr' or 'uvr_tadesigner'. Uses config.json or env vars for broker.
"""
import json
import os
import time
import paho.mqtt.client as mqtt


def load_config():
    cfg_path = os.path.join(os.getcwd(), "config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    mqtt_cfg = cfg.get("mqtt", {})
    mqtt_cfg.setdefault("broker", os.environ.get("MQTT_BROKER", "localhost"))
    mqtt_cfg.setdefault("port", int(os.environ.get("MQTT_PORT", 1883)))
    mqtt_cfg.setdefault("user", os.environ.get("MQTT_USER", ""))
    mqtt_cfg.setdefault("password", os.environ.get("MQTT_PASSWORD", ""))
    return mqtt_cfg


found = []


def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected — subscribing to homeassistant/#")
    client.subscribe("homeassistant/#")


def on_message(client, userdata, msg):
    if msg.retain:
        t = msg.topic
        if "uvr" in t.lower():
            payload = msg.payload.decode("utf-8", errors="replace")
            print("RETAIN:", t)
            print("  payload:", payload[:200])
            found.append((t, payload))


def main():
    cfg = load_config()
    client = mqtt.Client()
    if cfg.get("user") and cfg.get("password"):
        client.username_pw_set(cfg.get("user"), cfg.get("password"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(cfg.get("broker"), cfg.get("port"), keepalive=60)
    client.loop_start()
    print("Collecting retained discovery topics for 6s...")
    time.sleep(6)
    client.loop_stop()
    client.disconnect()

    if not found:
        print("No retained discovery topics mentioning 'uvr' found.")
    else:
        print("Found retained topics:")
        for t, p in found:
            print(t)


if __name__ == '__main__':
    main()

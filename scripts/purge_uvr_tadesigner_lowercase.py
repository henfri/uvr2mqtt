#!/usr/bin/env python3
"""Safe purge of retained Home Assistant discovery /config topics that contain
the exact lowercase string 'uvr_tadesigner'."""
import json
import time
import re
import sys
from pathlib import Path
import paho.mqtt.client as mqtt

CONF_PATH = Path(__file__).resolve().parents[1] / "config.json"

pattern = re.compile(r".*uvr_tadesigner.*?/config$")

found = set()

def on_connect(client, userdata, flags, rc):
    client.subscribe("homeassistant/#")

def on_message(client, userdata, msg):
    if msg.retain and pattern.match(msg.topic):
        found.add(msg.topic)


def main():
    if not CONF_PATH.exists():
        print("config.json not found at", CONF_PATH)
        sys.exit(1)
    conf = json.loads(CONF_PATH.read_text())
    mconf = conf.get("mqtt", {})

    client = mqtt.Client()
    if mconf.get("user"):
        client.username_pw_set(mconf.get("user"), mconf.get("password"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mconf.get("broker", "localhost"), int(mconf.get("port", 1883)))
    client.loop_start()
    print("Collecting retained uvr_tadesigner /config topics for 6 seconds...")
    time.sleep(6)
    client.loop_stop()

    if not found:
        print("No retained uvr_tadesigner /config topics found.")
        return

    print(f"Found {len(found)} topics; purging by publishing empty retained payloads...")
    client = mqtt.Client()
    if mconf.get("user"):
        client.username_pw_set(mconf.get("user"), mconf.get("password"))
    client.connect(mconf.get("broker", "localhost"), int(mconf.get("port", 1883)))
    for t in sorted(found):
        print("Purging:", t)
        client.publish(t, payload=b"", retain=True)
    time.sleep(1)
    print("Purge complete.")

if __name__ == '__main__':
    main()

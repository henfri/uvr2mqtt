#!/usr/bin/env python3
"""Collect retained Home Assistant discovery config topics for UVR_TADesigner
and publish empty retained payloads to delete them (case-sensitive)."""
import json
import time
import re
import sys
from pathlib import Path
import paho.mqtt.client as mqtt

CONF_PATH = Path(__file__).resolve().parents[1] / "config.json"

pattern = re.compile(r".*UVR_TADesigner.*?/config$")

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
    print("Collecting retained UVR_TADesigner /config topics for 6 seconds...")
    time.sleep(6)
    client.loop_stop()

    if not found:
        print("No retained UVR_TADesigner /config topics found.")
        return

    print("Found {} topics; purging by publishing empty retained payloads...".format(len(found)))
    client = mqtt.Client()
    if mconf.get("user"):
        client.username_pw_set(mconf.get("user"), mconf.get("password"))
    client.connect(mconf.get("broker", "localhost"), int(mconf.get("port", 1883)))
    for t in sorted(found):
        print("Purging:", t)
        client.publish(t, payload=b"", retain=True)
    # give broker time to process
    time.sleep(1)
    print("Purge complete.")

if __name__ == '__main__':
    main()

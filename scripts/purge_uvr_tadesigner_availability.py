#!/usr/bin/env python3
"""Remove retained availability topic for uvr_tadesigner."""
import json
import sys
from pathlib import Path
import paho.mqtt.client as mqtt

CONF_PATH = Path(__file__).resolve().parents[1] / "config.json"
TOPIC = "homeassistant/uvr_tadesigner/availability"

if not CONF_PATH.exists():
    print("config.json not found at", CONF_PATH)
    sys.exit(1)

conf = json.loads(CONF_PATH.read_text())
mconf = conf.get("mqtt", {})

client = mqtt.Client()
if mconf.get("user"):
    client.username_pw_set(mconf.get("user"), mconf.get("password"))
client.connect(mconf.get("broker", "localhost"), int(mconf.get("port", 1883)))
client.publish(TOPIC, payload=b"", retain=True)
print("Published empty retained payload to", TOPIC)

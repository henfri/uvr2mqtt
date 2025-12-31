import json
import time
import ssl
from pathlib import Path
import paho.mqtt.client as mqtt

cfg_path = Path(__file__).parents[1] / 'config.json'
config = json.loads(cfg_path.read_text())
broker = config['mqtt']['broker']
port = config['mqtt'].get('port', 1883)
user = config['mqtt'].get('user')
password = config['mqtt'].get('password')

found = []

def on_connect(client, userdata, flags, rc):
    client.subscribe('homeassistant/#')


def on_message(client, userdata, msg):
    if msg.retain:
        try:
            payload = msg.payload.decode('utf-8')
        except Exception:
            payload = repr(msg.payload)
        line = f"RETained: {msg.topic} -> {payload}"
        print(line)
        if 'uvr' in msg.topic.lower() or 'uvr' in payload.lower():
            found.append((msg.topic, payload))


client = mqtt.Client()
if user:
    client.username_pw_set(user, password)
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker, port, 60)
client.loop_start()
# wait a short time to collect retained messages
try:
    time.sleep(5)
finally:
    client.loop_stop()
    client.disconnect()

print('\nSummary:')
if found:
    for t, p in found:
        print(f"MATCH: {t} -> {p}")
else:
    print('No retained topics mentioning "uvr" found.')

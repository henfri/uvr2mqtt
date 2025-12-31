import json
import paho.mqtt.client as mqtt
from pathlib import Path

cfg = json.load(open(Path.cwd() / 'config.json'))
mb = cfg['mqtt']
dev = cfg.get('device', {})

device_id = dev.get('name', 'UVR')
client = mqtt.Client()
if mb.get('user'):
    client.username_pw_set(mb.get('user'), mb.get('password'))
client.connect(mb.get('broker'), mb.get('port', 1883), 60)
topic = f"homeassistant/{device_id.lower()}/availability"
client.publish(topic, 'online', retain=True)
client.disconnect()
print('published', topic, '-> online')

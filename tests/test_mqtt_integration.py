import unittest
from uvr_mqtt import send_config, send_values, sanitize_name


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))


class TestMQTTIntegration(unittest.TestCase):
    def test_send_config_and_values(self):
        client = FakeClient()
        device_name = "UVR"
        # send a simple config
        send_config(client, device_name, 'test_sensor', '%', friendly_name='Test Sensor')
        self.assertTrue(len(client.published) >= 1)
        topic, payload, retain = client.published[0]
        self.assertIn('homeassistant/sensor', topic)
        data = __import__('json').loads(payload)
        self.assertEqual(data.get('name'), 'Test Sensor')

        # send values
        client.published.clear()
        values = [{
            'T.Speicher 1 Wert': {'value': 61.9, 'unit': '°C'},
            'Pumpe 1 Status': {'value': 1.0, 'unit': 'switch'},
            'Some Modus_mode': {'value': 1.0, 'unit': 'OutputMode'},
            'Some Modus_percent': {'value': 12.5, 'unit': '%'},
        }]
        send_values(client, device_name, values)
        # expect at least 4 publishes
        self.assertTrue(len(client.published) >= 4)
        # ensure topics look right
        topics = [p[0] for p in client.published]
        self.assertTrue(any('/t_speicher_1_wert/state' in t for t in topics))


if __name__ == '__main__':
    unittest.main()

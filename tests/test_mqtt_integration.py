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
        # ensure mode publishes text AUTO or HAND
        mode_pub = [p for p in client.published if 'some_modus_mode' in p[0]]
        self.assertTrue(len(mode_pub) >= 1)
        self.assertEqual(mode_pub[0][1], 'AUTO')

    def test_create_config_with_mode_sensors(self):
        from uvr_mqtt import create_config
        import json
        client = FakeClient()
        device_name = "UVR"
        values = [{
            'Ausgang 15 (analog)  Modus (Hand/Auto)_mode': {'value': 1, 'unit': 'OutputMode'},
            'Ausgang 15 (analog)  Modus (Hand/Auto)_percent': {'value': 100.0, 'unit': '%'},
            'SOLSTART Zähler Startversuche': {'value': 0.0, 'unit': None},
        }]
        create_config(client, device_name, values)
        self.assertEqual(len(client.published), 3)

        configs = {p[0]: json.loads(p[1]) for p in client.published}
        mode_topic = "homeassistant/sensor/uvr_sensor_ausgang_15_analog_modus_mode/config"
        percent_topic = "homeassistant/sensor/uvr_sensor_ausgang_15_analog_modus_percent/config"
        unitless_topic = "homeassistant/sensor/uvr_sensor_solstart_zaehler_startversuche/config"

        self.assertIn(mode_topic, configs)
        self.assertIn(percent_topic, configs)
        self.assertIn(unitless_topic, configs)

        # Mode sensor: must NOT have state_class or unit_of_measurement
        self.assertNotIn("state_class", configs[mode_topic])
        self.assertNotIn("unit_of_measurement", configs[mode_topic])

        # Percent sensor: must have measurement and %
        self.assertEqual(configs[percent_topic].get("state_class"), "measurement")
        self.assertEqual(configs[percent_topic].get("unit_of_measurement"), "%")

        # Unitless sensor: must NOT have state_class
        self.assertNotIn("state_class", configs[unitless_topic])
        self.assertNotIn("unit_of_measurement", configs[unitless_topic])


if __name__ == '__main__':
    unittest.main()

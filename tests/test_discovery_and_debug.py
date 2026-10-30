import json
import logging
import unittest

from uvr_mqtt import send_config, configure_logging, sanitize_name


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))


class TestDiscoveryAndDebug(unittest.TestCase):
    def test_send_config_contains_expected_fields(self):
        client = FakeClient()
        device_name = "My Device"
        entity_name = sanitize_name("My Sensor")
        send_config(client, device_name, entity_name, "%")

        # one publish should have happened
        self.assertTrue(len(client.published) >= 1)
        topic, payload, retain = client.published[0]
        data = json.loads(payload)

        # unique_id deterministic
        expected_unique = f"{sanitize_name(device_name)}_{entity_name}"
        self.assertEqual(data.get("unique_id"), expected_unique)

        # device info present
        device = data.get("device")
        self.assertIsNotNone(device)
        self.assertIn("identifiers", device)
        self.assertIn("manufacturer", device)

        # availability topic present
        self.assertIn("availability_topic", data)

        # unit is set to % for percent
        self.assertEqual(data.get("unit_of_measurement"), "%")
        self.assertEqual(data.get("state_class"), "measurement")

    def test_send_config_mode_sensor_has_no_state_class(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "ausgang_15_analog_modus_mode"
        friendly_name = "Ausgang 15 (analog)  Modus (Hand/Auto)_mode"
        send_config(client, device_name, entity_name, "OutputMode", friendly_name=friendly_name)

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        self.assertEqual(topic, "homeassistant/sensor/uvr_sensor_ausgang_15_analog_modus_mode/config")
        self.assertTrue(retain)
        data = json.loads(payload)

        # Critical: Mode sensors must NEVER have state_class or unit_of_measurement
        self.assertNotIn("state_class", data)
        self.assertNotIn("unit_of_measurement", data)
        self.assertEqual(data.get("unique_id"), "uvr_ausgang_15_analog_modus_mode")

    def test_send_config_unitless_sensor_has_no_state_class(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "solstart_zaehler_startversuche"
        send_config(client, device_name, entity_name, None, friendly_name="SOLSTART Zähler Startversuche")

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        data = json.loads(payload)

        # Unitless sensors must not have state_class
        self.assertNotIn("state_class", data)
        self.assertNotIn("unit_of_measurement", data)

    def test_send_config_energy_sensor_has_total_increasing(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "wmz_solar_kilowattstunden_zaehler"
        send_config(client, device_name, entity_name, "kWh", friendly_name="WMZ SOLAR Kilowattstunden (Zähler)")

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        data = json.loads(payload)

        self.assertEqual(data.get("state_class"), "total_increasing")
        self.assertEqual(data.get("unit_of_measurement"), "kWh")
        self.assertEqual(data.get("device_class"), "energy")

    def test_send_config_temperature_sensor_has_measurement(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "t_kollektor_wert"
        send_config(client, device_name, entity_name, "°C", friendly_name="T.Kollektor Wert")

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        data = json.loads(payload)

        self.assertEqual(data.get("state_class"), "measurement")
        self.assertEqual(data.get("unit_of_measurement"), "°C")
        self.assertEqual(data.get("device_class"), "temperature")
        self.assertEqual(data.get("expire_after"), 600)

    def test_send_config_flow_rate_has_l_per_h(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "wmz_solar_durchfluss"
        send_config(client, device_name, entity_name, "l/h", friendly_name="WMZ SOLAR Durchfluss")

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        data = json.loads(payload)

        self.assertEqual(data.get("unit_of_measurement"), "l/h")
        self.assertEqual(data.get("state_class"), "measurement")
        self.assertEqual(data.get("expire_after"), 600)

    def test_send_config_irradiance_has_w_per_m2(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "solarstr_wert"
        send_config(client, device_name, entity_name, "W/m²", friendly_name="Solarstr. Wert")

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        data = json.loads(payload)

        self.assertEqual(data.get("unit_of_measurement"), "W/m²")
        self.assertEqual(data.get("device_class"), "irradiance")
        self.assertEqual(data.get("state_class"), "measurement")
        self.assertEqual(data.get("expire_after"), 600)

    def test_send_config_binary_sensor_has_no_state_class(self):
        client = FakeClient()
        device_name = "UVR"
        entity_name = "pumpe_1_status"
        send_config(client, device_name, entity_name, "switch", friendly_name="Pumpe 1 Status")

        self.assertEqual(len(client.published), 1)
        topic, payload, retain = client.published[0]
        self.assertTrue(topic.startswith("homeassistant/binary_sensor/"))
        data = json.loads(payload)

        self.assertNotIn("state_class", data)
        self.assertNotIn("unit_of_measurement", data)
        self.assertEqual(data.get("device_class"), "running")

    def test_configure_logging_sets_debug(self):
        configure_logging(True)
        logger = logging.getLogger("UVR2MQTT")
        self.assertEqual(logger.level, logging.DEBUG)
        configure_logging(False)
        self.assertEqual(logger.level, logging.INFO)


if __name__ == "__main__":
    unittest.main()

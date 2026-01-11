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

    def test_configure_logging_sets_debug(self):
        configure_logging(True)
        logger = logging.getLogger("UVR2MQTT")
        self.assertEqual(logger.level, logging.DEBUG)
        configure_logging(False)
        self.assertEqual(logger.level, logging.INFO)


if __name__ == "__main__":
    unittest.main()

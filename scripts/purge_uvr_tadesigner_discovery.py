"""List retained Home Assistant discovery topics for 'uvr_tadesigner' and delete them.

Writes nothing permanent; uses `config.json` (workspace root) or environment vars.
Run from workspace root with the same Python used for the project.
"""
import json
import time
import os
import sys
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


found = set()


def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected to broker, subscribing to homeassistant/# ...")
    client.subscribe("homeassistant/#")


def on_message(client, userdata, msg):
    # Only consider retained messages; these are the discovery payloads
    if msg.retain:
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="ignore")
        if "uvr_tadesigner" in topic:
            found.add(topic)
            print("RETAINED:", topic)


def main():
    cfg = load_config()
    broker = cfg["broker"]
    port = cfg["port"]
    user = cfg.get("user")
    password = cfg.get("password")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    if user and password:
        client.username_pw_set(user, password)
    client.connect(broker, port, keepalive=60)
    client.loop_start()

    # Collect retained discovery topics for a short time
    print("Collecting retained discovery topics for 6 seconds...")
    time.sleep(6)

    if not found:
        print("No retained discovery topics found for 'uvr_tadesigner'.")
    else:
        print("Found topics to purge:")
        for t in sorted(found):
            print("  ", t)

        # Confirm auto-delete: proceed to publish empty retained payloads
        print("Publishing empty retained payload to delete discovered topics...")
        for t in sorted(found):
            try:
                client.publish(t, payload="", retain=True)
                print("Deleted: ", t)
            except Exception as e:
                print("Failed to delete", t, e)

        # Give broker time to settle
        time.sleep(2)

        # Re-subscribe/check to confirm none remain
        found_after = set()

        def on_message_after(client, userdata, msg):
            if msg.retain and "uvr_tadesigner" in msg.topic:
                found_after.add(msg.topic)

        client.on_message = on_message_after
        client.subscribe("homeassistant/#")
        time.sleep(4)
        if found_after:
            print("Some topics still retained:")
            for t in sorted(found_after):
                print("  ", t)
        else:
            print("All uvr_tadesigner discovery topics appear removed.")

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

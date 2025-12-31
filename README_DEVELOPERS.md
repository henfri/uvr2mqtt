Developer notes — uvr2mqtt

This file contains developer-oriented details, testing commands and debugging pointers.

Running tests

```powershell
$env:PYTHONPATH = "X:\uvr"
python -m pytest -q
```

Key scripts
- `send_uvr_mqtt.py` — main sender that reads UVR and publishes MQTT discovery + states.
- `uvr.py` — parser and fetcher for XML/HTML pages from the CMI.
- `scripts/check_uvr_discovery_now.py` — lists retained discovery topics on MQTT broker.
- `scripts/publish_availability.py` — publish retained availability payload.

Debugging tips
- Run `send_uvr_mqtt.py` with `UVR_DEBUG=1` to enable DEBUG logs.
- Use `UVR_CYCLES=1` to run a single cycle for easy capture.
- If you see encoding issues (weird Â characters), check `uvr.separate()` normalization.

MQTT topics and naming
- Device id uses `sanitize_name(device_name)`; default device id is `uvr` (see `config.json`).
- Discovery topics are published to `homeassistant/<entity_type>/<deviceid>_<entity_type>_<object_id>/config` and are retained.
- State topics are `homeassistant/<entity_type>/<deviceid>/<object_id>/state` and are published non-retained.

Changing entity ids / backward compatibility
- If you change `device.name` or the sanitizer algorithm, Home Assistant may show duplicate entities. Remove old discovery retained topics from the broker and delete stale entities from HA's Entity Registry.

Packaging / requirements
- This project uses `paho-mqtt` and `beautifulsoup4` for parsing. A minimal `requirements.txt` may look like:

```
paho-mqtt
beautifulsoup4
requests
```

Contributing
- Keep parser changes minimal and add unit tests for difficult HTML/Modus parsing cases.

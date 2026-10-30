# Developer Notes — uvr2mqtt

This document provides developer-oriented details, testing instructions, and architecture pointers.

---

## Running Tests

Run the test suite from the repository root:

```bash
# Windows / Linux / macOS
python -m pytest tests/
```

Or with verbose output:

```bash
python -m pytest -v tests/
```

All 29 tests cover:
- `test_discovery_and_debug.py`: Home Assistant MQTT discovery payloads, device classes, state classes, units, and `expire_after`.
- `test_ta_designer_mapping.py`: Deterministic DIV mapping, `CMILinkObj` deferral, and canvas sensor deduplication.
- `test_modus_parsing.py` & `test_separate.py`: String normalization, degree sign cleaning, and unit parsing.
- `test_mqtt_integration.py`: MQTT connection, publication diagnostics, and mock dispatch.
- `test_fetch.py`: HTTP fetch retry handling.

---

## Core Architecture

```
uvr.py (Main Service Loop & Metrics)
  │
  ├──> uvr_fetch.py (HTTP Requests to C.M.I. .cgi pages)
  │
  ├──> uvr_parse.py (TA-Designer XML + HTML Parsing, DIV Mapping & Deduplication)
  │
  └──> uvr_mqtt.py (Home Assistant MQTT Discovery & State Dispatcher)
```

### TA-Designer HTML/XML Mapping Principles
TA-Designer exports HTML pages where DIV elements receive position IDs (`pos0`, `pos1`, ...). The parser maps these back to XML objects:
1. `Pic_Obj` elements generate no HTML DIVs and are skipped.
2. `CAN_CMI_Obj` (sensors) and `CMI_Obj` (static labels) receive sequential `pos` indices in XML document order.
3. `CMILinkObj` (navigation buttons) are deferred by TA-Designer and appended at the very end of the HTML output.
4. If a sensor with identical CAN signature appears multiple times on the same canvas (e.g. for display purposes), it is deduplicated to a single Home Assistant entity.
5. Invariant check: If the total number of expected DIVs in XML does not match the actual number of DIVs in the fetched HTML, a schema mismatch error is logged, and the cycle safely returns empty data to prevent cross-assignment of sensor values.

---

## Helper Scripts (`scripts/`)

- `check_uvr_discovery_now.py`: Connects to the MQTT broker and lists all retained UVR discovery topics.
- `publish_availability.py`: Sends a manual `online` payload to the availability topic.
- `purge_uvr_tadesigner_discovery.py`: Cleans up legacy/stale retained discovery topics on the broker.
- `build_and_push.sh`: Helper script to build and push the multi-tag Docker image (`henfri/uvr2mqtt:<version>` and `latest`).

---

## Docker Image Build

To build and tag the Docker image locally:

```bash
docker build -t henfri/uvr2mqtt:latest .
```

Or using the release helper:

```bash
./scripts/build_and_push.sh 1.2.0
```

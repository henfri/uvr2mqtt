import argparse
import json
import os
from pathlib import Path
from time import sleep
import logging
import pprint

from uvr import filter_empty_values, read_data
from uvr_mqtt import (
    build_mqtt_client,
    create_config,
    send_values,
    send_config,
    sanitize_name,
)

logger = logging.getLogger("UVR2MQTT")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Create a handler for the logger (e.g., StreamHandler to print to console)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)
logger.propagate = False


def configure_logging(debug: bool = False):
    """Configure module logger level. Call from CLI or tests."""
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def load_configs():
    """Load configuration from config.json (workspace root) or environment variables.

    Priority: config.json > environment variables > sensible defaults.
    """
    cfg_path = Path.cwd() / "config.json"
    cfg = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            logger.exception("Failed to load config.json")

    mqtt = cfg.get("mqtt", {})
    uvr = cfg.get("uvr", {})
    device = cfg.get("device", {})

    mqtt.setdefault("broker", os.environ.get("MQTT_BROKER", "192.168.177.152"))
    mqtt.setdefault("port", int(os.environ.get("MQTT_PORT", 1883)))
    mqtt.setdefault("user", os.environ.get("MQTT_USER", ""))
    mqtt.setdefault("password", os.environ.get("MQTT_PASSWORD", ""))

    uvr.setdefault("xml_filename", os.environ.get("UVR_XML", "Neu.xml"))
    uvr.setdefault("ip", os.environ.get("UVR_IP", "192.168.177.5"))
    uvr.setdefault("user", os.environ.get("UVR_USER", "user"))
    uvr.setdefault("password", os.environ.get("UVR_PASSWORD", ""))

    device_name = device.get("name", os.environ.get("DEVICE_NAME", "UVR_TADesigner"))

    # Basic validation: ensure broker present and device name
    if not mqtt.get("broker"):
        raise ValueError("MQTT broker not configured (config.json or MQTT_BROKER env)")
    if not device_name:
        raise ValueError("Device name not configured (config.json device.name or DEVICE_NAME env)")

    return mqtt, uvr, device_name



# Beispielaufruf der Funktion
#send_config(mqtt_client,"bedroom", "temp1", "temperature")
#send_config(mqtt_client,"bedroom", "temp2", "temperature")
#send_config(mqtt_client,"bedroom", "temp1", "humidity")


def create_config(mqtt_client, mqtt_device_name, values):
    for entry in values:
        for name, data in entry.items():
            entity_name  = sanitize_name(name)
            # pass the original/prettified label as the friendly name
            send_config(mqtt_client, mqtt_device_name, entity_name, data["unit"], friendly_name=name)
            

def get_device_class(unit,t):

    #(°C|Â°C|l/h|W/m²|W/m°²|%|kWh|kW|min|AUS|AN|ON|OFF|AUTO|EIN)'
    
    device_class=None
    entity_type=None
    unit_of_measurement=None


    if unit == None:
        device_class="None"  
        entity_type="sensor" # Geändert von "number" zu "sensor"
        unit_of_measurement="None" # Oder eine passendere Einheit, falls bekannt
    elif unit.lower() == "none":
        device_class="None"  
        entity_type="sensor" # Geändert von "number" zu "sensor"
        unit_of_measurement="None" # Oder eine passendere Einheit
    elif unit == "C" or unit == "°C":
        device_class= "temperature"
        entity_type="sensor"
        unit_of_measurement="°C"
    elif unit == "l/h":
        device_class= "water"
        entity_type="sensor"
        unit_of_measurement="L"
    elif unit == "W/m2" or unit=="W/m°²":
        device_class= "power"
        entity_type="sensor"      
        unit_of_measurement="W"  
    elif unit == "kWh":
        device_class= "energy"
        entity_type="sensor"
        unit_of_measurement="kWh"
    elif unit == "kW":
        device_class= "power"  
        entity_type="sensor"  
        unit_of_measurement="kW"
    elif unit == "min":
        device_class= "duration"  
        entity_type="sensor"  
        unit_of_measurement="min"
    elif unit == "%":
        device_class=None
        entity_type="sensor"
        unit_of_measurement="%"
    elif unit == "switch":
        device_class= "running"
        entity_type="binary_sensor"
        unit_of_measurement="On/Off" 
    elif unit == "OutputMode":
        device_class = None
        entity_type = "sensor"
        unit_of_measurement = None
    elif unit == "":
        device_class= "running"
        entity_type="binary_sensor"
        unit_of_measurement="On/Off" 
    else:
        # Füge weitere Bedingungen hinzu, wenn andere Geräteklassen benötigt werden
        device_class= "None"
        entity_type="sensor"
    if device_class=="None":
        logger.debug("none for device {} with unit {}".format(t,unit)) 
    return device_class,entity_type,unit_of_measurement



# MQTT helper functions are provided by `uvr_mqtt` and re-exported at module level.




werte =[{
 'VERGL. 2 Vergleichswert a234': {'value': 60.0, 'unit': '°C'},
 'VERGL. 2 Vergleichswert b234': {'value': 55.0, 'unit': '°C'},
 'DurchflSolar  Wert234': {'value': 7.0, 'unit': 'l/h'},
 'Solarstr. Wert234': {'value': 9.0, 'unit': 'W/m°²'}
 }];
 

# Beispielaufruf der Funktion
alle_werte =[{'VERGL. 2 Vergleichswert a': {'value': 59.8, 'unit': '°C'},
 'VERGL. 2 Vergleichswert b': {'value': 50.0, 'unit': '°C'},
 'DurchflSolar  Wert': {'value': 0.0, 'unit': 'l/h'},
 'Solarstr. Wert': {'value': 14592.0, 'unit': 'W/m°²'},

 'VERGL. 2 Status Wa < Wb + diff': {'value': 1.0, 'unit': 'switch'},
 'SOLAR 1 Freigabe Solarregelung': {'value': 0.0, 'unit': 'switch'},
 'SOLAR 1 Kollektortemperatur': {'value': 29.8, 'unit': '°C'},
 'SOLAR 1 Referenztemperatur': {'value': 30.3, 'unit': '°C'},
 'SOLAR 1 Status Solarkreis': {'value': 0.0, 'unit': 'switch'},
 'SOLAR 2 Freigabe Solarregelung': {'value': 1.0, 'unit': 'switch'},
 'SOLAR 2 Kollektortemperatur': {'value': 6.9, 'unit': '°C'},
 'SOLAR 2 Referenztemperatur': {'value': 27.5, 'unit': '°C'},
 'SOLAR 2 Status Solarkreis': {'value': 0.0, 'unit': 'switch'},
 'PID SOLAR 1 Freigabe PID-Regelung': {'value': 0.0, 'unit': 'switch'},
 'PID SOLAR 1 Temperatur Absolutwertreg.': {'value': 6.9, 'unit': '°C'},
 'PID SOLAR 1 Sollwert Absolutwertreg.': {'value': 50.0, 'unit': '°C'},
 'PID SOLAR 1 Temperatur (+) Differenzreg.': {'value': 20.7, 'unit': '°C'},
 'PID SOLAR 1 Temperatur (-) Differenzreg.': {'value': 30.3, 'unit': '°C'},
 'PID SOLAR 1 Aktivierungstemperatur Ereignisreg.': {'value': 6.9, 'unit': '°C'},
 'PID SOLAR 1 Regeltemperatur Ereignisreg.': {'value': 6.9, 'unit': '°C'},
 'PID SOLAR 1 aktuelle Stellgröße': {'value': 0.0, 'unit': 'switch'},
 'PID SOLAR 2 Freigabe PID-Regelung': {'value': 0.0, 'unit': 'switch'},
 'PID SOLAR 2 Temperatur (+) Differenzreg.': {'value': 20.7, 'unit': '°C'},
 'PID SOLAR 2 Temperatur (-) Differenzreg.': {'value': 23.0, 'unit': '°C'},
 'PID SOLAR 2 Aktivierungstemperatur Ereignisreg.': {'value': 6.9, 'unit': '°C'},
 'PID SOLAR 2 Regeltemperatur Ereignisreg.': {'value': 6.9, 'unit': '°C'},
 'PID SOLAR 2 aktuelle Stellgröße': {'value': 0.0, 'unit': 'switch'},
 'SOLVORR. Laufzeit': {'value': 20.0, 'unit': 'min'},
 'SOLVORR. Wartezeit': {'value': 5.0, 'unit': 'min'},
 'SOLVORR. Status Spülvorgang': {'value': 0.0, 'unit': 'switch'},
 'SOLSTART Bezugstemperatur': {'value': 6.9, 'unit': '°C'},
 'SOLSTART Zähler Startversuche': {'value': 11.0, 'unit': None},
 'SOLSTART Zähler erfolglose Startversuche': {'value': 11.0, 'unit': None},
 'SOLSTART Zähler Startversuche seit letztem Lauf': {'value': 11.0, 'unit': None},
 'SOLSTART Status Spülvorgang': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Analogeingang 1 Wert': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Analogeingang 2 Wert': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Analogeingang 3 Wert': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Analogeingang 4 Wert': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Analogeingang 5 Wert': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Analogeingang 6 Wert': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 1 Ergebnis': {'value': 0.0, 'unit': None},
 'Ausgang 15 (analog)  Modus (Hand/Auto)': {'value': 2.0, 'unit': 'OutputMode'},
 'Umsch_Solar   Zustand (Ein/Aus)': {'value': 1.0, 'unit': 'switch'},
 'Umsch_Solar   1 Digitaleingang 1 Status': {'value': 0.0, 'unit': 'switch'},
 'Umsch_Solar   1 Digitaleingang 2 Status': {'value': 0.0, 'unit': 'switch'},
 'Umsch_Solar   1 Digitaleingang 3 Status': {'value': 0.0, 'unit': 'switch'},
 'Umsch_Solar   1 Status Ergebnis': {'value': 0.0, 'unit': 'switch'},
 'KUEHLFKT. 1 Freigabe Kühlfunktion': {'value': 0.0, 'unit': 'switch'},
 'KUEHLFKT. 1 Referenztemperatur': {'value': 27.6, 'unit': '°C'},
 'KUEHLFKT. 1 Stellgröße Drehzahlstufe': {'value': 10.0, 'unit': None},
 'VERZG. Status Timerausgang': {'value': 0.0, 'unit': 'switch'},
 'VERZG. Triggereingang': {'value': 0.0, 'unit': 'switch'},
 'Uebertemp.  Set-Eingang Meldung': {'value': 0.0, 'unit': 'switch'},
 'Uebertemp.  Reset-Eingang Meldung': {'value': 1.0, 'unit': 'switch'},
 'Uebertemp.  Meldung aktiv': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) 3 Analogeingang 1 Wert': {'value': 20.7, 'unit': '°C'},
 'MAX(An) 3 Analogeingang 2 Wert': {'value': 6.9, 'unit': '°C'},
 'MAX(An) 3 Ergebnis': {'value': 20.7, 'unit': '°C'},
 'ANALOG 9 Analogeingang 3 Wert': {'value': 0.0, 'unit': None},
 'ANALOG 9 Ergebnis': {'value': 0.0, 'unit': None},
 'MAX(An) Analogeingang 1 Wert+Offset ': {'value': 26.5, 'unit': '°C'},
 'MAX(An) Analogeingang 2 Wert+Offset ': {'value': 5.0, 'unit': '°C'},
 'C.M.I. 2': {'value': 1.0, 'unit': 'switch'},
 'FBHEIZ. 1 Vorlauftemperatur': {'value': 25.7, 'unit': '°C'},
 'FBHEIZ. 1 Außentemperatur': {'value': 8.8, 'unit': '°C'},
 'FBHEIZ. 1 Raumtemperatur': {'value': 0.0, 'unit': '°C'},
 'FBHEIZ. 1 Vorlaufsolltemperatur': {'value': 26.5, 'unit': '°C'},
 'FBHEIZ. 1 Status Pumpe': {'value': 1.0, 'unit': 'switch'},
 'FBHEIZ. 1 Status Mischer': {'value': 0.0, 'unit': 'switch'},
 'FBHEIZ. 1 Vorlauftemp. bei + 10 °C': {'value': 26.0, 'unit': '°C'},
 'FBHEIZ. 1 Vorlauftemp. bei - 20 °C oder Steilheit abhängig vom Heizkurvenmodus': {'value': 36.0, 'unit': '°C'},
 'WW_ANF. effektiver Sollwert': {'value': 50.0, 'unit': '°C'},
 'WW_ANF. Solltemperatur': {'value': 57.0, 'unit': '°C'},
 'C.M.I. 3': {'value': 10.0, 'unit': '°C'},
 'C.M.I. 1': {'value': 20.0, 'unit': '°C'},
 'Text': {'value': 60.1, 'unit': '°C'},
 'T.Warmwasser  Freigabe Anf. Heizung': {'value': 30.4, 'unit': '°C'},
 'T.Warmwasser  Anforderungstemperatur': {'value': 0.0, 'unit': 'switch'},
 'T.Warmwasser  Abschalttemperatur': {'value': 0.2, 'unit': '%'},
 'T.Warmwasser  Status Anforderung': {'value': 1.0, 'unit': 'switch'},
 'T.Warmwasser  Unterdeckung Ökobetrieb': {'value': 29.8, 'unit': '°C'},
 'HZ_ANF. Freigabe Anf. Heizung': {'value': 27.6, 'unit': '°C'},
 'HZ_ANF. Anforderungstemperatur': {'value': 26.5, 'unit': '°C'},
 'HZ_ANF. Abschalttemperatur': {'value': 5.0, 'unit': '°C'},
 'HZ_ANF. Solltemp. Anforderung': {'value': 26.5, 'unit': '°C'},
 'MAX(An) Analogeingang 2 Wert+Offset ': {'value': 26.5, 'unit': '°C'},
 'MAX(An) Analogeingang 1 Wert+Offset ': {'value': 0.0, 'unit': 'switch'},
 'MAX(An) Ergebnis': {'value': 0.0, 'unit': 'switch'},
 'ODER Digitaleingang 1 Status': {'value': 0.0, 'unit': 'switch'},
 'ODER Digitaleingang 2 Status': {'value': 0.0, 'unit': 'switch'},
 'ODER Digitaleingang 3 Status': {'value': 0.0, 'unit': 'switch'},
 'ODER Status Ergebnis': {'value': 0.0, 'unit': 'switch'},
 'UND Status Ergebnis': {'value': 1.0, 'unit': 'switch'},
 'UND Digitaleingang 1 Status': {'value': 0.0, 'unit': 'switch'},
 'UND Digitaleingang 2 Status': {'value': 0.0, 'unit': 'switch'},
 'Anf.Kessel Zustand (Ein/Aus)': {'value': 0.0, 'unit': 'switch'},
 'T.Kollektor Wert': {'value': 6.9, 'unit': '°C'},
 'T.Speicher 1 Wert': {'value': 60.0, 'unit': '°C'},
 'T.Speicher 2 Wert': {'value': 30.4, 'unit': '°C'},
 'T.Speicher 3 Wert': {'value': 27.6, 'unit': '°C'},
 'T.Speicher 4 Wert': {'value': 29.8, 'unit': '°C'},
 'T.Kollekt.VL Wert': {'value': 20.8, 'unit': '°C'},
 'T.Kollekt.RL Wert': {'value': 23.0, 'unit': '°C'},
 'Temp.Aussen Wert': {'value': 8.9, 'unit': '°C'},
 'DurchflSolar  Wert': {'value': 0.0, 'unit': 'l/h'},
 'Solarstr. Wert': {'value': 14592.0, 'unit': 'W/m°²'},
 'Pumpe-Hzkr 1 Zustand (Ein/Aus)': {'value': 1.0, 'unit': 'switch'},
 'Pumpe-Hzkr 2 Zustand (Ein/Aus)': {'value': 0.0, 'unit': 'switch'},
 'Umsch_Solar   Zustand (Ein/Aus)': {'value': 1.0, 'unit': 'switch'},
 'Misch.Hzkr 1 Zustand (Ein/Aus)': {'value': 0.0, 'unit': 'switch'},
 'Ausgang 15 (analog)  Modus (Hand/Auto)': {'value': 2.0, 'unit': 'switch'},
 'Anf.Kessel Zustand (Ein/Aus)': {'value': 0.0, 'unit': 'switch'},
 'NW-Eingang analog 8  Wert': {'value': 46.7, 'unit': '°C'},
 'NW-Eingang analog 9  Wert': {'value': 23.3, 'unit': '°C'},
 'NW-Eingang analog 7  Wert': {'value': 0.0, 'unit': 'l/h'},
 'NW-Eingang analog 5  Wert': {'value': 25.7, 'unit': '°C'},
 'NW-Eingang analog 6  Wert': {'value': 24.7, 'unit': '°C'},
 'NW-Eingang analog 4  Wert': {'value': 334.0, 'unit': 'l/h'},
 'WMZ SOLAR Vorlauftemperatur': {'value': 20.8, 'unit': '°C'},
 'WMZ SOLAR Rücklauftemperatur': {'value': 23.0, 'unit': '°C'},
 'WMZ SOLAR Durchfluss': {'value': 0.0, 'unit': 'l/h'},
 'WMZ SOLAR Momentanleistung': {'value': 0.0, 'unit': 'kW'},
 'WMZ SOLAR Kilowattstunden (Zähler)': {'value': 11.2, 'unit': 'kWh'},
 'WMZ Pellets   Vorlauftemperatur': {'value': 46.7, 'unit': '°C'},
 'WMZ Pellets   Rücklauftemperatur': {'value': 23.3, 'unit': '°C'},
 'WMZ Pellets   Durchfluss': {'value': 0.0, 'unit': 'l/h'},
 'WMZ Pellets   Momentanleistung': {'value': 0.0, 'unit': 'kW'},
 'WMZ Pellets   Kilowattstunden (Zähler)': {'value': 89.1, 'unit': 'kWh'},
 'WMZ HZK. Vorlauftemperatur': {'value': 25.7, 'unit': '°C'},
 'WMZ HZK. Rücklauftemperatur': {'value': 24.7, 'unit': '°C'},
 'WMZ HZK. Durchfluss': {'value': 334.0, 'unit': 'l/h'},
 'WMZ HZK. Momentanleistung': {'value': 0.37, 'unit': 'kW'},
 'WMZ HZK. Kilowattstunden (Zähler)': {'value': 24.1, 'unit': 'kWh'}}]

# load config in place (keep original load_configs in main file for now)
mqtt_config, uvr_config, device_name = load_configs()

# Enable debug logging when requested by environment (useful for foreground debugging)
if os.environ.get("UVR_DEBUG", "").lower() in ("1", "true", "yes"):
    configure_logging(True)
    logger.info("Debug logging enabled via UVR_DEBUG environment variable")

# Optional: limit number of polling cycles for foreground debug runs.
# Set UVR_CYCLES=1 to run one cycle and exit.
try:
    UVR_CYCLES = int(os.environ.get("UVR_CYCLES", "0"))
except Exception:
    UVR_CYCLES = 0



# Verbindung zum MQTT-Broker herstellen
if __name__ == '__main__':
    try:
        mqtt_client = build_mqtt_client(mqtt_config)
    except Exception as e:
        logger.exception("Failed to establish MQTT connection: %s", e)
        raise SystemExit(1)

    # use device_name loaded from config.json (set earlier by load_configs())

    # create_config(mqtt_client, device_name, alle_werte)
    # send_values(mqtt_client, device_name, alle_werte)

    page_values = filter_empty_values(read_data(uvr_config))

    # publish discovery configs
    create_config(mqtt_client, device_name, page_values)
    sleep(5)

    device_id = sanitize_name(device_name)
    availability_topic = f"homeassistant/{device_id}/availability"
    # publish initial availability retained
    mqtt_client.publish(availability_topic, "online", retain=True)

    try:
        cycle_count = 0
        while True:
            try:
                # Check MQTT connection status and attempt reconnect if needed
                if not check_mqtt_connection(mqtt_client):
                    logger.error("MQTT connection unavailable; skipping cycle")
                    mqtt_client.publish(availability_topic, "offline", retain=True)
                    time.sleep(30)
                    continue
                # Read and filter UVR data
                page_values = filter_empty_values(read_data(uvr_config))

                # Send UVR data via MQTT
                send_values(mqtt_client, device_name, page_values)

                logger.info("Completed one cycle.")
                cycle_count += 1
                if UVR_CYCLES > 0 and cycle_count >= UVR_CYCLES:
                    logger.info("Reached UVR_CYCLES=%s, exiting loop.", UVR_CYCLES)
                    break
            except Exception as e:
                logger.exception("Error during cycle: %s", e)
            # wait 60 seconds before next poll
            sleep(60)
    except KeyboardInterrupt:
        logger.info("Interrupted, marking offline and exiting")
        mqtt_client.publish(availability_topic, "offline", retain=True)
        mqtt_client.loop_stop()
        try:
            mqtt_client.disconnect()
        except Exception:
            pass


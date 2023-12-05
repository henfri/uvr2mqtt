import json
import paho.mqtt.client as mqtt
import re
import logging
from time import sleep
from uvr import filter_empty_values
from uvr import read_data

logger = logging.getLogger("UVR2MQTT")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Create a handler for the logger (e.g., StreamHandler to print to console)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)
logger.propagate = False

def send_config(mqtt_client, mqtt_device_name,entity_name, unit):
    device_class, entity_type, unit_of_measurement = get_device_class(unit)
    config_topic = f"{device_name}_{entity_type}_{entity_name}"
    config_payload = {
        "device_class": device_class,
        "name": entity_name,
        "state_topic": f"homeassistant/{entity_type}/{device_name}/state",
        "unit_of_measurement": unit_of_measurement,
        "value_template": f"{{{{ value_json.{entity_name.lower()}}}}}",
        "unique_id": f"{config_topic.lower()}xxxzzzaaa",
        "device": {
            "identifiers": [f"{mqtt_device_name.lower()}xxxzzzaaa"],
            "name": mqtt_device_name.capitalize()
        }
    }

    mqtt_message = json.dumps(config_payload)
    mqtt_topic = f"homeassistant/sensor/{config_topic}/config"

    # Nachricht senden
    #print(mqtt_topic)
    #print(mqtt_message)
    mqtt_client.publish(mqtt_topic, mqtt_message)


def send_values(client, device_name, values):
    state_topic = f"homeassistant/sensor/{device_name}/state"

    payload = {}
    for entry in values:
        for sensor_name, data in entry.items():
            payload[sanitize_name(sensor_name).lower()] = float(data['value'])

    mqtt_message = json.dumps(payload)

    # Nachricht senden
    client.publish(state_topic, mqtt_message)
    #print(state_topic)
    #print(mqtt_message)

# Beispielaufruf der Funktion
#send_config(mqtt_client,"bedroom", "temp1", "temperature")
#send_config(mqtt_client,"bedroom", "temp2", "temperature")
#send_config(mqtt_client,"bedroom", "temp1", "humidity")


def create_config(mqtt_client, mqtt_device_name, values):
    for entry in values:
        for name, data in entry.items():
            entity_name  = sanitize_name(name)

            send_config(mqtt_client, mqtt_device_name,entity_name, data["unit"])
            

def get_device_class(unit):

    #(°C|Â°C|l/h|W/m²|W/m°²|%|kWh|kW|min|AUS|AN|ON|OFF|AUTO|EIN)'
    
    device_class=None
    entity_type=None
    unit_of_measurement=None

    if unit == "C" or unit == "°C":
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
    elif unit == "switch":
        device_class= "None"
        entity_type="binary_sensor"
    elif unit == "":
        device_class= "None"
        entity_type="binary_sensor"  
    else:
        # Füge weitere Bedingungen hinzu, wenn andere Geräteklassen benötigt werden
        device_class= "None"
        entity_type="sensor" 
    return device_class,entity_type,unit_of_measurement



def sanitize_name(name):
    # Erlaube nur Buchstaben, Zahlen, Unterstriche und Bindestriche
    cleaned_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return cleaned_name.lower()


def check_mqtt_connection(client):
    """Check MQTT connection status."""
    if client.is_connected():
        logger.debug("MQTT Connection is active.")
    else:
        logger.warning("MQTT Connection lost. Reconnecting...")
        client.reconnect()
        sleep(2)
        if client.is_connected():
            logger.info("MQTT Connection is active after reconnect")
        else:
            logger.error("MQTT Reconnection failed.")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.debug("Connected to MQTT broker")
    else:
        logger.warning(f"Connection to MQTT broker failed with result code {rc}")

def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected from MQTT broker with result code {rc}")




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
 'Ausgang 15 (analog)  Modus (Hand/Auto)': {'value': 2.0, 'unit': 'switch'},
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

mqtt_config = {
    "broker": "192.168.177.3",
    "port": 1883,
    "user": "user",  
    "password": "x" 
}

uvr_config = {
    "xml_filename": "Neu.xml",
    "ip": "192.168.177.5",
    "user": "user",  
    "password": "123" 
}



# Verbindung zum MQTT-Broker herstellen
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
#mqtt_client.on_log = lambda client, userdata, level, buf: logger.debug(buf)
if mqtt_config["user"] and mqtt_config["password"]:
    mqtt_client.username_pw_set(mqtt_config["user"], mqtt_config["password"])
mqtt_client.connect(mqtt_config["broker"], mqtt_config["port"], keepalive=300)
if mqtt_client.is_connected():
   logger.debug("MQTT Connection is active.")
mqtt_client.loop_start()



device_name  = "uvr1611_TA-Designer"

#create_config(mqtt_client, device_name, alle_werte)
#send_values(mqtt_client, device_name, alle_werte)


page_values = filter_empty_values(read_data(uvr_config))

create_config(mqtt_client, device_name, alle_werte)
sleep(5) 

while True:
    try:
        # Check MQTT connection status
        check_mqtt_connection(mqtt_client)
        # Read and filter UVR data
        page_values = filter_empty_values(read_data(uvr_config))

        # Send UVR data via MQTT
        send_values(mqtt_client, device_name, page_values)

        logger.warning("Sleeping for 60 seconds...")
        sleep(6)


    except Exception as e:
        logger.error(f"An error occurred: {e}")
        # Add more specific exception handling if needed
  

# uvr2mqtt
Tool to read all available data from UVR to MQTT including Homeassistant Auto-Discovery 

# Introduction
With a little help of the TA-Support, I have developed a way to read also Variables from within Logic Blocks and transfer them to HA.
As an example, for a PID Block, these Values are available:

All of this runs in a python script with little dependencies.

# Configuration
The only thing you need to do is to create a Schema with TA-Designer. We need the resulting xml (and it must be uploaded to CMI/BLNet).
The other prerequisite is an MQTT Broker and the MQTT Integration in HomeAssistant (in case the the Data shall become available in HomeAssistant).

Then, the only configuration is this (send_uvr_mqtt.py):
```
mqtt_config = {
    "broker": "192.168.177.3",
    "port": 1883,
    "user": "user",
    "password": "pass" 
}

uvr_config = {
    "xml_filename": "Neu.xml",
    "ip": "192.168.177.5",
    "user": "user", 
    "password": "pass"  
}
```

# Testing
1) Check that your TA-Designer / CMI Schema is working by accessing
http://cmi/schema.html

2) (optional)
edit the line page_values=_read_data("Neu.xml","192.168.177.5","user","123")` 
run uvr.py

The data available from your schema should be shown on the commandline

# Running
run ´send_uvr_mqtt.py´ 
It will poll information from CMI every 60s.

# HomeAssistant Integration
In HA, the result is an MQTT Device that has the different Sensors as Entities. As soon as the XML is updated (and the script restarted) the new Entities are created automatically. No configuration in HA needed (auto-discovery)

import logging
import pprint
import re
from html.parser import HTMLParser
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import requests
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def separate(s):
    value = None
    s = s.lstrip('\n')  # Remove newline characters at the beginning
    if "-" in s:
        logger.debug("Negativ {}".format(s))
    
    unit_pattern = r'(°C|Â°C|l/h|W/m²|W/m°²|%|kWh|kW|min|AUS|AN|ON|OFF|AUTO|EIN)'
    numeric_parts = re.findall(r'-?\s*[\d.,]+', s)

    for part in numeric_parts:
        try:
            float_value = float(part.replace(' ', '') )
            value = str(float_value)
            break  # Break on the first valid numeric value found
        except ValueError:
            continue  # Continue to the next part if conversion to float fails
    
    # Extracting the unit
    unit_match = re.search(unit_pattern, s,flags=re.IGNORECASE)
    unit = unit_match.group().strip() if unit_match else None
    if isinstance(unit, str):
        if unit.upper() in ["AN", "ON", "EIN"]:
            unit="switch"
            value=1
        if unit.upper() in ["AUS", "OFF"]:
            unit="switch"  
            value=0
        if unit.upper() in ["AUTO"]:
            unit="OutputMode"  
            value=1
        if unit.upper() in ["HAND"]:
            unit="OutputMode"  
            value=0
        if unit.upper() in ["W/m²","W/m°²"]:
            unit="power"
        
    if value is not None: 
        try:
            value = float(value)
        except ValueError:
            # Code für den Fall, dass die Umwandlung fehlschlägt
            logger.error("Die Umwandlung von 'value' in eine Zahl ist fehlgeschlagen.")
            value=None
        
    if unit=="%":
        value=float(value)/100.0    
    
#    if unit== None:
#        print("Unit none for |{}|. Value is |{}|".format(s, value))          
    
    return value, unit


class MyHTMLParser(HTMLParser):
    def __init__(self, log):
        super().__init__()
        self.log = log
        self.id = []
        self.data = []
        self.tag = None
        self.temp = []
        self.dict = {}
        self.curr_id = ""

    def handle_starttag(self, tag, attrs):
        if tag != 'div':
            self.log.debug('no div')
            return
        self.tag = tag
        self.temp = []
        for attr in attrs:
            v = attr[1].split('pos')
            if len(v) > 1:
                idx = int(v[1])
                self.id.append(idx)
                self.curr_id = idx
                self.log.debug('index {}'.format(idx))

    def handle_data(self, data):
        if self.tag == 'div':
            self.log.debug('div with data {} for id {}'.format(data, self.curr_id))
            self.temp.append(data)
        elif self.tag == 'a':
            self.log.debug('a with data {} for id {}'.format(data, self.curr_id))
            self.temp.append(data)
        else:
            self.log.debug('Tag is neither a or div for id {}'.format(data, self.curr_id))


    def handle_endtag(self, tag):
        if tag == 'div':
            s = "".join(self.temp)
            self.log.debug('Handle endtag {} for id {}'.format(s, self.curr_id))
            s = s.replace(',', '.').replace('Â', '°').encode('utf-8').decode('utf-8')
            #s = s.replace('AUS', '0').replace('EIN', '1').replace('OFF', '0').replace('ON', '1')
            self.log.debug('closing tag and saving{} for id {}'.format(s, self.curr_id))
            if True:
                value_part, unit = separate(s)
                
                # Store values and units separately
                self.data.append({'value': value_part, 'unit': unit})
                self.dict[self.curr_id] = {'value': value_part, 'unit': unit}

            #except Exception as e:
            #    self.log.warning('Exception {} for value |{}|. String was|{}|'.format(e, w, s))


def fetch(url, username, password, timeout=10):
    try:
        res = requests.get(url, auth=(username, password), timeout=timeout).text
        logger.debug("########request")
        logger.debug(res)
        logger.debug(type(res))
        logger.debug("########request")
        return res
    except requests.Timeout:
        logger.error(f"Request to {url} timed out after {timeout} seconds.")
        # Handle the timeout error as needed
        return None
    except requests.RequestException as e:
        logger.error(f"An error occurred during the request: {e}")
        # Handle other request exceptions as needed
        return None


def read_xml(root, Seite):
    beschreibung = []
    id_conf = []
    xml_dict = {}
    idx = 0
    for i in range(0, len(root.findall('./Seiten/Seite_{}/Objekte/*'.format(Seite)))):
        b = root.findall('./Seiten/Seite_{}/Objekte/Objekt_{}'.format(Seite, i))[-1].get('Bezeichnung').split(': ')[
            -1]
        typ = root.findall('./Seiten/Seite_{}/Objekte/Objekt_{}'.format(Seite, i))[-1].get('Objekt_Typ')
        if "Pic_Obj" not in typ:
            beschreibung.append(b)
            id_conf.append(idx)
            xml_dict[b] = idx
            idx += 1

    logger.debug('[UVR] Available Strings in xml auf Seite {}:'.format(Seite))
    logger.debug(beschreibung)
    return beschreibung, id_conf, xml_dict


def read_html(ip, Seite, username, password):
    url = 'http://{}/schematic_files/{}.cgi'.format(ip, Seite + 1)
    logger.debug('Handling url {}'.format(url))
    h = fetch(url, username, password)
    return h


def combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html):
    parser = MyHTMLParser(logging)
    parser.feed(html)

    id_res = parser.id
    content = parser.data
    html_dict = parser.dict
    logger.debug("[UVR] HTML-dict {0}".format(pprint.pformat(html_dict)))
    logger.debug("[UVR] XML-dict {0}".format(pprint.pformat(xml_dict)))

    logger.debug('[UVR] TA-XML id_conf {0}'.format(pprint.pformat(id_conf)))
    logger.debug('[UVR] TA-XML Beschreibung {0}'.format(pprint.pformat(beschreibung)))
    logger.debug('[UVR] HTML id_res {0}'.format(pprint.pformat(id_res)))
    logger.debug('[UVR] HTML content {0}'.format(pprint.pformat(content)))
    if len(content) != len(id_conf):
        logger.error('[UVR] ERROR. Länge XML {} und HTML {} sind ungleich'.format(len(id_conf), len(content))) 
        exit()

    combined_dict = {}
    for key, value in xml_dict.items():
        try:
            combined_dict[key] = {'value': html_dict[value]['value'], 'unit': html_dict[value]['unit']}
        except Exception as err:
            logger.exception("[UVR] Error matching HTML and Item: {0}, {1}. Exception".format(key, value), exc_info=True)

    logger.debug("[UVR] Combined-dict {0}".format(pprint.pformat(combined_dict)))
    return combined_dict.copy()



def extract_entity_data(results, unit=None):
    if unit is not None:
        filtered_data = {key: value['value'] for key, value in results.items() if value.get('unit') == unit}
        return filtered_data
    else:
        entity_data = {key: value['value'] for key, value in results.items()}
        return entity_data


def _read_data(xml,ip, user, password):
    # read the configuration-----------------------------------------------------------------------------
    tree = ET.parse(xml)
    root = tree.getroot()
    Seiten = range(0, len(root.findall('./Seiten/')))
    combined_dict = []

    for Seite in Seiten:
        # ----------read the page in xml-----------------------------
        beschreibung, id_conf, xml_dict = read_xml(root, Seite)
        # ----------read the response-------------------------------
        html = read_html(ip, Seite, user, password)
        now = datetime.now()
        # with open("/usr/local/smarthome/var/log/"+now.strftime("%Y%m%d-%H%M%S")+"uvr.log", "w") as text_file:
        #    print(html, file=text_file)
        # ----------combine xml and html----------------------------
        if html is not None and html is not False:
            combined_dict.append(combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html))
        else:
            logger.error('[UVR] html could not be loaded. html is {0}'.format(html))

    return combined_dict


def read_data(credentials):
    return _read_data(credentials['xml_filename'], credentials['ip'], credentials['user'], credentials['password'])


def print_data(combined_dict, filter):
    # Print the values at the end
    for page_values in combined_dict:
        logger.debug("[UVR] Page values: {0}".format(pprint.pformat(page_values)))
        logger.debug(extract_entity_data(page_values,unit=filter))




def filter_empty_values(data):
    filtered_data = [{key: value for key, value in entry.items() if value['value'] is not None} for entry in data]
    return filtered_data


if __name__ == "__main__":
    page_values=_read_data("Neu.xml","192.168.177.5","user","gast123")

    # Beispielaufruf
    page_values = filter_empty_values(page_values)

    #print_data(page_values, 'C')
    print(page_values)
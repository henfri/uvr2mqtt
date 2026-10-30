import logging
import pprint
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    if raw_unit is None:
        return None
    u = str(raw_unit).strip()
    u_upper = u.upper()
    if u_upper in ("AN", "ON", "EIN", "AUS", "OFF"):
        return "switch"
    if u_upper in ("AUTO", "HAND"):
        return "OutputMode"
    if u_upper in ("W/M²", "W/M°²", "W/M2", "W/M\u00b2"):
        return "W/m²"
    if u_upper == "KW":
        return "kW"
    if u_upper == "KWH":
        return "kWh"
    if u_upper in ("L/H",):
        return "l/h"
    if u_upper == "%":
        return "%"
    if u_upper in ("°C", "C", "Â°C"):
        return "°C"
    return u


def separate(s: Any) -> Tuple[Optional[float], Optional[str]]:
    if s is None:
        return None, None
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = s.replace('\xa0', ' ').replace('Â', '°')
    s = s.replace('\u2212', '-')  # normalize unicode minus to ASCII
    s = re.sub(r'([+-])\s+(?=\d)', r'\1', s)  # remove spaces between sign and digits
    s = s.replace(',', '.')
    numeric_parts = re.findall(r'[+-]?\d+(?:\.\d+)?', s)
    value = None
    for part in numeric_parts:
        try:
            value = float(part)
            break
        except ValueError:
            continue
    unit_pattern = r'(°C|Â°C|l/h|W/m²|W/m°²|%|kWh|kW|min|AUS|AN|ON|OFF|AUTO|EIN|C)'
    unit_match = re.search(unit_pattern, s, flags=re.IGNORECASE)
    raw_unit = unit_match.group().strip() if unit_match else None
    unit = normalize_unit(raw_unit)
    if unit == 'switch' and value is None:
        if re.search(r'\b(AN|ON|EIN)\b', s, flags=re.IGNORECASE):
            value = 1.0
        elif re.search(r'\b(AUS|OFF)\b', s, flags=re.IGNORECASE):
            value = 0.0
    return value, unit


class MyHTMLParser(HTMLParser):
    def __init__(self, log: logging.Logger):
        super().__init__()
        self.log = log
        self.id: List[int] = []
        self.data: Dict[int, str] = {}
        self.tag = None
        self.temp: List[str] = []
        self.dict: Dict[int, Dict[str, Any]] = {}
        self.curr_id: Optional[int] = None

    def handle_starttag(self, tag, attrs):
        if tag != 'div':
            return
        self.tag = tag
        self.temp = []
        for attr in attrs:
            v = attr[1].split('pos')
            if len(v) > 1:
                idx = int(v[1])
                self.id.append(idx)
                self.curr_id = idx

    def handle_data(self, data):
        if self.tag == 'div' or self.tag == 'a':
            self.temp.append(data)

    def handle_endtag(self, tag):
        if tag == 'div':
            s = "".join(self.temp)
            s = s.replace(',', '.').replace('Â', '°')
            value_part, unit = separate(s)
            if self.curr_id is not None:
                self.data[self.curr_id] = s
                self.dict[self.curr_id] = {'value': value_part, 'unit': unit}


def read_xml(root: ET.Element, Seite: int) -> Tuple[List[str], List[int], Dict[str, int]]:
    beschreibung: List[str] = []
    xml_dict: Dict[str, int] = {}
    seen_names: Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]] = {}

    objs = root.findall(f'./Seiten/Seite_{Seite}/Objekte/*')

    # 1. Deterministic TA-Designer HTML DIV mapping:
    # - Pic_Obj generate no DIVs.
    # - CAN_CMI_Obj and CMI_Obj receive sequential pos IDs (pos0, pos1, ...) in XML order.
    # - CMILinkObj buttons are deferred to the very end of the HTML by TA-Designer.
    pos_mapping: Dict[ET.Element, int] = {}
    pos_idx = 0
    links: List[ET.Element] = []

    for node in objs:
        typ = node.get('Objekt_Typ')
        if typ == 'Pic_Obj':
            continue
        elif typ == 'CMILinkObj':
            links.append(node)
        else:
            pos_mapping[node] = pos_idx
            pos_idx += 1

    for node in links:
        pos_mapping[node] = pos_idx
        pos_idx += 1

    total_divs = pos_idx
    id_conf: List[int] = list(range(total_divs))

    # 2. Extract valid sensors (only CAN_CMI_Obj are sensors for Home Assistant)
    for node in objs:
        typ = node.get('Objekt_Typ')
        if typ == 'CAN_CMI_Obj':
            raw_b = node.get('Bezeichnung') or ''
            b = raw_b.split(': ')[-1].strip()
            pos = pos_mapping[node]
            can_sig = (node.get('can_knoten'), node.get('can_subindex'), node.get('can_index'))

            if b not in xml_dict:
                beschreibung.append(b)
                xml_dict[b] = pos
                seen_names[b] = can_sig
            else:
                if seen_names[b] == can_sig:
                    logger.info(
                        '[UVR] Deduplicating canvas duplicate for sensor "%s" on page %d (pos%d -> keeping first pos%d)',
                        b, Seite, pos, xml_dict[b]
                    )
                else:
                    suffix = 2
                    unique_b = f"{b}_{suffix}"
                    while unique_b in xml_dict:
                        suffix += 1
                        unique_b = f"{b}_{suffix}"
                    logger.warning(
                        '[UVR] Name collision: sensor "%s" on page %d has different CAN signature %s (previous %s). Disambiguating to "%s" at pos%d',
                        b, Seite, can_sig, seen_names[b], unique_b, pos
                    )
                    beschreibung.append(unique_b)
                    xml_dict[unique_b] = pos
                    seen_names[unique_b] = can_sig

    logger.debug('[UVR] Available Strings in xml auf Seite %s: %s', Seite, beschreibung)
    return beschreibung, id_conf, xml_dict


def combine_html_xml(MyHTMLParserClass, beschreibung, id_conf, xml_dict, html: str) -> Dict[str, Any]:
    def parse_html_bs(html_text: str):
        soup = BeautifulSoup(html_text, 'html.parser')
        ids = []
        content = {}
        html_dict = {}
        for div in soup.find_all('div'):
            pos = None
            for attr_val in div.attrs.values():
                if isinstance(attr_val, str) and 'pos' in attr_val:
                    m = re.search(r'pos\s*(\d+)|pos(\d+)', attr_val)
                    if m:
                        pos = int(m.group(1) or m.group(2))
                        break
                elif isinstance(attr_val, (list, tuple)):
                    for v in attr_val:
                        if 'pos' in v:
                            m = re.search(r'pos\s*(\d+)|pos(\d+)', v)
                            if m:
                                pos = int(m.group(1) or m.group(2))
                                break
                    if pos is not None:
                        break
            if pos is None:
                id_attr = div.get('id')
                if id_attr and 'pos' in id_attr:
                    m = re.search(r'pos\s*(\d+)|pos(\d+)', id_attr)
                    if m:
                        pos = int(m.group(1) or m.group(2))
            if pos is None:
                continue
            ids.append(pos)
            raw = ''.join(str(c) for c in div.contents)
            content[pos] = raw
            text = div.get_text(separator=' ').strip()
            value_part, unit = separate(text)
            html_dict[pos] = {'value': value_part, 'unit': unit}
        return ids, content, html_dict

    id_res, content, html_dict = parse_html_bs(html)
    logger.debug('[UVR] HTML-dict %s', pprint.pformat(html_dict))
    logger.debug('[UVR] XML-dict %s', pprint.pformat(xml_dict))
    if len(id_conf) > 0 and len(content) != len(id_conf):
        logger.error('[UVR] Invariant violation: Page has %d HTML DIVs, but XML expects %d. Schema mismatch!', len(content), len(id_conf))
        return {}

    combined_dict: Dict[str, Any] = {}
    for key, value in xml_dict.items():
        try:
            html_entry = html_dict[value]
            if 'Modus' in key:
                entry_str = content[value]
                entry_text = BeautifulSoup(entry_str, 'html.parser').get_text(separator='\n').replace('\r', '').strip()
                parts = entry_text.split('\n')
                mode = None
                percent = None
                if len(parts) >= 1:
                    mode_part = parts[0].strip()
                    if mode_part == 'AUTO':
                        mode = 1.0
                    elif mode_part == 'HAND':
                        mode = 0.0
                    else:
                        try:
                            mode = float(mode_part)
                        except Exception:
                            mode = None
                if len(parts) >= 2:
                    percent_part = parts[1].strip()
                    percent_match = re.search(r'(\d+(?:[.,]\d+)?)', percent_part)
                    if percent_match:
                        percent_str = percent_match.group(1).replace(',', '.')
                        percent = float(percent_str)
                if len(parts) == 1:
                    combined_part = parts[0].strip()
                    combined_percent_match = re.search(r'(\d+(?:[.,]\d+)?)', combined_part)
                    if combined_percent_match:
                        pct = combined_percent_match.group(1).replace(',', '.')
                        try:
                            percent = float(pct)
                        except Exception:
                            percent = None
                        mode_token = re.sub(r'(\d+(?:[.,]\d+)?\s*%?)', '', combined_part).strip()
                        if mode_token == 'AUTO':
                            mode = 1.0
                        elif mode_token == 'HAND':
                            mode = 0.0
                        else:
                            try:
                                mode = float(mode_token)
                            except Exception:
                                mode = None
                if mode is not None:
                    try:
                        mode_val = int(mode)
                    except Exception:
                        mode_val = None
                    combined_dict[key + '_mode'] = {'value': mode_val, 'unit': 'OutputMode'}
                if percent is not None:
                    try:
                        percent_val = float(percent)
                    except Exception:
                        percent_val = None
                    combined_dict[key + '_percent'] = {'value': percent_val, 'unit': '%'}
                if mode is None and percent is None:
                    combined_dict[key] = html_entry
            else:
                combined_dict[key] = html_entry
        except Exception:
            logger.exception('[UVR] Error matching HTML and Item: %s, %s', key, value)

    logger.debug('[UVR] Combined-dict %s', pprint.pformat(combined_dict))
    return combined_dict.copy()


def extract_entity_data(results: Dict[str, Dict[str, Any]], unit: Optional[str] = None) -> Dict[str, Any]:
    if unit is not None:
        return {key: value['value'] for key, value in results.items() if value.get('unit') == unit}
    return {key: value['value'] for key, value in results.items()}


def filter_empty_values(data: List[Dict[str, Dict[str, Any]]]) -> List[Dict[str, Dict[str, Any]]]:
    filtered = []
    for entry_idx, entry in enumerate(data):
        filtered_entry = {}
        for key, value in entry.items():
            if value['value'] is not None:
                filtered_entry[key] = value
            else:
                logger.debug('[UVR] Filtered out: %s (value=None, unit=%s) from page %d', key, value.get('unit'), entry_idx)
        filtered.append(filtered_entry)
    return filtered

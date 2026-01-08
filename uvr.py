"""Facade module providing UVR read helpers.

This module exposes `read_data` and small helper re-exports while delegating
implementation to `uvr_fetch` and `uvr_parse` modules.
"""
from typing import Any, Dict
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging
from pathlib import Path
import os
import json
import time
import requests

from uvr_fetch import read_html
from uvr_parse import (
    combine_html_xml,
    MyHTMLParser,
    read_xml,
    separate,
    extract_entity_data,
    filter_empty_values,
)

logger = logging.getLogger(__name__)


def _read_data(xml: str, ip: str, user: str, password: str):
    """Read UVR data from all pages. Returns (combined_dict, success_status_dict)."""
    try:
        tree = ET.parse(xml)
        root = tree.getroot()
    except Exception as e:
        logger.error('[UVR] Failed to parse XML file %s: %s', xml, e)
        return [], {'xml_error': str(e), 'pages_attempted': 0, 'pages_successful': 0, 'pages_failed': 0}
    
    Seiten = range(0, len(root.findall('./Seiten/')))
    combined_dict = []
    pages_attempted = len(Seiten)
    pages_successful = 0
    pages_failed = 0
    failed_pages = []

    for Seite in Seiten:
        try:
            beschreibung, id_conf, xml_dict = read_xml(root, Seite)
            html = read_html(ip, Seite, user, password)
            if html is not None and html is not False:
                combined_dict.append(combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html))
                pages_successful += 1
            else:
                logger.error('[UVR] Page %d: HTML could not be loaded', Seite)
                pages_failed += 1
                failed_pages.append(Seite)
        except Exception as e:
            logger.exception('[UVR] Page %d: Exception during processing: %s', Seite, e)
            pages_failed += 1
            failed_pages.append(Seite)

    status = {
        'pages_attempted': pages_attempted,
        'pages_successful': pages_successful,
        'pages_failed': pages_failed,
        'failed_pages': failed_pages,
        'all_successful': pages_failed == 0
    }
    return combined_dict, status


def read_data(credentials: Dict[str, Any]):
    """Read UVR data. Returns (combined_dict, status_dict) for new callers, or just combined_dict for backwards compatibility."""
    result = _read_data(credentials['xml_filename'], credentials['ip'], credentials['user'], credentials['password'])
    # Backwards compatibility: if caller expects single return value, they get combined_dict
    # New code can unpack tuple
    return result


def print_data(combined_dict, filter_unit=None):
    for page_values in combined_dict:
        logger.debug('[UVR] Page values: %s', page_values)
        logger.debug(extract_entity_data(page_values, unit=filter_unit))


# Re-export commonly used functions for backwards compatibility/tests
__all__ = [
    'read_data',
    'combine_html_xml',
    'MyHTMLParser',
    'separate',
    'extract_entity_data',
    'filter_empty_values',
]
import logging
import pprint
import re
from html.parser import HTMLParser
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """Normalize a raw unit token into a canonical unit string used by the rest of the code.

    Examples: 'Â°C' -> '°C', 'AUS' -> 'switch', 'W/m²' -> 'W'
    """
    if raw_unit is None:
        return None
    u = str(raw_unit).strip()
    u_upper = u.upper()
    if u_upper in ("AN", "ON", "EIN", "AUS", "OFF"):
        return "switch"
    if u_upper == "AUTO" or u_upper == "HAND":
        return "OutputMode"
    if u_upper in ("W/M²", "W/M°²", "W/M2", "W/M\u00b2"):
        return "W"
    if u_upper in ("KW"):
        return "kW"
    if u_upper in ("KWH"):
        return "kWh"
    if u_upper in ("L/H", "L/H"):
        return "l/h"
    if u_upper in ("%",):
        return "%"
    if u_upper in ("°C", "C", "Â°C"):
        return "°C"
    # fallback: return original stripped token
    return u


def separate(s: Any) -> Tuple[Optional[float], Optional[str]]:
    """Extract a numeric value and unit from a text fragment.

    Returns (value, unit) where unit is normalized by `normalize_unit`.
    """
    value: Optional[float] = None
    if s is None:
        return None, None
    # Normalize to string
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = s.lstrip('\n')
    s = s.replace('\xa0', ' ')
    s = s.replace('Â', '°')
    # Accept both comma and dot as decimal separators
    s = s.replace(',', '.')

    # find numeric parts
    numeric_parts = re.findall(r'-?\d+(?:\.\d+)?', s)
    for part in numeric_parts:
        try:
            value = float(part)
            break
        except ValueError:
            continue

    # detect unit token near numeric or any known words
    unit_pattern = r'(°C|Â°C|l/h|W/m²|W/m°²|%|kWh|kW|min|AUS|AN|ON|OFF|AUTO|EIN|C)'
    unit_match = re.search(unit_pattern, s, flags=re.IGNORECASE)
    raw_unit = unit_match.group().strip() if unit_match else None
    unit = normalize_unit(raw_unit)

    # convert textual ON/OFF etc to numeric values
    if unit == 'switch' and value is None:
        if re.search(r'\b(AN|ON|EIN)\b', s, flags=re.IGNORECASE):
            value = 1.0
        elif re.search(r'\b(AUS|OFF)\b', s, flags=re.IGNORECASE):
            value = 0.0

    # percent values in TA often shown as '0,0 %' meaning 0.0% — keep percent as raw number
        from uvr_fetch import read_html, fetch
        from uvr_parse import (
            combine_html_xml,
            MyHTMLParser,
            read_xml,
            separate,
            extract_entity_data,
            filter_empty_values,
        )
        # keep percent as percentage (0-100)
        try:
            value = float(value)
        except Exception:
            pass

    return value, unit


class MyHTMLParser(HTMLParser):
    def __init__(self, log):
        super().__init__()
        self.log = log
        self.id = []
        self.data = {}
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
            # Log the raw fragment before any normalization so we can inspect exact HTML/text
            self.log.debug('Raw fragment before normalization for id {}: {}'.format(self.curr_id, repr(s)))
            self.log.debug('Handle endtag {} for id {}'.format(s, self.curr_id))
            # Keep a copy of the original before we replace comma/characters
            raw_original = s
            s = s.replace(',', '.').replace('Â', '°').encode('utf-8').decode('utf-8')
            #s = s.replace('AUS', '0').replace('EIN', '1').replace('OFF', '0').replace('ON', '1')
            self.log.debug('closing tag and saving{} for id {}'.format(s, self.curr_id))
            if True:
                value_part, unit = separate(s)
                
                # Store values and units separately
                self.data[self.curr_id] = s
                self.dict[self.curr_id] = {'value': value_part, 'unit': unit}

            #except Exception as e:
            #    self.log.warning('Exception {} for value |{}|. String was|{}|'.format(e, w, s))


def fetch(url: str, username: str, password: str, timeout: int = 10, attempts: int = 3) -> Optional[str]:
    """Fetch URL using requests with retries and timeout.

    Returns response text or None on persistent failure.
    """
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, auth=(username, password), timeout=timeout)
            resp.raise_for_status()
            text = resp.text
            logger.debug("Fetched %s (len=%d)", url, len(text))
            return text
        except requests.Timeout as e:
            last_exc = e
            logger.debug("Timeout fetching %s (attempt %s/%s)", url, attempt, attempts)
        except requests.RequestException as e:
            last_exc = e
            logger.debug("Request exception fetching %s (attempt %s/%s): %s", url, attempt, attempts, e)
        # backoff
        backoff = min(2 ** attempt, 30)
        logger.debug("Waiting %.1f seconds before retry", backoff)
        time_sleep = backoff + (0.1 * attempt)
        from time import sleep as _sleep
        _sleep(time_sleep)
    logger.error("Failed to fetch %s after %s attempts: %s", url, attempts, last_exc)
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
    # Store the fetched HTML for debugging
    with open(f"debug_fetched_html_seite{Seite}.html", "w", encoding="utf-8") as f:
        f.write(h if h else "")
    return h


def combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html):
    # Use BeautifulSoup to extract div blocks and their pos-ids.
    def parse_html_bs(html_text):
        soup = BeautifulSoup(html_text, "html.parser")
        ids = []
        content = {}
        html_dict = {}
        for div in soup.find_all('div'):
            # find pos number in attributes or id
            pos = None
            # check attributes
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
            # check id attribute as fallback
            if pos is None:
                id_attr = div.get('id')
                if id_attr and 'pos' in id_attr:
                    m = re.search(r'pos\s*(\d+)|pos(\d+)', id_attr)
                    if m:
                        pos = int(m.group(1) or m.group(2))
            if pos is None:
                continue
            ids.append(pos)
            # inner HTML content
            raw = ''.join(str(c) for c in div.contents)
            content[pos] = raw
            # extract text for numeric parsing
            text = div.get_text(separator=' ').strip()
            value_part, unit = separate(text)
            html_dict[pos] = {'value': value_part, 'unit': unit}
        return ids, content, html_dict

    id_res, content, html_dict = parse_html_bs(html)
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
            html_entry = html_dict[value]
            # Special handling for 'Modus' entries
            if "Modus" in key:
                entry_str = content[value]  # Use raw HTML content instead of parsed value
                logger.debug(f"Processing Modus key: {key}, entry_str: {repr(entry_str)}")
                # Convert HTML to plain text, preserving line breaks
                entry_text = BeautifulSoup(entry_str, "html.parser").get_text(separator='\n').replace('\r', '').strip()
                # Split by newlines
                parts = entry_text.split('\n')
                logger.debug(f"Parts after split: {parts}")
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
                    # Accept both comma and dot as decimal separators
                    percent_match = re.search(r'(\d+(?:[.,]\d+)?)', percent_part)
                    if percent_match:
                        percent_str = percent_match.group(1).replace(',', '.')
                        percent = float(percent_str)
                # Handle case where the HTML contained mode and percent on one line
                # e.g. 'AUTO 0,0 %' or 'AUTO 0.0%'
                if len(parts) == 1:
                    combined_part = parts[0].strip()
                    # try to find percent inside the same part
                    combined_percent_match = re.search(r'(\d+(?:[.,]\d+)?)', combined_part)
                    if combined_percent_match:
                        pct = combined_percent_match.group(1).replace(',', '.')
                        try:
                            percent = float(pct)
                        except Exception:
                            percent = None
                        # remove percent substring to isolate the mode token
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
                logger.debug(f"Detected mode: {mode}, percent: {percent}")
                # Add mode as OutputMode (binary sensor)
                if mode is not None:
                    try:
                        mode_val = int(mode)
                    except Exception:
                        mode_val = None
                    combined_dict[key + "_mode"] = {'value': mode_val, 'unit': 'OutputMode'}
                # Add percent as number sensor
                if percent is not None:
                    try:
                        percent_val = float(percent)
                        logger.debug(f"Percent value: {percent_val}")
                    except Exception as e:
                        logger.debug(f"Error parsing percent: {e}")
                        percent_val = None
                    combined_dict[key + "_percent"] = {'value': percent_val, 'unit': '%'}
                # If neither found, fallback to original
                if mode is None and percent is None:
                    combined_dict[key] = html_entry
            else:
                combined_dict[key] = html_entry
        except Exception as err:
            logger.exception("[UVR] Error matching HTML and Item: {0}, {1}. Exception".format(key, value), exc_info=True)

    # Debug output for combined_dict
    logger.debug("[UVR] Combined-dict {0}".format(pprint.pformat(combined_dict)))
    return combined_dict.copy()


def filter_empty_values(data):
    filtered_data = [{key: value for key, value in entry.items() if value['value'] is not None} for entry in data]
    return filtered_data


class MetricsTracker:
    """Track operational metrics and write to log file hourly."""
    def __init__(self, log_file_path: str):
        self.log_file = Path(log_file_path)
        self.cycle_count = 0
        self.success_count = 0
        self.partial_success_count = 0
        self.failure_count = 0
        self.total_pages_fetched = 0
        self.total_pages_failed = 0
        self.mqtt_publish_success = 0
        self.mqtt_publish_failure = 0
        self.total_fetch_time = 0.0
        self.last_log_time = datetime.now()
        self.start_time = datetime.now()
        
    def record_cycle(self, fetch_status: Dict, fetch_duration: float, mqtt_success: bool = False):
        """Record metrics for a completed cycle."""
        self.cycle_count += 1
        self.total_fetch_time += fetch_duration
        
        if fetch_status.get('all_successful'):
            self.success_count += 1
        elif fetch_status.get('pages_successful', 0) > 0:
            self.partial_success_count += 1
        else:
            self.failure_count += 1
            
        self.total_pages_fetched += fetch_status.get('pages_successful', 0)
        self.total_pages_failed += fetch_status.get('pages_failed', 0)
        
        if mqtt_success:
            self.mqtt_publish_success += 1
        else:
            self.mqtt_publish_failure += 1
    
    def should_write_log(self) -> bool:
        """Check if an hour has passed since last log write."""
        return (datetime.now() - self.last_log_time) >= timedelta(hours=1)
    
    def write_log(self):
        """Write metrics to log file."""
        now = datetime.now()
        uptime = now - self.start_time
        avg_fetch_time = self.total_fetch_time / self.cycle_count if self.cycle_count > 0 else 0
        
        log_entry = {
            "timestamp": now.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "metrics": {
                "total_cycles": self.cycle_count,
                "successful_cycles": self.success_count,
                "partial_success_cycles": self.partial_success_count,
                "failed_cycles": self.failure_count,
                "total_pages_fetched": self.total_pages_fetched,
                "total_pages_failed": self.total_pages_failed,
                "mqtt_publish_success": self.mqtt_publish_success,
                "mqtt_publish_failure": self.mqtt_publish_failure,
                "average_fetch_time_seconds": round(avg_fetch_time, 2)
            }
        }
        
        try:
            # Append to log file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            logger.info("Metrics written to %s", self.log_file)
            self.last_log_time = now
        except Exception:
            logger.exception("Failed to write metrics log")
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        uptime = datetime.now() - self.start_time
        return (f"Uptime: {int(uptime.total_seconds())}s | "
                f"Cycles: {self.cycle_count} | "
                f"Success: {self.success_count} | "
                f"Partial: {self.partial_success_count} | "
                f"Failed: {self.failure_count}")


def push_uptime_kuma(url: str, status: str = "up", msg: str = "", ping: float = None):
    """Push status update to Uptime Kuma push monitor.
    
    Args:
        url: Full Uptime Kuma push URL (e.g., http://uptime-kuma:3001/api/push/xxxxx)
        status: 'up' or 'down'
        msg: Optional status message
        ping: Optional response time in ms
    """
    if not url:
        return
    
    try:
        params = {"status": status}
        if msg:
            params["msg"] = msg
        if ping is not None:
            params["ping"] = int(ping)
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        logger.debug("Uptime Kuma push successful")
    except Exception:
        logger.debug("Failed to push to Uptime Kuma", exc_info=True)

if __name__ == "__main__":
    # Configure basic logging for foreground runs
    import sys as _sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(_sys.stdout)], force=True)
    # Configure module loggers
    logger.setLevel(logging.INFO)
    logging.getLogger('uvr_fetch').setLevel(logging.INFO)
    logging.getLogger('uvr_parse').setLevel(logging.INFO)
    logging.getLogger('uvr_mqtt').setLevel(logging.INFO)

    # Load configuration from config.json or environment
    cfg = {}
    cfg_path = Path.cwd() / "config.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            logger.exception("Failed to load config.json")
            cfg = {}

    uvr_cfg = cfg.get("uvr", {})
    mqtt_cfg = cfg.get("mqtt", {})
    device_cfg = cfg.get("device", {})
    monitoring_cfg = cfg.get("monitoring", {})
    loop_cfg = cfg.get("loop", {})

    xml_file = uvr_cfg.get("xml_filename", os.environ.get("UVR_XML", "Neu.xml"))
    ip = uvr_cfg.get("ip", os.environ.get("UVR_IP", "192.168.177.5"))
    user = uvr_cfg.get("user", os.environ.get("UVR_USER", "user"))
    password = uvr_cfg.get("password", os.environ.get("UVR_PASSWORD", ""))

    # Data fetch/publish loop interval (seconds)
    try:
        loop_interval = int(loop_cfg.get("interval_seconds", os.environ.get("UVR_INTERVAL", 60)))
    except Exception:
        loop_interval = 60
    
    # Monitoring settings
    uptime_kuma_url = monitoring_cfg.get("uptime_kuma_url", os.environ.get("UPTIME_KUMA_URL", ""))
    metrics_log_file = monitoring_cfg.get("metrics_log_file", os.environ.get("METRICS_LOG_FILE", "uvr_metrics.log"))
    try:
        # Prefer explicit monitoring.interval_seconds, then kuma_interval_seconds, else fallback to loop interval
        kuma_interval_seconds = int(monitoring_cfg.get("interval_seconds", monitoring_cfg.get("kuma_interval_seconds", os.environ.get("KUMA_INTERVAL_SECONDS", loop_interval))))
    except Exception:
        kuma_interval_seconds = loop_interval

    # MQTT settings (optional; if broker is specified, we will publish values)
    broker = mqtt_cfg.get("broker", os.environ.get("MQTT_BROKER"))
    port = int(mqtt_cfg.get("port", os.environ.get("MQTT_PORT", 1883)))
    mqtt_user = mqtt_cfg.get("user", os.environ.get("MQTT_USER", ""))
    mqtt_password = mqtt_cfg.get("password", os.environ.get("MQTT_PASSWORD", ""))
    device_name = device_cfg.get("name", os.environ.get("DEVICE_NAME", "UVR_TADesigner"))

    # Prepare MQTT client if broker configured
    mqtt_client = None
    availability_topic = None
    try:
        if broker:
            from uvr_mqtt import build_mqtt_client, create_config as _create_config, send_values as _send_values, sanitize_name as _sanitize_name, check_mqtt_connection as _check_mqtt_connection
            mqtt_client = build_mqtt_client({"broker": broker, "port": port, "user": mqtt_user, "password": mqtt_password})
            device_id = _sanitize_name(device_name)
            availability_topic = f"homeassistant/{device_id}/availability"
            # Publish retained availability online
            mqtt_client.publish(availability_topic, "online", retain=True)
            # Send discovery/config once on startup
            try:
                logger.info("Sending initial discovery config to MQTT...")
                initial_data, initial_status = _read_data(xml_file, ip, user, password)
                if initial_status.get('pages_successful', 0) > 0:
                    initial_values = filter_empty_values(initial_data)
                    _create_config(mqtt_client, device_name, initial_values)
                    logger.info("Discovery config sent successfully")
                else:
                    logger.warning("Skipping discovery config - no pages fetched successfully")
            except Exception:
                logger.exception("Failed to publish discovery config - will continue without it")
    except Exception:
        logger.exception("MQTT setup failed; continuing without MQTT publishing")
        mqtt_client = None

    # Initialize metrics tracker
    metrics = MetricsTracker(metrics_log_file)
    logger.info("Metrics logging to: %s (written hourly)", metrics_log_file)
    if uptime_kuma_url:
        logger.info("Uptime Kuma push enabled: %s (interval=%ss)", uptime_kuma_url[:50] + "..." if len(uptime_kuma_url) > 50 else uptime_kuma_url, kuma_interval_seconds)
    last_kuma_push = datetime.now() - timedelta(seconds=kuma_interval_seconds)

    logger.info("Starting UVR loop: interval=%ss, mqtt=%s", loop_interval, ("enabled" if mqtt_client else "disabled"))
    cycle_num = 0
    try:
        while True:
            cycle_num += 1
            try:
                logger.info("=== Cycle %d: Starting data fetch ===", cycle_num)
                
                # Track fetch timing
                fetch_start = time.time()
                
                # Read and filter data
                combined_data, fetch_status = _read_data(xml_file, ip, user, password)
                page_values = filter_empty_values(combined_data)
                
                fetch_duration = time.time() - fetch_start
                
                # Report fetch status with details
                mqtt_success = False
                if fetch_status.get('all_successful'):
                    logger.info("✓ Successfully fetched %d/%d pages (%.2fs)", 
                               fetch_status['pages_successful'], fetch_status['pages_attempted'], fetch_duration)
                else:
                    logger.warning("⚠ Partial success: fetched %d/%d pages (failed: %s)", 
                                 fetch_status['pages_successful'], fetch_status['pages_attempted'],
                                 fetch_status.get('failed_pages', []))
                    if fetch_status['pages_successful'] == 0:
                        logger.error("✗ All pages failed to fetch")
                        raise Exception("All pages failed")
                
                # Optionally publish via MQTT
                if mqtt_client:
                    try:
                        if not _check_mqtt_connection(mqtt_client):
                            logger.error("✗ MQTT connection unavailable; skipping publish")
                        else:
                            _send_values(mqtt_client, device_name, page_values)
                            logger.info("✓ Successfully published values to MQTT")
                            mqtt_success = True
                    except Exception:
                        logger.exception("✗ Failed to publish MQTT values")
                
                # Record metrics
                metrics.record_cycle(fetch_status, fetch_duration, mqtt_success)
                
                # Push to Uptime Kuma (report as 'up' with fetch time) on interval
                if uptime_kuma_url:
                    now_ts = datetime.now()
                    if (now_ts - last_kuma_push).total_seconds() >= kuma_interval_seconds:
                        status_msg = f"Cycle {cycle_num}: {fetch_status['pages_successful']}/{fetch_status['pages_attempted']} pages"
                        push_uptime_kuma(uptime_kuma_url, status="up", msg=status_msg, ping=fetch_duration * 1000)
                        last_kuma_push = now_ts
                
                # Write metrics log if an hour has passed
                if metrics.should_write_log():
                    metrics.write_log()
                
                logger.info("=== Cycle %d: Complete. Waiting %ds until next cycle ===", cycle_num, loop_interval)
                logger.debug("Metrics: %s", metrics.get_summary())
                # Sleep until next cycle
                from time import sleep as _sleep
                for _ in range(int(loop_interval)):
                    _sleep(1)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.exception("✗ Error during polling cycle: %s", e)
                # Notify Uptime Kuma of failure immediately
                if uptime_kuma_url:
                    push_uptime_kuma(uptime_kuma_url, status="down", msg=f"Cycle {cycle_num} failed: {str(e)[:100]}")
                from time import sleep as _sleep
                _sleep(5)
    except KeyboardInterrupt:
        logger.info("Stopping UVR loop (KeyboardInterrupt)")
    finally:
        # Write final metrics before shutdown
        try:
            metrics.write_log()
            logger.info("Final metrics: %s", metrics.get_summary())
        except Exception:
            logger.debug("Could not write final metrics")
        
        try:
            if mqtt_client and availability_topic:
                try:
                    mqtt_client.publish(availability_topic, "offline", retain=True)
                except Exception:
                    pass
                try:
                    mqtt_client.loop_stop()
                except Exception:
                    pass
                try:
                    mqtt_client.disconnect()
                except Exception:
                    pass
        except Exception:
            logger.exception("Error during MQTT shutdown")
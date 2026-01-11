"""Facade module providing UVR read helpers.

This module exposes `read_data` and helper re-exports while delegating
implementation to `uvr_fetch` and `uvr_parse` modules.
"""
from typing import Any, Dict
import xml.etree.ElementTree as ET
import logging

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
    return result


def print_data(combined_dict, filter_unit=None):
    for page_values in combined_dict:
        logger.debug('[UVR] Page values: %s', page_values)
        logger.debug(extract_entity_data(page_values, unit=filter_unit))


__all__ = [
    'read_data',
    'combine_html_xml',
    'MyHTMLParser',
    'separate',
    'extract_entity_data',
    'filter_empty_values',
]

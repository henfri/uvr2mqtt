import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def fetch(url: str, username: str, password: str, timeout: int = 10, attempts: int = 3) -> Optional[str]:
    """Fetch URL with retries and return text or None on failure."""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, auth=(username, password), timeout=timeout)
            resp.raise_for_status()
            logger.info("Daten erfolgreich abgerufen von %s", url)
            logger.debug("Fetched %s (len=%d)", url, len(resp.text))
            return resp.text
        except requests.Timeout as e:
            last_exc = e
            logger.debug("Timeout fetching %s (attempt %d/%d)", url, attempt, attempts)
        except requests.RequestException as e:
            last_exc = e
            logger.debug("Request exception %s while fetching %s (attempt %d/%d)", e, url, attempt, attempts)
        # simple backoff
        import time
        time.sleep(min(2 ** attempt, 30))
    logger.error("Failed to fetch %s after %d attempts: %s", url, attempts, last_exc)
    return None


def read_html(ip: str, Seite: int, username: str, password: str, timeout: int = 10) -> Optional[str]:
    url = f'http://{ip}/schematic_files/{Seite+1}.cgi'
    logger.debug('Handling url %s', url)
    html = fetch(url, username, password, timeout=timeout)
    # Save debug copy to workspace for offline inspection
    try:
        with open(f"debug_fetched_html_seite{Seite}.html", "w", encoding="utf-8") as f:
            f.write(html or "")
    except Exception:
        logger.debug("Could not write debug html file for Seite %s", Seite)
    return html

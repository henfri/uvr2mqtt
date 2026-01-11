import os
import tempfile
import shutil

import uvr_fetch
from uvr_fetch import read_html


def test_read_html_writes_debug_file():
    html_text = "<div>ok</div>"
    # Patch fetch to avoid network calls
    orig_fetch = uvr_fetch.fetch
    try:
        uvr_fetch.fetch = lambda url, username, password, timeout=10: html_text
        tmpdir = tempfile.mkdtemp()
        cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = read_html("127.0.0.1", 0, "user", "pass")
            debug_path = os.path.join(tmpdir, "debug_html", "debug_fetched_html_seite0.html")
            assert os.path.exists(debug_path)
            with open(debug_path, "r", encoding="utf-8") as f:
                saved = f.read()
            assert saved == html_text
            assert result == html_text
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)
    finally:
        uvr_fetch.fetch = orig_fetch

"""Wait for the isolated QA API and frontend with a bounded startup deadline."""
import time
import urllib.error
import urllib.request

deadline = time.monotonic() + 120
pending = {"http://127.0.0.1:8018/health/ready", "http://127.0.0.1:3018/"}
while pending and time.monotonic() < deadline:
    for url in tuple(pending):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    pending.remove(url)
        except (OSError, urllib.error.URLError):
            pass
    if pending:
        time.sleep(1)
if pending:
    raise SystemExit("QA services did not become ready: " + ", ".join(sorted(pending)))

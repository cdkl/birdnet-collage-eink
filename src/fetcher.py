import os
import logging

log = logging.getLogger(__name__)


class CollageFetcher:
    def __init__(self, base_url, cache_dir="/var/lib/birdnet-eink", timeout=30):
        self._base_url = base_url.rstrip("/")
        self._etag_file = os.path.join(cache_dir, "last-etag.txt")
        self._cache_dir = cache_dir
        self._timeout = timeout
        self.last_status_code = None
        os.makedirs(cache_dir, exist_ok=True)

    def _load_etag(self):
        try:
            with open(self._etag_file) as f:
                return f.read().strip()
        except (FileNotFoundError, OSError):
            return None

    def save_etag(self, etag):
        try:
            with open(self._etag_file, "w") as f:
                f.write(etag)
        except OSError:
            log.warning("Failed to save ETag to %s", self._etag_file)

    def fetch(self, width=1600, height=1200, hours=24, refresh=0, skip_etag=False):
        import requests

        url = f"{self._base_url}/api/eink?w={width}&h={height}&hours={hours}"
        if refresh:
            url += "&refresh=1"
        headers = {}
        etag = None if skip_etag else self._load_etag()
        if etag:
            headers["If-None-Match"] = f'"{etag}"'

        log.debug("Fetching %s (etag=%s)", url, etag or "none")
        try:
            resp = requests.get(url, headers=headers, timeout=self._timeout)
            self.last_status_code = resp.status_code
        except requests.RequestException as e:
            log.error("Fetch failed: %s", e)
            self.last_status_code = None
            return (None, None)

        if resp.status_code == 304:
            log.info("No new collage (304)")
            return (None, etag)

        if resp.status_code != 200:
            log.error("Unexpected status %d from %s", resp.status_code, url)
            return (None, None)

        new_etag = resp.headers.get("ETag", "").strip('"')
        log.info(
            "Fetched new collage (%d bytes, etag=%s)",
            len(resp.content), new_etag,
        )
        return (resp.content, new_etag)
"""Small polite HTTP client: per-host rate limit, retries, gzip, JSON helpers.

Uses only the standard library. Proxies from HTTPS_PROXY/HTTP_PROXY are
honoured automatically by urllib.
"""
from __future__ import annotations

import gzip
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

log = logging.getLogger(__name__)

USER_AGENT = "intenetparser/0.1 (public-discussion research; +https://github.com/simonhgergo-cmd/intenetparser)"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpError(Exception):
    def __init__(self, status: int, url: str, body: str = ""):
        super().__init__(f"HTTP {status} for {url}: {body[:200]}")
        self.status = status
        self.url = url
        self.body = body


class Client:
    def __init__(self, min_interval: float = 1.0, max_retries: int = 4,
                 timeout: float = 30.0, user_agent: str = USER_AGENT):
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.timeout = timeout
        self.user_agent = user_agent
        self._last_call: dict[str, float] = {}

    def _throttle(self, host: str) -> None:
        wait = self._last_call.get(host, 0) + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_call[host] = time.monotonic()

    def request(self, url: str, params: dict | None = None, headers: dict | None = None,
                data: bytes | None = None, method: str | None = None) -> bytes:
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(clean, doseq=True)
        host = urllib.parse.urlsplit(url).netloc
        hdrs = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        hdrs.update(headers or {})

        for attempt in range(self.max_retries + 1):
            self._throttle(host)
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return _decode(resp.read(), resp.headers.get("Content-Encoding", ""))
            except urllib.error.HTTPError as e:
                body = _decode(e.read(), e.headers.get("Content-Encoding", "")).decode("utf-8", "replace")
                if e.code not in RETRY_STATUSES or attempt == self.max_retries:
                    raise HttpError(e.code, url, body) from None
                delay = _retry_after(e.headers.get("Retry-After"), attempt)
                log.warning("HTTP %s from %s, retrying in %.0fs", e.code, host, delay)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == self.max_retries:
                    raise
                delay = 2 ** (attempt + 1)
                log.warning("Network error for %s (%s), retrying in %.0fs", host, e, delay)
            time.sleep(delay)
        raise AssertionError("unreachable")

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None):
        return json.loads(self.request(url, params=params, headers=headers))

    def post_json(self, url: str, payload: dict, headers: dict | None = None):
        hdrs = {"Content-Type": "application/json"}
        hdrs.update(headers or {})
        return json.loads(self.request(url, headers=hdrs, data=json.dumps(payload).encode(), method="POST"))


def _decode(raw: bytes, encoding: str) -> bytes:
    encoding = encoding.lower()
    if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    if encoding == "deflate":
        return zlib.decompress(raw)
    return raw


def _retry_after(value: str | None, attempt: int) -> float:
    try:
        return min(float(value), 120.0)
    except (TypeError, ValueError):
        return float(min(2 ** (attempt + 1), 120))

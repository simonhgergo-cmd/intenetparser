"""Local browser control panel (`iparse app`, what the start files open).

Serves on 127.0.0.1 only. Requests must carry a matching Host header and,
for changes, an X-IParse header, so other websites open in the browser
can't drive it.
"""
from __future__ import annotations

import json
import logging
import re
import secrets
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import catalog
from . import pipeline as P
from .interactive import EXAMPLE, check_reddit, set_in_section
from .webapp_page import PAGE

log = logging.getLogger("iparse")
SAFE_NAME = re.compile(r"^[\w.-]+\.md$")


class _LogBuffer(logging.Handler):
    def __init__(self, size: int = 400):
        super().__init__(logging.INFO)
        self.lines: deque[str] = deque(maxlen=size)
        self.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))

    def emit(self, record):
        self.lines.append(self.format(record))


class App:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.first_run = not config_path.exists()
        if self.first_run:
            text = EXAMPLE.read_text(encoding="utf-8")
            config_path.write_text(set_in_section(text, "storage", "author_salt", secrets.token_hex(16)),
                                   encoding="utf-8")
        self.logs = _LogBuffer()
        logging.getLogger().addHandler(self.logs)
        logging.getLogger().setLevel(logging.INFO)
        self.running: str | None = None  # None | "once" | "loop"
        self.next_run: float | None = None
        self.last_run: float | None = None
        self.last_error: str | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def cfg(self) -> dict:
        return P.load_config(self.config_path)

    # ---------------------------------------------------------------- runs
    def start(self, loop: bool) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running = "loop" if loop else "once"
            self._stop.clear()
        threading.Thread(target=self._worker, args=(loop,), daemon=True).start()
        return True

    def stop_loop(self) -> None:
        self._stop.set()

    def _worker(self, loop: bool) -> None:
        try:
            while True:
                self.next_run = None
                P.run_cycle(self.cfg())
                self.last_run, self.last_error = time.time(), None
                if not loop or self._stop.is_set():
                    break
                interval = P.parse_interval(self.cfg().get("schedule", {}).get("every", "12h"))
                self.next_run = time.time() + interval
                log.info("Next run at %s", time.strftime("%H:%M", time.localtime(self.next_run)))
                if self._stop.wait(interval):
                    break
        except Exception as e:  # shown in the UI
            log.exception("Run failed")
            self.last_error = str(e)
        finally:
            self.running, self.next_run = None, None
            self._stop.clear()

    # -------------------------------------------------------------- status
    def status(self) -> dict:
        cfg = self.cfg()
        report_path, _ = P.output_paths(cfg)
        store = P.open_store(cfg)
        try:
            counts = store.counts()
            size = store.size_bytes()
        finally:
            store.close()
        return {
            **counts, "db_mb": round(size / 1e6, 1), "running": self.running,
            "stopping": self._stop.is_set(), "next_run": self.next_run, "last_run": self.last_run,
            "last_error": self.last_error, "report": report_path.exists(),
            "report_time": report_path.stat().st_mtime if report_path.exists() else None,
            "log": list(self.logs.lines)[-150:], "first_run": self.first_run,
        }

    # ------------------------------------------------------------ settings
    def settings(self) -> dict:
        cfg = self.cfg()
        cat = cfg.get("catalog", {})
        include = bool(cat.get("include_sensitive", False))
        selected = set(catalog.select(cat.get("groups", ["*"]), include))
        src = cfg.get("sources", {})
        reddit = src.get("reddit", {})
        return {
            "groups": {dim: [{"name": n, "sensitive": g["sensitive"], "selected": n in selected}
                             for n, g in catalog.CATALOG.items() if g["dim"] == dim]
                       for dim in ("audience", "interest", "region")},
            "include_sensitive": include,
            "reddit_mode": reddit.get("mode", "auto"),
            "reddit_client_id": reddit.get("client_id", ""),
            "reddit_has_secret": bool(reddit.get("client_secret")),
            "keep_days": cfg.get("storage", {}).get("keep_days", 0),
            "every": cfg.get("schedule", {}).get("every", "12h"),
            "bluesky_handle": src.get("bluesky", {}).get("handle", ""),
            "bluesky_has_password": bool(src.get("bluesky", {}).get("app_password")),
            "youtube_has_key": bool(src.get("youtube", {}).get("api_key")),
            "sources": {name: bool(c.get("enabled")) for name, c in src.items()},
        }

    def save_settings(self, data: dict) -> dict:
        groups = [g for g in data.get("groups", []) if g in catalog.CATALOG]
        if not groups:
            return {"ok": False, "error": "Válassz legalább egy csoportot."}
        include = bool(data.get("include_sensitive"))
        everything = {n for n, g in catalog.CATALOG.items() if include or not g["sensitive"]}
        groups_value = ["*"] if set(groups) == everything else groups
        try:
            P.parse_interval(data.get("every", "12h"))
        except ValueError:
            return {"ok": False, "error": "Az időköz formátuma pl. 12h, 6h, 1d vagy 30m."}

        text = self.config_path.read_text(encoding="utf-8")
        text = set_in_section(text, "catalog", "groups", groups_value)
        text = set_in_section(text, "catalog", "include_sensitive", include)
        text = set_in_section(text, "schedule", "every", data.get("every", "12h"))
        text = set_in_section(text, "storage", "keep_days", int(data.get("keep_days") or 0))
        if data.get("reddit_mode") in ("auto", "archive", "official"):
            text = set_in_section(text, "sources.reddit", "mode", data["reddit_mode"])
        message = "Mentve."
        cid, secret = (data.get("reddit_client_id") or "").strip(), (data.get("reddit_client_secret") or "").strip()
        if cid and secret:
            problem = check_reddit(cid, secret)
            if problem and problem.startswith("Reddit rejected"):
                return {"ok": False, "error": "A Reddit elutasította az azonosítót vagy a titkos kulcsot."}
            message += "" if problem is None else " (A Reddit-adatokat nem tudtam ellenőrizni.)"
        if cid or data.get("reddit_clear"):
            text = set_in_section(text, "sources.reddit", "client_id", cid)
            if secret or data.get("reddit_clear"):
                text = set_in_section(text, "sources.reddit", "client_secret", secret)
        for name, enabled in (data.get("sources") or {}).items():
            if name in ("reddit", "hackernews", "bluesky", "mastodon", "stackexchange", "appstore",
                        "youtube", "tiktok"):
                text = set_in_section(text, f"sources.{name}", "enabled", bool(enabled))
        if data.get("bluesky_handle") is not None:
            text = set_in_section(text, "sources.bluesky", "handle", data["bluesky_handle"].strip())
        if data.get("bluesky_password"):
            text = set_in_section(text, "sources.bluesky", "app_password", data["bluesky_password"].strip())
        if data.get("youtube_key"):
            text = set_in_section(text, "sources.youtube", "api_key", data["youtube_key"].strip())
        self.config_path.write_text(text, encoding="utf-8")
        self.first_run = False
        return {"ok": True, "message": message}

    # ------------------------------------------------------------- exports
    def export_dir(self) -> Path:
        return P.output_paths(self.cfg())[1] / "llm"

    def exports(self) -> list[dict]:
        folder = self.export_dir()
        files = sorted(folder.glob("*.md"), key=lambda f: (f.name != "summary.md", f.name)) if folder.exists() else []
        return [{"name": f.name, "kb": round(f.stat().st_size / 1024)} for f in files]


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "iparse"

        def log_message(self, *args):
            pass

        def _send(self, code: int, body, ctype: str = "application/json; charset=utf-8", extra=None):
            raw = body if isinstance(body, bytes) else (
                json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(raw)

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, {"error": "forbidden"})
            path = urlsplit(self.path).path
            if path == "/":
                return self._send(200, PAGE, "text/html; charset=utf-8")
            if path == "/report":
                report = P.output_paths(app.cfg())[0]
                if report.exists():
                    return self._send(200, report.read_bytes(), "text/html; charset=utf-8")
                return self._send(404, "<p>Még nincs riport. Indíts egy gyűjtést.</p>", "text/html; charset=utf-8")
            if path.startswith("/exports/"):
                name = unquote(path.removeprefix("/exports/"))
                file = app.export_dir() / name
                if SAFE_NAME.match(name) and file.is_file():
                    return self._send(200, file.read_bytes(), "text/plain; charset=utf-8")
                return self._send(404, {"error": "not found"})
            api = {"/api/status": app.status, "/api/settings": app.settings, "/api/exports": app.exports,
                   "/api/plan": lambda: P.plan(app.cfg())}
            if path in api:
                try:
                    return self._send(200, api[path]())
                except Exception as e:
                    return self._send(500, {"error": str(e)})
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._host_ok() or self.headers.get("X-IParse") != "1":
                return self._send(403, {"error": "forbidden"})
            length = int(self.headers.get("Content-Length") or 0)
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self._send(400, {"error": "bad json"})
            path = urlsplit(self.path).path
            if path == "/api/run":
                return self._send(200, {"ok": app.start(bool(data.get("loop")))})
            if path == "/api/stop":
                app.stop_loop()
                return self._send(200, {"ok": True})
            if path == "/api/settings":
                return self._send(200, app.save_settings(data))
            if path == "/api/shutdown":
                self._send(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return None
            return self._send(404, {"error": "not found"})

    return Handler


def serve(config_path: Path, port: int = 8765, open_browser: bool = True) -> None:
    app = App(config_path)
    for p in (port, 0):  # fall back to any free port
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), make_handler(app))
            break
        except OSError:
            continue
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"\n  A vezérlőpult megnyílt a böngészőben: {url}")
    print("  Ha nem nyílt meg, másold be ezt a címet a böngészőbe.")
    print("  Ezt az ablakot hagyd nyitva (lekicsinyítheted). Ha bezárod, a program leáll.\n")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

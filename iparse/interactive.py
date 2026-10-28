"""Setup wizard and menu for people who'd rather not type commands."""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from . import catalog
from . import pipeline as P
from .http import Client, HttpError

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.toml"

REDDIT_INFO = """
Reddit is most of the data. By default it's read from Arctic Shift, a free public
archive of Reddit: no account, key or approval needed, and a full run takes
about 10-15 minutes. (It's run by a third party, so if it ever stops working,
the tool falls back to reading Reddit directly, which is slower.)

Reddit's own API now needs approval under its Responsible Builder Policy.
Only answer "y" below if Reddit has already approved an app for you.
"""


# --------------------------------------------------------------- config edits
def set_in_section(text: str, section: str, key: str, value) -> str:
    """Set `key = value` inside [section], uncommenting an existing line if there is one."""
    literal = json.dumps(value) if not isinstance(value, bool) else str(value).lower()
    header = re.search(rf"^\[{re.escape(section)}\][ \t]*$", text, re.M)
    if not header:
        return text.rstrip() + f"\n\n[{section}]\n{key} = {literal}\n"
    nxt = re.search(r"^\[", text[header.end():], re.M)
    end = header.end() + (nxt.start() if nxt else len(text[header.end():]))
    body = text[header.end():end]
    line = re.compile(rf"^#?[ \t]*{re.escape(key)}[ \t]*=.*$", re.M)
    if line.search(body):
        body = line.sub(lambda _: f"{key} = {literal}", body, count=1)
    else:
        body = f"\n{key} = {literal}" + body
    return text[:header.end()] + body + text[end:]


def check_reddit(client_id: str, secret: str) -> str | None:
    """None if the credentials work, otherwise a short reason."""
    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    try:
        Client(min_interval=0, max_retries=1).request(
            "https://www.reddit.com/api/v1/access_token",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            data=b"grant_type=client_credentials", method="POST")
        return None
    except HttpError as e:
        return "Reddit rejected the ID/secret" if e.status in (400, 401, 403) else f"Reddit answered {e.status}"
    except Exception as e:
        return f"couldn't reach Reddit ({e})"


def ask(prompt: str, default: str = "") -> str:
    try:
        answer = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    except EOFError:
        answer = ""
    return answer or default


def yes(prompt: str, default: bool = False) -> bool:
    return ask(f"{prompt} (y/n)", "y" if default else "n").lower().startswith("y")


# --------------------------------------------------------------------- wizard
def setup(config_path: Path) -> None:
    print("\n=== intenetparser setup ===\nPress Enter to skip any question.\n")
    if not config_path.exists():
        shutil.copy(EXAMPLE, config_path)
    text = config_path.read_text(encoding="utf-8")
    cfg = P.load_config(config_path)
    if cfg.get("storage", {}).get("author_salt", "change-me") == "change-me":
        text = set_in_section(text, "storage", "author_salt", secrets.token_hex(16))

    # Reddit
    print(REDDIT_INFO)
    has_reddit = bool(cfg.get("sources", {}).get("reddit", {}).get("client_id"))
    if yes("Do you have an approved Reddit app (client ID and secret)?", has_reddit):
        while True:
            cid = ask("Paste the client ID (Enter to cancel)")
            if not cid:
                break
            secret = ask("Paste the secret")
            print("Checking with Reddit...")
            problem = check_reddit(cid, secret)
            if problem is None or not problem.startswith("Reddit rejected"):
                text = set_in_section(text, "sources.reddit", "client_id", cid)
                text = set_in_section(text, "sources.reddit", "client_secret", secret)
                print("Works! Saved.\n" if problem is None else f"Saved, but couldn't verify: {problem}\n")
                break
            print(f"{problem}. Check the short client ID and the secret, then try again.\n")
    else:
        print("OK: Reddit will be read from the free archive.\n")

    # Groups
    dims = {d: [n for n, g in catalog.CATALOG.items() if g["dim"] == d and not g["sensitive"]]
            for d in ("audience", "interest", "region")}
    print("Which groups of people should it cover?")
    for d, names in dims.items():
        print(f"  {d}: {', '.join(names[:8])}{', ...' if len(names) > 8 else ''} ({len(names)} groups)")
    print('  Enter = everything, or e.g. "audience, region" or "parents, teachers, Canada"')
    while True:
        raw = ask("Groups", "everything")
        groups = ["*"] if raw == "everything" else [g.strip() for g in raw.split(",") if g.strip()]
        try:
            catalog.select(groups)
            break
        except ValueError as e:
            print(f"  {e}")
    text = set_in_section(text, "catalog", "groups", groups)
    text = set_in_section(text, "catalog", "include_sensitive",
                          yes("Include health, disability and LGBTQ+ communities?"))

    # Optional extras
    if yes("\nSet up optional extras (Bluesky account, YouTube key)?"):
        handle = ask("Bluesky handle, e.g. you.bsky.social (Enter to skip)")
        if handle:
            text = set_in_section(text, "sources.bluesky", "handle", handle)
            text = set_in_section(text, "sources.bluesky", "app_password",
                                  ask("Bluesky app password (Settings > Privacy and security > App passwords)"))
        key = ask("YouTube Data API key (free, from console.cloud.google.com; Enter to skip)")
        if key:
            text = set_in_section(text, "sources.youtube", "api_key", key)
            text = set_in_section(text, "sources.youtube", "enabled", True)

    config_path.write_text(text, encoding="utf-8")
    print(f"\nSaved settings to {config_path.resolve()}")
    print("To change anything later, run setup again from the menu, or edit that file in a text editor.\n")


# ----------------------------------------------------------------------- menu
def open_path(path: Path) -> None:
    if path.suffix == ".html":
        webbrowser.open(path.resolve().as_uri())
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(path)], check=False)


def show_stats(cfg: dict) -> None:
    store = P.open_store(cfg)
    try:
        c = store.counts()
        print(f"\n{c['posts']:,} posts collected, {c['analyzed']:,} analysed, "
              f"database {store.size_bytes() / 1e6:,.0f} MB")
        for s, n in sorted(c["by_source"].items(), key=lambda kv: -kv[1]):
            print(f"  {s:15} {n:,}")
    finally:
        store.close()


def menu(config_path: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    if not config_path.exists():
        setup(config_path)
    while True:
        cfg = P.load_config(config_path)
        report_path, export_dir = P.output_paths(cfg)
        every = cfg.get("schedule", {}).get("every", "12h")
        print(f"""
=== intenetparser ===
  1  Collect now, then open the report
  2  Keep collecting every {every} (leave this window open; close it to stop)
  3  Open the latest report
  4  Open the files to paste into Claude
  5  How much is collected / disk space
  6  Estimate time for one collection run
  7  Change settings (Reddit app, groups, ...)
  0  Quit""")
        choice = ask("Choose")
        try:
            if choice == "1":
                open_path(P.run_cycle(cfg))
            elif choice == "2":
                interval = P.parse_interval(every)
                first = True
                while True:
                    path = P.run_cycle(P.load_config(config_path))
                    if first:
                        open_path(path)
                        first = False
                    print(f"Next run in {interval / 3600:.1f} h. Refresh the report page to see new data.")
                    time.sleep(interval)
            elif choice == "3":
                if report_path.exists():
                    open_path(report_path)
                else:
                    print("No report yet: choose 1 first.")
            elif choice == "4":
                folder = export_dir / "llm"
                if folder.exists():
                    print("Paste summary.md into Claude first; pack_*.md files hold the posts in batches.")
                    open_path(folder)
                else:
                    print("Nothing exported yet: choose 1 first.")
            elif choice == "5":
                show_stats(cfg)
            elif choice == "6":
                rows = P.plan(cfg)
                for r in rows:
                    print(f"  {r['source']:14} ~{r['items']:>7,} posts  ~{r['minutes']:>4.0f} min  {r['note']}")
                if rows:
                    print(f"  sources run at the same time: about {max(r['minutes'] for r in rows):.0f} min in total")
            elif choice == "7":
                setup(config_path)
            elif choice in ("0", "q", "quit", "exit"):
                return
        except KeyboardInterrupt:
            print("\nStopped.")

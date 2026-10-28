"""Optional: run exported prompt packs through a local LLM.

Works with any OpenAI-compatible chat endpoint, e.g. Ollama
(http://localhost:11434/v1), LM Studio (http://localhost:1234/v1) or
llama.cpp's server. Nothing leaves your machine.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .http import Client

log = logging.getLogger(__name__)


def run_packs(pack_dir: Path, base_url: str, model: str, api_key: str = "",
              timeout: float = 600.0) -> list[Path]:
    client = Client(min_interval=0, timeout=timeout, max_retries=1)
    out_dir = pack_dir / "responses"
    out_dir.mkdir(exist_ok=True)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    written = []
    for pack in sorted(pack_dir.glob("*.md")):
        target = out_dir / pack.name.replace(".md", ".out.md")
        if target.exists():
            log.info("Skipping %s (already done)", pack.name)
            continue
        log.info("Sending %s to %s", pack.name, model)
        data = client.post_json(f"{base_url.rstrip('/')}/chat/completions", {
            "model": model,
            "messages": [{"role": "user", "content": pack.read_text(encoding="utf-8")}],
            "temperature": 0.2,
        }, headers=headers)
        target.write_text(data["choices"][0]["message"]["content"], encoding="utf-8")
        written.append(target)
    return written

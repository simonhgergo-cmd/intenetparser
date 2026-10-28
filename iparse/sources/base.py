from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from typing import Iterator

from ..http import Client
from ..models import Post

_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<\s*(br|/p|p)\s*/?>", re.I)


class Source:
    """A collector for one platform. Subclasses yield Post objects."""

    name = ""

    def __init__(self, cfg: dict, client: Client):
        self.cfg = cfg
        self.client = client
        self.log = logging.getLogger(f"iparse.sources.{self.name}")

    def collect(self) -> Iterator[Post]:
        raise NotImplementedError


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = _BR_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    return html.unescape(text).strip()


def iso_to_epoch(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0

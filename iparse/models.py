from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Post:
    """One piece of public text: a post, comment, review or video caption."""

    source: str
    native_id: str
    text: str
    title: str = ""
    kind: str = "post"  # post | comment | review | video
    community: str = ""
    author: str = ""  # hashed before it is stored
    url: str = ""
    created_utc: float = 0.0
    score: int = 0
    num_comments: int = 0
    parent_id: str = ""
    query: str = ""
    lang: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.source}:{self.native_id}"

    @property
    def full_text(self) -> str:
        return f"{self.title}\n{self.text}".strip()

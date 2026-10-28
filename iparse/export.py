"""Exports: CSV / JSONL for spreadsheets, and prompt packs for an LLM.

The LLM pack is a folder of Markdown files sized to paste into Claude (or
feed to a local model with `iparse llm`). Each file holds instructions plus
a batch of posts that the keyword analyser flagged as containing a problem,
wish or joy, so the model only reads the interesting part of the data.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

POST_PROMPT = """You are analysing public social-media posts to find real problems people have, \
so that someone can build products that solve them.

For EACH post below, return one JSON object per line (JSON Lines), with:
  "id": the post id exactly as given,
  "problems": list of {{"problem": short noun phrase, "severity": 1-5, "evidence": short quote}},
  "wishes": list of things the author wants that don't seem to exist yet,
  "joys": list of things that make the author happy,
  "who": what the author says about themselves (age, role, life situation) or "unknown" - \
do not guess from writing style,
  "product_idea": one sentence, or null if there is no actionable problem.

Skip posts that are jokes, spam or have no real content (return them with empty lists).
Only output JSON Lines, nothing else.

The keyword pre-analysis is included as a hint; it is often wrong, so judge from the text.

---
{posts}
"""

SUMMARY_PROMPT = """Below are problem, wish and joy themes found in {n_posts} public posts \
from {sources}, broken down by audience segment, with example quotes. Counts come from a simple \
keyword analyser, so treat them as rough.

Please:
1. Merge themes that describe the same underlying problem.
2. For each segment, list the 5 most important real problems, with why you think so.
3. Propose 10 product ideas ranked by (pain intensity x how many people x ability to pay x \
ease of building). For each: target segment, problem, solution, how they solve it today, and \
the evidence (quotes) behind it.
4. Point out where the data is too thin or biased to conclude anything.

---
{body}
"""


def export_table(rows, path: Path, fmt: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fmt == "jsonl":
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return len(rows)

    cols = ["id", "source", "kind", "community", "url", "created_utc", "score", "num_comments",
            "title", "text", "sentiment", "segments", "problems", "wishes", "joys", "keyphrases"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([
                *(r.get(c, "") for c in cols[:11]),
                "; ".join(r.get("segments", [])),
                *("; ".join(s["object"] or s["trigger"] for s in r.get(k, [])) for k in ("problems", "wishes", "joys")),
                "; ".join(r.get("keyphrases", [])[:8]),
            ])
    return len(rows)


def _post_block(r: dict, max_text: int) -> str:
    text = f"{r.get('title') or ''}\n{r.get('text') or ''}".strip()
    if len(text) > max_text:
        text = text[:max_text] + " [...]"
    hint = {k: [s["object"] or s["trigger"] for s in r.get(k, [])] for k in ("problems", "wishes", "joys")}
    hint = {k: v for k, v in hint.items() if v}
    segs = [s for s in r.get("segments", []) if not s.startswith("platform:")]
    return (f"### id: {r['id']}\n"
            f"source: {r['source']} | community: {r.get('community', '')} | score: {r.get('score', 0)}\n"
            f"segments: {', '.join(segs) or 'none'} | hint: {json.dumps(hint, ensure_ascii=False)}\n\n"
            f"{text}\n")


def export_llm_pack(rows, out_dir: Path, aggregate_data: dict | None = None,
                    max_chars: int = 60_000, max_text: int = 1500, only_signals: bool = True) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("pack_*.md"):
        old.unlink()
    rows = [r for r in rows if not only_signals or r.get("problems") or r.get("wishes") or r.get("joys")]
    rows.sort(key=lambda r: (len(r.get("wishes", [])) * 2 + len(r.get("problems", [])), r.get("score") or 0),
              reverse=True)

    files: list[Path] = []
    budget = max_chars - len(POST_PROMPT)
    batch: list[str] = []
    size = 0

    def flush():
        if batch:
            p = out_dir / f"pack_{len(files) + 1:03d}.md"
            p.write_text(POST_PROMPT.format(posts="\n".join(batch)), encoding="utf-8")
            files.append(p)

    for r in rows:
        block = _post_block(r, max_text)
        if size + len(block) > budget and batch:
            flush()
            batch, size = [], 0
        batch.append(block)
        size += len(block)
    flush()

    if aggregate_data:
        p = out_dir / "summary.md"
        p.write_text(summary_prompt(aggregate_data), encoding="utf-8")
        files.append(p)
    return files


def summary_prompt(agg: dict, themes_per_kind: int = 12, max_segments: int = 25) -> str:
    lines = []
    segments = sorted(agg["segments"].items(), key=lambda kv: -kv[1]["posts"])[:max_segments]
    for name, seg in segments:
        lines.append(f"## Segment: {name} ({seg['posts']} posts, avg sentiment {seg['avg_sentiment']})")
        topics = ", ".join(t["topic"] for t in seg["topics"][:15])
        lines.append(f"Most discussed: {topics or '-'}")
        for kind in ("problems", "wishes", "joys"):
            items = seg[kind][:themes_per_kind]
            if not items:
                continue
            lines.append(f"\n**{kind.title()}**")
            for t in items:
                quote = t["examples"][0]["quote"].replace("\n", " ") if t["examples"] else ""
                lines.append(f"- {t['theme']} ({t['mentions']} posts) - \"{quote[:200]}\"")
        lines.append("")
    sources = ", ".join(agg["totals"]["by_source"]) or "various sources"
    return SUMMARY_PROMPT.format(n_posts=agg["totals"]["posts"], sources=sources, body="\n".join(lines))

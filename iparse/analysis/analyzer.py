"""Keyword/rule-based analysis of a single post.

For each post this finds:
  * problems: complaints and struggles, with the thing complained about
  * wishes: requests for something that doesn't exist yet
  * joys: what makes people happy
  * sentiment in [-1, 1]
  * keyphrases: the topics the post talks about
  * segments: who is talking (see segments.py)

It is deliberately simple and transparent. For better quality, export the
signal-bearing posts (iparse export llm) and have an LLM review them.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from . import lexicon as L
from .segments import infer_segments

ANALYSIS_VERSION = 1

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'+#&-]*")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_CLAUSE_RE = re.compile(r"[,;:()\[\]\u2013\u2014]|\s-\s")


def _compile(patterns):
    return [(re.compile(p, re.I), w, side) for p, w, side in patterns]


PROBLEMS = _compile(L.PROBLEM_PATTERNS)
WISHES = _compile(L.WISH_PATTERNS)
JOYS = _compile(L.JOY_PATTERNS)
# Emotion words describe how people feel, not what they talk about.
_NON_TOPICS = L.TOPIC_STOPWORDS | set(L.POSITIVE) | set(L.NEGATIVE) | {
    "complete", "total", "wish", "pay", "find", "laid", "honestly", "seriously", "literally", "anyone", "else"}


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower().replace("’", "'"))


def sentences(text: str) -> list[str]:
    text = _URL_RE.sub(" ", text.replace("’", "'"))
    return [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 3]


def normalize_word(w: str) -> str:
    w = w.strip("'-")
    if w.endswith("'s"):
        w = w[:-2]
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is", "ous")):
        return w[:-1]
    return w


def _clean_object(tokens: list[str], max_content: int = 3, max_len: int = 7) -> str:
    """Short phrase from tokens: at most max_content non-stopwords, max_len words in total."""
    out: list[str] = []
    content = 0
    for t in tokens:
        if t in L.OBJECT_BREAKERS and out:
            break
        if not out and t in L.OBJECT_LEAD_DROP:
            continue
        out.append(t)
        content += t not in L.STOPWORDS
        if content >= max_content or len(out) >= max_len:
            break
    while out and out[-1] in L.STOPWORDS:
        out.pop()
    phrase = " ".join(normalize_word(t) for t in out)
    if not phrase or phrase in L.EMPTY_OBJECTS or all(t in L.STOPWORDS for t in out):
        return ""
    return phrase


def extract_object(sentence: str, match: re.Match, side: str) -> str:
    if side == "after":
        return _clean_object(tokenize(_CLAUSE_RE.split(sentence[match.end():], 1)[0]))
    before = tokenize(_CLAUSE_RE.split(sentence[:match.start()])[-1])
    # take the noun phrase right before the verb, e.g. "[the new update] is a mess"
    tail: list[str] = []
    for t in reversed(before):
        if t in L.OBJECT_BREAKERS or (tail and len(tail) >= 4):
            break
        tail.insert(0, t)
    return _clean_object(tail)


def find_signals(text: str) -> dict[str, list[dict]]:
    """Problems, wishes and joys in text. A signal whose object is a pronoun
    ("I would pay for that") borrows the object of the previous signal."""
    found: dict[str, list[dict]] = {"problems": [], "wishes": [], "joys": []}
    last_object = ""
    for sent in sentences(text):
        for kind, compiled in (("problems", PROBLEMS), ("wishes", WISHES), ("joys", JOYS)):
            for rx, weight, side in compiled:
                m = rx.search(sent)
                if not m:
                    continue
                obj = extract_object(sent, m, side) or (last_object if kind != "joys" else "")
                if obj:
                    last_object = obj
                found[kind].append({
                    "kind": kind[:-1] if kind != "wishes" else "wish",
                    "object": obj,
                    "trigger": m.group(0).lower().strip(),
                    "weight": weight,
                    "quote": sent[:300],
                })
                break  # one signal of each kind per sentence
    return found


def sentiment(text: str) -> float:
    tokens = tokenize(text)
    total = 0.0
    for i, tok in enumerate(tokens):
        val = L.POSITIVE.get(tok) or L.NEGATIVE.get(tok)
        if not val:
            continue
        window = tokens[max(0, i - 3):i]
        boost = sum(L.INTENSIFIERS.get(w, 0) for w in window)
        val *= 1 + boost
        if any(w in L.NEGATIONS for w in window):
            val *= -0.75
        total += val
    if text.count("!") and total:
        total *= 1 + min(text.count("!"), 4) * 0.05
    return round(total / math.sqrt(total * total + 15), 4)


def keyphrases(text: str, max_n: int = 3, top: int = 15) -> list[str]:
    """RAKE-style candidate phrases: runs of non-stopwords, up to max_n words."""
    counts: Counter[str] = Counter()
    for sent in sentences(text):
        run: list[str] = []
        for tok in tokenize(sent) + [""]:
            word = normalize_word(tok) if tok else ""
            if word and tok not in L.STOPWORDS and word not in _NON_TOPICS and tok not in _NON_TOPICS \
                    and len(word) > 2 and not any(c.isdigit() for c in word):
                run.append(word)
                continue
            for n in range(1, min(max_n, len(run)) + 1):
                for i in range(len(run) - n + 1):
                    counts[" ".join(run[i:i + n])] += 1
            run = []
    return [p for p, _ in counts.most_common(top)]


def analyze_post(post: dict, community_map: dict | None = None) -> dict:
    text = f"{post.get('title') or ''}\n{post.get('text') or ''}".strip()
    sent = sentiment(text)
    rating = (post.get("meta") or {}).get("rating")
    if rating:  # app store stars are a stronger sentiment signal than words
        sent = round(0.5 * sent + 0.5 * ((int(rating) - 3) / 2), 4)

    signals = find_signals(text)
    problems, wishes, joys = signals["problems"], signals["wishes"], signals["joys"]
    if rating and int(rating) <= 2 and not problems:
        problems = [{"kind": "problem", "object": post.get("community", "").removeprefix("app:").lower(),
                     "trigger": f"{rating}-star review", "weight": 0.7, "quote": text[:300]}]

    return {
        "post_id": post["id"],
        "version": ANALYSIS_VERSION,
        "sentiment": sent,
        "problems": problems,
        "wishes": wishes,
        "joys": joys,
        "keyphrases": keyphrases(text),
        "segments": infer_segments(post, text, community_map),
    }

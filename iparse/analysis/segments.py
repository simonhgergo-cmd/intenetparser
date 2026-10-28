"""Who is talking: rough audience segments.

Platforms do not tell us the age, gender or job of whoever wrote a post, so
segments come from two places only:

  * audience:/interest:/region:<x> - the community a post appeared in
                    (r/Parenting -> audience:parents, r/AusFinance -> region:Australia),
                    from catalog.py. This describes the community, not the individual.
  * age:/gender:/role:/life: - things the author said about themselves
                    ("as a nurse", "I'm 34F", "my toddler"). Self-reported.

Every post also gets platform:<source>. Nothing sensitive (health,
ethnicity, religion, politics, sexuality) is inferred about individuals.
"""
from __future__ import annotations

import re

from ..catalog import community_segments

# community (lowercase) -> segment tags, from the catalog plus a few extras.
# Extend via [segments.communities] in config.
DEFAULT_COMMUNITIES: dict[str, list[str]] = {
    **community_segments(),
    "hackernews": ["audience:tech workers"],
}

ROLE_WORDS: dict[str, str] = {
    "mom": "parent", "mum": "parent", "mother": "parent", "dad": "parent", "father": "parent",
    "parent": "parent", "single mom": "parent", "single dad": "parent", "stay at home mom": "parent",
    "sahm": "parent", "sahd": "parent", "new mom": "parent", "new dad": "parent",
    "student": "student", "college student": "student", "grad student": "student", "phd student": "student",
    "high school student": "student", "freshman": "student", "senior in high school": "student",
    "nurse": "healthcare worker", "doctor": "healthcare worker", "physician": "healthcare worker",
    "pharmacist": "healthcare worker", "paramedic": "healthcare worker", "caregiver": "caregiver",
    "teacher": "teacher", "professor": "teacher", "tutor": "teacher",
    "developer": "tech worker", "software engineer": "tech worker", "programmer": "tech worker",
    "data scientist": "tech worker", "designer": "creative", "artist": "creative", "musician": "creative",
    "writer": "creative", "photographer": "creative", "content creator": "creative",
    "small business owner": "business owner", "business owner": "business owner", "founder": "business owner",
    "entrepreneur": "business owner", "freelancer": "freelancer", "contractor": "trades",
    "electrician": "trades", "plumber": "trades", "mechanic": "trades", "carpenter": "trades",
    "truck driver": "driver", "trucker": "driver", "uber driver": "driver", "delivery driver": "driver",
    "server": "hospitality worker", "bartender": "hospitality worker", "chef": "hospitality worker",
    "cook": "hospitality worker", "barista": "hospitality worker", "cashier": "retail worker",
    "retail worker": "retail worker", "accountant": "office worker", "lawyer": "professional",
    "engineer": "engineer", "manager": "manager", "realtor": "real estate agent",
    "farmer": "farmer", "veteran": "veteran", "retiree": "retiree", "landlord": "landlord",
}

_ROLE_RE = re.compile(
    r"\b(?:i'?m|i am|im|as) (?:an? |a (?:new |single |first[- ]time |young |working )?)"
    r"(" + "|".join(sorted(map(re.escape, ROLE_WORDS), key=len, reverse=True)) + r")s?\b", re.I)
_AGE_RE = re.compile(
    r"\b(?:i'?m|i am|im|as an?|turning|just turned)\s+(\d{2})"
    r"(?:\s*(?:y/?o|yo|years?[- ]old|yrs?[- ]old)\b|(?=\s*(?:[,.!?)]|$|and\b|but\b|now\b|with\b)))", re.I)
# Reddit-style "34F" / "(34f)" / "[M28]". Lowercase only inside brackets ("20m" is usually metres).
_AGE_SEX_RE = re.compile(r"(?:^|[\s(\[])(?:(\d{2})([MF])|([MF])(\d{2}))(?=[\s)\],.!?]|$)")
_AGE_SEX_BRACKET_RE = re.compile(r"[(\[](?:(\d{2})\s?([mfMF])|([mfMF])\s?(\d{2}))[)\]]")
_GENDER_RE = re.compile(r"\b(?:i'?m|i am|im|as) an? (woman|man|guy|girl|female|male|wife|husband|mom|dad|mother|father)\b", re.I)
_LIFE_PATTERNS = [
    (re.compile(r"\bmy (?:kids?|son|daughter|toddler|baby|newborn|children)\b", re.I), "role:parent"),
    (re.compile(r"\b(?:i'?m|i am) pregnant\b", re.I), "life:expecting"),
    (re.compile(r"\b(?:i'?m|i am|im) (?:retired|a retiree)\b", re.I), "role:retiree"),
    (re.compile(r"\bjust graduated\b|\brecent grad\b", re.I), "life:new graduate"),
    (re.compile(r"\b(?:got laid off|been laid off|lost my job|i'?m unemployed|job hunting)\b", re.I), "life:job seeker"),
    (re.compile(r"\bmy landlord\b|\bi rent\b|\bi'?m renting\b", re.I), "housing:renter"),
    (re.compile(r"\bmy mortgage\b|\bbought (?:a|our|my) (?:first )?(?:house|home)\b", re.I), "housing:homeowner"),
    (re.compile(r"\bmy (?:husband|wife)\b", re.I), "life:married"),
    (re.compile(r"\bmy (?:boyfriend|girlfriend|partner|fianc[eé]e?)\b", re.I), "life:in a relationship"),
    (re.compile(r"\bliving alone\b|\bi live alone\b", re.I), "life:lives alone"),
    (re.compile(r"\bmy (?:elderly |aging )?(?:mom|dad|parents?) (?:has|have|with) (?:dementia|alzheimer)", re.I), "role:caregiver"),
]
_GENDER_MAP = {"woman": "woman", "girl": "woman", "female": "woman", "wife": "woman", "mom": "woman",
               "mother": "woman", "man": "man", "guy": "man", "male": "man", "husband": "man",
               "dad": "man", "father": "man", "f": "woman", "m": "man"}


def age_band(age: int) -> str | None:
    if age < 13 or age > 99:
        return None
    for hi, label in ((17, "13-17"), (24, "18-24"), (34, "25-34"), (44, "35-44"), (54, "45-54"), (64, "55-64")):
        if age <= hi:
            return label
    return "65+"


def infer_segments(post: dict, text: str, community_map: dict | None = None) -> list[str]:
    tags: list[str] = [f"platform:{post.get('source', 'unknown')}"]
    custom = {k.lower(): [v if ":" in v else f"audience:{v}" for v in vs]
              for k, vs in (community_map or {}).items()}
    for key in ((post.get("community") or "").lower(), f"{post.get('source')}:{post.get('query') or ''}".lower()):
        tags += custom.get(key) or DEFAULT_COMMUNITIES.get(key, [])

    for m in _ROLE_RE.finditer(text):
        tags.append(f"role:{ROLE_WORDS[m.group(1).lower()]}")
    for m in _AGE_RE.finditer(text):
        band = age_band(int(m.group(1)))
        if band:
            tags.append(f"age:{band}")
    for m in [*_AGE_SEX_RE.finditer(text), *_AGE_SEX_BRACKET_RE.finditer(text)]:
        age = m.group(1) or m.group(4)
        sex = (m.group(2) or m.group(3)).lower()
        band = age_band(int(age))
        if band:
            tags += [f"age:{band}", f"gender:{_GENDER_MAP[sex]}"]
    for m in _GENDER_RE.finditer(text):
        tags.append(f"gender:{_GENDER_MAP[m.group(1).lower()]}")
    for rx, tag in _LIFE_PATTERNS:
        if rx.search(text):
            tags.append(tag)
    return list(dict.fromkeys(tags))

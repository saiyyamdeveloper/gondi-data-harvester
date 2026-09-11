"""Phase 7: Gondi Language Detector (v1).

Flow:
    1. Masaram Gondi Unicode (U+11D00–U+11D5F) mila  -> 'masaram_gondi'
    2. Gunjala Gondi Unicode  (U+11D60–U+11DAF) mila -> 'gunjala_gondi'
    3. Roman text + dictionary hits >= 2 strong words -> 'roman_gondi'
    4. Devanagari + dictionary hits >= 2 strong words -> 'devanagari_gondi'
       (Gondi aksar Hindi ke saath Devanagari mein milta hai)
    5. Bas 1 hit                                  -> 'possible_gondi'
    6. Warna                                      -> 'other'
       ('other' posts bhi corpus mein rehte hain — dashboard par
       "Gondi vs non-Gondi" split dikhane ke liye)

Dictionary: filters/gondi_lexicon.txt  ->  ise badhate rahiye!
Kuch words Hindi mein bhi common hain (sab, koi, hak...) — unhe weight
0.5 diya gaya hai taaki aise ek word se post Gondi na maani jaye.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

MASARAM_RANGE = (0x11D00, 0x11D5F)   # Masaram Gondi block
GUNJALA_RANGE = (0x11D60, 0x11DAF)   # Gunjala Gondi block
DEVANAGARI_RANGE = (0x0900, 0x097F)

LEXICON_PATH = Path(__file__).resolve().parent / "gondi_lexicon.txt"

# Hindi mein bhi aane wale words — half weight (false-positive guard)
ROMAN_AMBIGUOUS = {"sab", "koi", "hak", "mane", "gaurav"}
DEVANAGARI_AMBIGUOUS = {"सब्", "हक्", "कौई", "कोई", "गौरव"}

_STRONG = 1.0
_WEAK = 0.5
_POSITIVE_THRESHOLD = 2.0
_POSSIBLE_THRESHOLD = 1.0

_LEXICON_CACHE: dict | None = None
_TOKEN_RE = re.compile(r"[^\W\d_]+")          # koi bhi letter-run (roman/ISO 15919)
_DEV_TOKEN_RE = re.compile(r"[\u0900-\u097F]+")


def _strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def load_lexicon(path: Path = LEXICON_PATH) -> dict:
    roman: set = set()
    devanagari: set = set()
    target = roman
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            target = devanagari if line.lower() == "[devanagari]" else roman
            continue
        parts = [p.strip() for p in line.split("\t")]
        word = (parts[0] if parts else "").strip().casefold()
        if not word:
            continue
        has_dev = any(DEVANAGARI_RANGE[0] <= ord(c) <= DEVANAGARI_RANGE[1] for c in word)
        target = devanagari if has_dev else roman
        target.add(word)
        if not has_dev:
            folded = _strip_diacritics(word)
            if folded and folded != word:
                target.add(folded)
    return {"roman": roman, "devanagari": devanagari}


def get_lexicon() -> dict:
    global _LEXICON_CACHE
    if _LEXICON_CACHE is None:
        _LEXICON_CACHE = load_lexicon()
    return _LEXICON_CACHE


def _count_range(text: str, lo: int, hi: int) -> int:
    return sum(1 for ch in text if lo <= ord(ch) <= hi)


def _roman_tokens(text: str) -> list:
    return _TOKEN_RE.findall(text.casefold())


def _dev_tokens(text: str) -> list:
    return _DEV_TOKEN_RE.findall(text)


def _score(tokens: list, lex: set, ambiguous: set) -> tuple:
    hits = sorted({t for t in tokens if t in lex})
    weight = sum(_WEAK if h in ambiguous else _STRONG for h in hits)
    return hits, weight


def _result(label: str, confidence: float, details: dict) -> dict:
    return {
        "language": label,
        "confidence": round(confidence, 2),
        "details": details,
    }


def detect(text: str, lexicon: dict | None = None) -> dict:
    """Ek post ka text -> {'language': ..., 'confidence': ..., 'details': ...}"""
    lex = lexicon or get_lexicon()
    text = text or ""

    m = _count_range(text, *MASARAM_RANGE)
    g = _count_range(text, *GUNJALA_RANGE)
    dev_chars = _count_range(text, *DEVANAGARI_RANGE)
    details = {"masaram_chars": m, "gunjala_chars": g, "devanagari_chars": dev_chars}

    # 1-2: Gondi ki apni Unicode lipi — sabse pakka signal
    if m > 0:
        return _result("masaram_gondi", min(1.0, 0.6 + m / 20), details)
    if g > 0:
        return _result("gunjala_gondi", min(1.0, 0.6 + g / 20), details)

    roman_hits, roman_w = _score(_roman_tokens(text), lex["roman"], ROMAN_AMBIGUOUS)
    dev_hits, dev_w = _score(_dev_tokens(text), lex["devanagari"], DEVANAGARI_AMBIGUOUS)
    details["roman_hits"] = roman_hits
    details["devanagari_hits"] = dev_hits
    details["roman_weight"] = roman_w
    details["devanagari_weight"] = dev_w

    # 3: Roman Gondi
    if roman_w >= _POSITIVE_THRESHOLD:
        return _result("roman_gondi", min(1.0, 0.4 + 0.2 * roman_w), details)

    # 4: Devanagari Gondi (mixed Hindi+Gondi)
    if dev_w >= _POSITIVE_THRESHOLD:
        return _result("devanagari_gondi", min(1.0, 0.4 + 0.2 * dev_w), details)

    # 5: bas 1-2 weak hits — review ke liye
    if (roman_w >= _POSSIBLE_THRESHOLD) or (dev_w >= _POSSIBLE_THRESHOLD):
        return _result("possible_gondi", 0.3, details)

    # 6: Gondi nahi dikh raha
    return _result("other", 0.0, details)

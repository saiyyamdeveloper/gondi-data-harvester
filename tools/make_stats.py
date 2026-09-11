#!/usr/bin/env python3
"""data/stats.json banata hai — dashboard aur reports ke liye.

Usage:  python tools/make_stats.py
(run_all.py khud bhi end mein yahi call karta hai)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.corpus import load_corpus  # noqa: E402

CORPUS_JSON = ROOT / "data" / "corpus" / "corpus.json"
STATS_JSON = ROOT / "data" / "stats.json"

GONDI_LABELS = {"masaram_gondi", "gunjala_gondi", "roman_gondi", "devanagari_gondi"}


def word_tokens(text: str) -> list:
    return [t for t in re.split(r"\s+", text or "") if any(c.isalpha() for c in t)]


def build_stats() -> dict:
    posts = load_corpus(CORPUS_JSON)
    by_platform = Counter(p.platform for p in posts)
    by_language = Counter(p.language for p in posts)

    all_words: list = []
    for p in posts:
        all_words += word_tokens(p.text)
    unique = {w.casefold() for w in all_words}

    masaram_chars = sum(1 for p in posts for ch in p.text if 0x11D00 <= ord(ch) <= 0x11D5F)
    gunjala_chars = sum(1 for p in posts for ch in p.text if 0x11D60 <= ord(ch) <= 0x11DAF)

    recent = sorted(posts, key=lambda p: (p.date or "", p.collected_at or ""), reverse=True)[:10]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_posts": len(posts),
        "gondi_posts": sum(by_language.get(l, 0) for l in GONDI_LABELS),
        "possible_gondi": by_language.get("possible_gondi", 0),
        "by_platform": dict(by_platform),
        "by_language": dict(by_language),
        "total_words": len(all_words),
        "unique_words": len(unique),
        "masaram_chars": masaram_chars,
        "gunjala_chars": gunjala_chars,
        "sample_count": sum(1 for p in posts if (p.is_sample or "").strip().lower() in ("yes", "true", "1")),
        "recent": [
            {
                "platform": p.platform,
                "author": p.author,
                "date": p.date,
                "language": p.language,
                "link": p.link,
                "preview": (p.text[:160] + ("…" if len(p.text) > 160 else "")),
            }
            for p in recent
        ],
    }


def main() -> dict:
    stats = build_stats()
    STATS_JSON.parent.mkdir(parents=True, exist_ok=True)
    STATS_JSON.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"stats.json written -> {STATS_JSON}  "
          f"({stats['total_posts']} posts, {stats['gondi_posts']} Gondi)")
    return stats


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Manual / external data ko corpus mein import karta hai.

Har line ek JSON object (JSONL format) — Post ke fields:
    {"platform":"facebook","author":"...","date":"2026-09-01",
     "text":"...","link":"...","is_sample":""}

Usage:
    python tools/import_inbox.py data/inbox/sample_posts.jsonl
    python tools/import_inbox.py data/inbox/facebook_2026-09-01.json   (list bhi chalega)
Bina argument ke: data/inbox/sample_posts.jsonl default.

Pipeline: detect -> dedup -> merge -> save -> stats.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.corpus import load_corpus, merge, save_corpus  # noqa: E402
from database.models import Post  # noqa: E402
from filters.dedup import dedup_posts  # noqa: E402
from filters.gondi_detector import detect  # noqa: E402

CORPUS_JSON = ROOT / "data" / "corpus" / "corpus.json"
CORPUS_CSV = ROOT / "data" / "corpus" / "corpus.csv"


def read_file(path: Path) -> list:
    """JSONL (.jsonl) ya JSON list (.json) — dono handle hokar Post banate hain."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        items = json.loads(raw)
        items = items if isinstance(items, list) else [items]
    else:
        items = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                items.append(json.loads(line))
    posts = []
    for d in items:
        text = (d.get("text") or "").strip()
        if not text:
            continue
        posts.append(Post(
            platform=(d.get("platform") or "manual").strip(),
            author=(d.get("author") or "").strip(),
            date=(d.get("date") or "").strip(),
            text=text,
            link=(d.get("link") or "").strip(),
            is_sample=(d.get("is_sample") or "").strip(),
        ))
    return posts


def main() -> None:
    files = [Path(f) for f in sys.argv[1:]] or [ROOT / "data" / "inbox" / "sample_posts.jsonl"]
    new: list = []
    for f in files:
        if not f.exists():
            print(f"[warn] {f} nahi mila")
            continue
        got = read_file(f)
        print(f"{f.name}: {len(got)} posts padhe")
        new += got

    for p in new:
        p.language = detect(p.text)["language"]
    new, internal_dups = dedup_posts(new)

    existing = load_corpus(CORPUS_JSON, CORPUS_CSV)
    merged, added, already = merge(existing, new)
    save_corpus(merged, CORPUS_CSV, CORPUS_JSON)

    print(f"Inbox import : {len(new)} posts  (internal dups: {internal_dups})")
    print(f"Corpus       : {len(existing)} -> {len(merged)}  "
          f"(naye: {added}, pehle se: {already})")
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_stats.py")], check=False)


if __name__ == "__main__":
    main()

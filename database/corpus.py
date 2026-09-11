"""Phase 2 (aadhar) + Phase 8: corpus load / merge / save.

Corpus hamesha `data/corpus/corpus.csv` + `data/corpus/corpus.json` mein
save hota hai. Merge text-content hash se duplicate rokta hai —
same text alag platform se aaye to bhi sirf EK copy rehti hai.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Post, content_hash, write_csv, write_json


def load_corpus(json_path: Path, csv_path: Path = None) -> list:
    """Pehle JSON try karo, warna CSV."""
    json_path = Path(json_path)
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return [Post.from_dict(d) for d in data]
    csv_path = Path(csv_path) if csv_path else json_path.with_suffix(".csv")
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            return [Post.from_dict(row) for row in csv.DictReader(f)]
    return []


def merge(existing: list, new: list) -> tuple:
    """existing + new merge karo; duplicates (id ya text-hash se) skip.
    Returns: (merged, added_count, skipped_count)"""
    merged = list(existing)
    ids = {p.id for p in merged}
    hashes = {content_hash(p.text) for p in merged if p.text}
    added = skipped = 0
    for p in new:
        h = content_hash(p.text) if p.text else ""
        if (p.id and p.id in ids) or (h and h in hashes):
            skipped += 1
            continue
        merged.append(p)
        ids.add(p.id)
        if h:
            hashes.add(h)
        added += 1
    return merged, added, skipped


def save_corpus(posts: list, csv_path: Path, json_path: Path) -> None:
    write_csv(posts, csv_path)
    write_json(posts, json_path)

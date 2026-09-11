"""Phase 2: Data Structure.

Har post ek hi format mein save hoti hai (CSV + JSON dono).

Aapke roadmap wale fields:
    platform, author, date, text, link, language
+ technical fields:
    id (dedup ke liye SHA-256 based), is_sample, collected_at
"""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

# CSV column order (aapke table ke order mein, phir technical fields)
FIELDS = [
    "platform", "author", "date", "text", "link", "language",
    "id", "is_sample", "collected_at",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_text(text: str) -> str:
    """NFKC + casefold + whitespace collapse — hashing/comparison ke liye."""
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def content_hash(text: str) -> str:
    """Text ka SHA-256 hash (normalise karke) — Phase 8: Duplicate Cleaner."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def make_id(platform: str, link: str, text: str) -> str:
    basis = f"{platform}|{link or ''}|{normalize_text(text)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


@dataclass
class Post:
    platform: str
    author: str = ""
    date: str = ""
    text: str = ""
    link: str = ""
    language: str = "unknown"
    id: str = ""
    is_sample: str = ""
    collected_at: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = make_id(self.platform, self.link, self.text)
        if not self.collected_at:
            self.collected_at = now_iso()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Post":
        d = {k: ("" if v is None else v) for k, v in (d or {}).items()}
        extra = {k: v for k, v in d.items() if k not in FIELDS and k != "extra"}
        extra.update(d.get("extra") or {})
        vals = {k: d.get(k, "") for k in FIELDS}
        return cls(**vals, extra=extra)


def write_csv(posts: list, path: Path) -> None:
    """CSV write — utf-8-sig BOM ke saath taaki Excel mein Devanagari/Gondi
    characters sahi dikhain."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for p in posts:
            w.writerow(p.to_dict() if isinstance(p, Post) else dict(p))


def write_json(posts: list, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [p.to_dict() if isinstance(p, Post) else dict(p) for p in posts]
    path.write_text(json_dumps(data), encoding="utf-8")


def json_dumps(data) -> str:
    import json
    return json.dumps(data, ensure_ascii=False, indent=1)

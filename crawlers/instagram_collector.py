"""Phase 6: Instagram Collector — v1 mein SAFE raasta (no scraping).

Instagram public scraping block karta hai aur ToS ke against hai, isliye
v1 mein manual inbox hi reliable raasta hai:

1) Browser se public captions/hashtags copy karo
2) File banao -> data/inbox/instagram_YYYY-MM-DD.json :

   [
     {
       "platform": "instagram",
       "author": "@handle",
       "date": "2026-09-01",
       "text": "Caption + hashtags",
       "link": "https://www.instagram.com/p/...",
       "is_sample": ""
     }
   ]

3) python tools/import_inbox.py data/inbox/instagram_2026-09-01.json
   (Ya run_all.py chhodo — woh apne aap scan kar leta hai.)

Baad mein (v2): apni IG Page ke liye Meta Graph API use kar sakte ho.
Sirf PUBLIC content. Private data kabhi nahi.
"""
from __future__ import annotations

import json
from pathlib import Path

from database.models import Post

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"


def collect(inbox_dir: Path = INBOX) -> list:
    """data/inbox/instagram_*.json files ko Post banakar laata hai."""
    inbox_dir = Path(inbox_dir)
    if not inbox_dir.exists():
        return []
    posts: list = []
    for f in sorted(inbox_dir.glob("instagram_*.json")):
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [warn] {f.name}: JSON nahi parhi ja saki ({e})")
            continue
        for d in items if isinstance(items, list) else [items]:
            text = (d.get("text") or "").strip()
            if not text:
                continue
            posts.append(Post(
                platform="instagram",
                text=text,
                author=(d.get("author") or "").strip(),
                date=(d.get("date") or "").strip(),
                link=(d.get("link") or "").strip(),
                is_sample=(d.get("is_sample") or "").strip(),
            ))
    return posts

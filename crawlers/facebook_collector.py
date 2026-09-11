"""Phase 5: Facebook Collector — v1 mein SAFE raasta (no scraping).

Facebook ki public posts scrape karna bhi unki Terms of Service ke
against hota hai, isliye v1 mein do legitimate tarike:

1) Meta Graph API (best — v1.1 mein script aayegi): apni FB Page ka
   token lekar public posts export karo.
2) Manual inbox (ABHI): browser se public posts copy karke yeh file
   banao -> data/inbox/facebook_YYYY-MM-DD.json :

   [
     {
       "platform": "facebook",
       "author": "Page ka naam",
       "date": "2026-09-01",
       "text": "Post ka poora text / caption",
       "link": "https://www.facebook.com/...",
       "is_sample": ""
     }
   ]

   Fir chalao:  python tools/import_inbox.py data/inbox/facebook_2026-09-01.json
   (Ya chhodo — run_all.py har baar data/inbox ke facebook_*.json ko
   apne aap scan kar leta hai; jo corpus mein pehle se hai woh
   duplicate ke roop mein skip ho jaata hai.)

Sirf PUBLIC posts. Private data kabhi nahi.
"""
from __future__ import annotations

import json
from pathlib import Path

from database.models import Post

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"


def collect(inbox_dir: Path = INBOX) -> list:
    """data/inbox/facebook_*.json files ko Post banakar laata hai."""
    inbox_dir = Path(inbox_dir)
    if not inbox_dir.exists():
        return []
    posts: list = []
    for f in sorted(inbox_dir.glob("facebook_*.json")):
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
                platform="facebook",
                text=text,
                author=(d.get("author") or "").strip(),
                date=(d.get("date") or "").strip(),
                link=(d.get("link") or "").strip(),
                is_sample=(d.get("is_sample") or "").strip(),
            ))
    return posts

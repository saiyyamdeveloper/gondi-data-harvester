#!/usr/bin/env python3
"""LINK INGESTION — koi bhi link do, uska Gondi content corpus mein aayega.

Usage:
    python tools/add_source.py <link-or-file> [--max N]

Examples:
    # YouTube channel (saare recent videos ke transcripts)
    python tools/add_source.py https://www.youtube.com/@gondibhasha_sikhen
    python tools/add_source.py https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxx
    python tools/add_source.py https://youtu.be/XXXXXXXXXXX        # ek video

    # Telegram public channel (latest + purani messages)
    python tools/add_source.py https://t.me/some_gondi_channel

    # Facebook / Instagram page (v1: manual export ki guidance milegi)
    python tools/add_source.py https://www.facebook.com/somepage
    python tools/add_source.py https://www.instagram.com/somepage

    # WhatsApp group (exported .txt file)
    python tools/add_source.py exports/whatsapp_gondwana_group.txt

Flow:  link detect -> harvest -> Gondi detect -> dedup -> corpus -> stats
Har link config/sources.txt mein register hota hai, isliye roz subah ka
auto-harvest bhi yahin se naya data uthata hai.

--max N : YouTube channel ke liye kitne videos lo (default 30)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crawlers.source_collector import detect_platform, harvest_source, register_source  # noqa: E402
from database.corpus import load_corpus, merge, save_corpus  # noqa: E402
from filters.dedup import dedup_posts  # noqa: E402
from filters.gondi_detector import detect  # noqa: E402

CORPUS_JSON = ROOT / "data" / "corpus" / "corpus.json"
CORPUS_CSV = ROOT / "data" / "corpus" / "corpus.csv"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    source = args[0]

    max_videos = 30
    if "--max" in sys.argv:
        max_videos = int(sys.argv[sys.argv.index("--max") + 1])

    plat = detect_platform(source)
    if plat == "unknown":
        raise SystemExit(
            "[error] Yeh link pehchana nahi gaya. Supported: YouTube, Telegram (t.me), "
            "Facebook, Instagram, WhatsApp export .txt file"
        )

    print(f"Source : {source}")
    print(f"Type   : {plat}")
    print("---")

    posts = harvest_source(source, max_videos=max_videos)
    for p in posts:
        p.language = detect(p.text)["language"]
    posts, internal_dups = dedup_posts(posts)

    existing = load_corpus(CORPUS_JSON, CORPUS_CSV)
    merged, added, already = merge(existing, posts)
    save_corpus(merged, CORPUS_CSV, CORPUS_JSON)

    print(f"\nHarvested : {len(posts)}  (internal dups: {internal_dups})")
    print(f"Corpus    : {len(existing)} -> {len(merged)}  (naye: {added}, pehle se: {already})")

    if plat in ("youtube", "telegram", "whatsapp"):
        register_source(source)
        print(f"Registered: config/sources.txt mein save — roz subah ka auto-harvest yahin se bhi chalega")

    subprocess.run([sys.executable, str(ROOT / "tools" / "make_stats.py")], check=False)
    print("Dashboard refresh: https://gondi-corpus.pages.dev (ghar par: python tools/serve_dashboard.py)")


if __name__ == "__main__":
    main()

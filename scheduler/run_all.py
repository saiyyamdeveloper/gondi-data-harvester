#!/usr/bin/env python3
"""Phase 9: Harvester orchestrator — ek command mein poora pipeline.

    Collect (crawlers)
        -> Detect (filters/gondi_detector.py)
        -> Dedup  (filters/dedup.py)
        -> Merge  (database/corpus.py)
        -> Save   (data/corpus/corpus.csv + corpus.json)
        -> Stats  (data/stats.json)

Usage:
    python scheduler/run_all.py
    python scheduler/run_all.py --platforms youtube,telegram
    python scheduler/run_all.py --dry-run     # report do, corpus mat badlo
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.corpus import load_corpus, merge, save_corpus  # noqa: E402
from filters.dedup import dedup_posts  # noqa: E402
from filters.gondi_detector import detect  # noqa: E402

CORPUS_JSON = ROOT / "data" / "corpus" / "corpus.json"
CORPUS_CSV = ROOT / "data" / "corpus" / "corpus.csv"

PLATFORM_MODULES = {
    "youtube": "crawlers.youtube_collector",
    "telegram": "crawlers.telegram_collector",
    "facebook": "crawlers.facebook_collector",
    "instagram": "crawlers.instagram_collector",
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Gondi Data Harvester pipeline")
    ap.add_argument("--platforms", default="youtube,telegram,facebook,instagram",
                    help="comma-separated: youtube,telegram,facebook,instagram")
    ap.add_argument("--dry-run", action="store_true",
                    help="sirf report — corpus update mat karo")
    args = ap.parse_args()

    chosen = [p.strip() for p in args.platforms.split(",") if p.strip()]
    all_posts = []

    # LINK SOURCES — config/sources.txt (YouTube channels, Telegram channels,
    # WhatsApp exports, FB/IG links) — add_source.py se registered
    src_file = ROOT / "config" / "sources.txt"
    if src_file.exists():
        print("\n=== LINK SOURCES ===")
        try:
            from crawlers.source_collector import harvest_source  # noqa: E402
            for line in src_file.read_text(encoding="utf-8").splitlines():
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                print(f"  source: {line[:70]}")
                try:
                    got = harvest_source(line)
                except Exception as e:
                    print(f"    [error] {type(e).__name__}: {e}")
                    got = []
                for p in got:
                    p.language = detect(p.text)["language"]
                print(f"    {len(got)} posts mile")
                all_posts += got
        except Exception as e:
            print(f"  [warn] sources skip kiye: {e}")

    for name in chosen:
        mod = PLATFORM_MODULES.get(name)
        if not mod:
            print(f"[skip] unknown platform: {name}")
            continue
        print(f"\n=== {name.upper()} ===")
        try:
            m = importlib.import_module(mod)
            posts = m.collect()
        except Exception as e:
            print(f"  [error] {type(e).__name__}: {e}")
            posts = []
        for p in posts:
            p.language = detect(p.text)["language"]
        print(f"  {len(posts)} posts mile")
        all_posts += posts

    # Phase 8: internal duplicates hatao
    all_posts, internal_dups = dedup_posts(all_posts)

    # Existing corpus ke saath merge (cross-platform duplicates bhi yahin rokte hain)
    existing = load_corpus(CORPUS_JSON, CORPUS_CSV)
    merged, added, already = merge(existing, all_posts)

    print("\n=== SUMMARY ===")
    print(f"Harvested : {len(all_posts)}  (internal duplicates: {internal_dups})")
    print(f"Corpus    : {len(existing)} -> {len(merged)}  "
          f"(naye: {added}, pehle se maujood: {already})")

    if args.dry_run:
        print("(dry-run: corpus update nahi hua)")
        return

    save_corpus(merged, CORPUS_CSV, CORPUS_JSON)
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_stats.py")], check=False)
    print(f"\nCorpus saved: {CORPUS_CSV}")
    print("Dashboard    : python tools/serve_dashboard.py  ->  http://localhost:8080")


if __name__ == "__main__":
    main()

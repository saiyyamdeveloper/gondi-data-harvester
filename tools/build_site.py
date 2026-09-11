#!/usr/bin/env python3
"""Cloudflare Pages ke liye static site folder banata hai: deploy/site/

Contents:
    index.html                 (dashboard)
    data/stats.json            (dashboard stats)
    data/corpus/corpus.csv     (corpus — public language data)
    data/corpus/corpus.json    (corpus)

Usage:  python tools/build_site.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "deploy" / "site"


def build() -> Path:
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "data" / "corpus").mkdir(parents=True)

    def copy(rel: str, src: Path) -> None:
        if not src.exists():
            raise SystemExit(f"[error] {src} nahi mila — pehle run_all.py / make_stats.py chalao")
        shutil.copyfile(src, SITE / rel)

    copy("index.html", ROOT / "dashboard" / "index.html")
    copy("data/stats.json", ROOT / "data" / "stats.json")
    copy("data/corpus/corpus.csv", ROOT / "data" / "corpus" / "corpus.csv")
    copy("data/corpus/corpus.json", ROOT / "data" / "corpus" / "corpus.json")
    print(f"Site ready: {SITE}")
    return SITE


if __name__ == "__main__":
    build()

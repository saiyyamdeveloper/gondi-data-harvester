"""Phase 3: YouTube Collector.

Sabse aasan aur sabse zyada data dene wala source.

Kaise kaam karta hai:
- config/youtube_videos.txt se video IDs padhta hai (URL bhi chalega)
- Har video ka transcript nikalta hai (youtube-transcript-api — API key NAHI chahiye)
- oembed se title/author (bina key ke)
- Description/transcript ka text Post banata hai
- 1-2 second ka polite delay rakhta hai (rate-limit)

Optional:
- YOUTUBE_API_KEY env var set karo -> config/keywords.json ke keywords se
  naye videos bhi search karke aayenge (YouTube Data API v3).

NOTE: Gondi audio ke auto-captions aksar Hindi hote hain — detector
decide karega ki text Gondi hai ya nahi. Dono useful hain corpus ke liye.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

from database.models import Post

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def parse_video_id(s: str) -> str:
    """URL ke forms se 11-char video ID nikalo."""
    s = (s or "").strip()
    if not s:
        return ""
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    if _ID_RE.fullmatch(s):
        return s
    return ""


def oembed_metadata(video_id: str) -> dict:
    """Bina API key ke title/author."""
    url = (f"https://www.youtube.com/oembed?url="
           f"https://www.youtube.com/watch?v={video_id}&format=json")
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        r.raise_for_status()
        d = r.json()
        return {"title": d.get("title", ""), "author": d.get("author_name", "")}
    except Exception:
        return {"title": "", "author": ""}


def get_transcript(video_id: str) -> str:
    """Video ka transcript (Hindi/English captions) ek string mein."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as e:
        raise RuntimeError("pehle: pip install -r requirements.txt") from e
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=["hi", "en"])
    return " ".join(seg.text for seg in fetched).strip()


def search_videos_api(api_key: str, keyword: str, max_results: int = 5) -> list:
    """YouTube Data API v3 search — sirf key set ho to."""
    r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet", "type": "video", "q": keyword,
        "maxResults": max_results, "key": api_key,
    }, timeout=20)
    r.raise_for_status()
    ids = []
    for item in r.json().get("items", []):
        vid = item.get("id", {}).get("videoId", "")
        if vid:
            ids.append(vid)
    return ids


def collect(config_dir: Path = CONFIG, sleep_secs: float = 1.5) -> list:
    """Main entry — scheduler/run_all.py yahi call karta hai."""
    posts: list = []
    ids: list = []

    vid_file = Path(config_dir) / "youtube_videos.txt"
    if vid_file.exists():
        for line in vid_file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            vid = parse_video_id(line)
            if vid and vid not in ids:
                ids.append(vid)
    else:
        print("  [warn] config/youtube_videos.txt nahi mila")

    # Optional keyword search
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if api_key:
        kw_file = Path(config_dir) / "keywords.json"
        try:
            kw = json.loads(kw_file.read_text(encoding="utf-8"))
        except Exception:
            kw = {"youtube_search": []}
        for k in (kw.get("youtube_search") or [])[:3]:
            try:
                for vid in search_videos_api(api_key, k, 5):
                    if vid not in ids:
                        ids.append(vid)
                print(f"  search '{k}': naye videos mile")
            except Exception as e:
                print(f"  [warn] search '{k}': {e}")

    for vid in ids:
        try:
            text = get_transcript(vid)
        except Exception as e:
            print(f"  [warn] {vid}: transcript nahi mila ({type(e).__name__})")
            continue
        if not text or len(text) < 20:
            print(f"  [skip] {vid}: transcript bohot chhota")
            continue
        meta = oembed_metadata(vid)
        posts.append(Post(
            platform="youtube",
            text=text,
            author=meta.get("author", ""),
            date="",
            link=f"https://www.youtube.com/watch?v={vid}",
        ))
        time.sleep(sleep_secs)
    return posts

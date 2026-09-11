"""LINK INGESTION — koi bhi social media link do, uska Gondi content corpus mein.

Support (v1):
    YouTube     : channel / playlist / video URL -> videos ke transcripts
                  (API key ho to reliable API raasta, warna page scrape)
    Telegram    : public channel URL -> latest messages + ?before= pagination
                  se purani messages (~60-150)
    Facebook    : link save hota hai — v1 mein manual export (ToS, README dekho)
    Instagram   : link save hota hai — v1 mein manual export (ToS, README dekho)
    WhatsApp    : exported chat .txt file -> messages

Config: config/sources.txt — yahan registered har source roz ka harvest mein
apne aap chalta hai. Naya source:  python tools/add_source.py <link>
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from database.models import Post
from .youtube_collector import (
    UA,
    get_transcript,
    oembed_metadata,
    parse_video_id,
    search_videos_api,
)
from .telegram_collector import clean_channel
from .whatsapp_parser import parse_export_file

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "config" / "sources.txt"

_MSG_LINK_RE = re.compile(r"^/(?:s/)?[^/]+/\d+$")


def detect_platform(source: str) -> str:
    u = (source or "").lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "t.me" in u or "telegram" in u:
        return "telegram"
    if "facebook.com" in u or "fb.com" in u:
        return "facebook"
    if "instagram.com" in u or "instagr.am" in u:
        return "instagram"
    if "whatsapp" in u or u.endswith(".txt"):
        return "whatsapp"
    return "unknown"


def register_source(source: str) -> None:
    """config/sources.txt mein source yaad rakho (roz ka harvest ke liye)."""
    source = source.strip()
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = SOURCES_FILE.read_text(encoding="utf-8").splitlines() if SOURCES_FILE.exists() else []
    if source not in existing:
        with open(SOURCES_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{source}\n")


# ---------------- YouTube ----------------

def _yt_videos_from_page(url: str) -> list:
    """Channel/playlist page se video IDs (ytInitialData parse)."""
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}, timeout=25)
    r.raise_for_status()
    html = r.text
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    scope = m.group(1) if m else html
    ids: list = []

    def walk(o) -> None:
        if isinstance(o, dict):
            vr = o.get("videoRenderer")
            if isinstance(vr, dict):
                vid = vr.get("videoId")
                if vid and vid not in ids:
                    ids.append(vid)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    if m:
        try:
            walk(json.loads(m.group(1)))
        except Exception:
            pass
    if not ids:
        for vid in re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', scope):
            if vid not in ids:
                ids.append(vid)
    return ids


def _yt_api_channel_videos(api_key: str, channel_ref: str, max_videos: int) -> list:
    """API key se channel ke videos (reliable raasta)."""
    api = "https://www.googleapis.com/youtube/v3"
    chan_id = None
    if channel_ref.startswith("UC") and len(channel_ref) == 24:
        chan_id = channel_ref
    elif channel_ref.startswith("@"):
        r = requests.get(f"{api}/channels",
                         params={"part": "id", "forHandle": channel_ref, "key": api_key}, timeout=20)
        r.raise_for_status()
        items = r.json().get("items", [])
        if items:
            chan_id = items[0]["id"]
    if not chan_id:
        return []
    ids: list = []
    page_tok = None
    while len(ids) < max_videos:
        params = {
            "part": "contentDetails",
            "playlistId": chan_id.replace("UC", "UU"),
            "maxResults": min(50, max_videos - len(ids)),
            "key": api_key,
        }
        if page_tok:
            params["pageToken"] = page_tok
        r = requests.get(f"{api}/playlistItems", params=params, timeout=20)
        r.raise_for_status()
        j = r.json()
        for it in j.get("items", []):
            vid = it["contentDetails"]["videoId"]
            if vid not in ids:
                ids.append(vid)
        page_tok = j.get("nextPageToken")
        if not page_tok:
            break
    return ids[:max_videos]


def _harvest_youtube(source: str, max_videos: int) -> list:
    posts: list = []
    vid = parse_video_id(source)
    if vid:
        ids = [vid]
    else:
        u = source.strip()
        page_url = u if ("list=" in u) else u.rstrip("/") + "/videos"
        api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
        ids: list = []
        if api_key:
            m = re.search(r"youtube\.com/(@[^/?]+|channel/UC[A-Za-z0-9_-]{22})\b", u)
            if m:
                try:
                    ids = _yt_api_channel_videos(api_key, m.group(1), max_videos)
                except Exception as e:
                    print(f"  [warn] YouTube API: {e}")
        if not ids:
            try:
                ids = _yt_videos_from_page(page_url)[:max_videos]
            except Exception as e:
                print(f"  [warn] channel ki video list nahi aayi: {e}")
                return []
        print(f"  channel se videos mile: {len(ids)}")
    for v in ids:
        try:
            text = get_transcript(v)
        except Exception as e:
            print(f"  [warn] {v}: transcript nahi ({type(e).__name__})")
            continue
        if not text or len(text) < 20:
            print(f"  [skip] {v}: transcript bohot chhota")
            continue
        meta = oembed_metadata(v)
        posts.append(Post(
            platform="youtube",
            text=text,
            author=meta.get("author", ""),
            date="",
            link=f"https://www.youtube.com/watch?v={v}",
        ))
        time.sleep(1.5)
    return posts


# ---------------- Telegram ----------------

def _harvest_telegram(source: str, max_pages: int) -> list:
    """Public channel — latest messages + ?before= pagination se purani bhi."""
    name = clean_channel(source)
    posts: list = []
    seen_links: set = set()
    url = f"https://t.me/s/{name}"
    for page in range(max_pages):
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title_el = soup.select_one(".tgme_channel_info_header_title")
        author = title_el.get_text(" ", strip=True) if title_el else name

        new_on_page = 0
        for msg in soup.select("div.tgme_widget_message"):
            text_el = msg.select_one(".tgme_widget_message_text")
            cap_el = msg.select_one(".tgme_widget_message_caption")
            el = text_el or cap_el
            if el is None:
                continue
            text = el.get_text(" ", strip=True)
            if not text:
                continue
            date = ""
            t = msg.select_one("time[datetime]")
            if t is not None and t.has_attr("datetime"):
                date = t["datetime"][:10]
            link = ""
            for a in msg.find_all("a", href=True):
                href = a["href"].split("?")[0]
                if href.startswith(("http://", "https://")):
                    href = urlparse(href).path
                if _MSG_LINK_RE.match(href):
                    link = "https://t.me" + href
                    break
            if link:
                if link in seen_links:
                    continue
                seen_links.add(link)
            posts.append(Post(platform="telegram", text=text, author=author, date=date, link=link))
            new_on_page += 1

        # agla (purana) page — sabse aakhri ?before= link
        nxt = None
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "before=" in href:
                nxt = href.split("before=")[-1].split("&")[0]
        if not nxt or new_on_page == 0:
            break
        url = f"https://t.me/s/{name}?before={nxt}"
        time.sleep(2.0)
    return posts


# ---------------- Main entry ----------------

def harvest_source(source: str, max_videos: int = 30, max_telegram_pages: int = 3) -> list:
    """Ek source (URL ya WhatsApp file) se posts lao. Returns list[Post]."""
    plat = detect_platform(source)
    if plat == "youtube":
        return _harvest_youtube(source, max_videos)
    if plat == "telegram":
        return _harvest_telegram(source, max_telegram_pages)
    if plat == "whatsapp":
        p = Path(source)
        if not p.exists():
            print(f"  [warn] file nahi mili: {source}")
            return []
        return parse_export_file(p)
    if plat in ("facebook", "instagram"):
        print(f"  [info] {plat} link yaad rakha — v1 mein manual export (README: Facebook/Instagram section)")
        return []
    print(f"  [warn] unknown source type: {source}")
    return []

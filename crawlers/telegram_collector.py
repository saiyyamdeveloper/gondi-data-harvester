"""Phase 4: Telegram Collector — sirf PUBLIC channels.

Public channels ka web preview (t.me/s/channel) bina kisi token ke milta
hai — isme channel ki latest ~20 messages hoti hain: text, media caption,
date aur message link. Private channels nahi milenge (aur na lena chahiye).

Config: config/telegram_channels.txt — ek line mein ek channel.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from database.models import Post

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Message links: /channel/123 ya /s/channel/123 (absolute URL se path nikala jaata hai)
_LINK_RE = re.compile(r"^/(?:s/)?[^/]+/\d+$")


def clean_channel(raw: str) -> str:
    """'@xyz', 'xyz', 't.me/xyz', 'https://t.me/s/xyz/12' — sabse sirf channel name."""
    raw = (raw or "").strip().split("#", 1)[0].strip().split("?")[0].strip("/")
    if "://" in raw:
        p = urlparse(raw)
        host = (p.netloc or "").lower()
        if "t.me" not in host and "telegram" not in host:
            return raw
        parts = [x for x in (p.path or "").split("/") if x]
        if parts and parts[0] == "s":
            parts = parts[1:]
        return parts[0].lstrip("@") if parts else raw
    for prefix in ("t.me/", "telegram.me/", "telegram.dog/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    return raw.lstrip("@").strip("/")


def collect_channel(channel: str, limit: int = 30, timeout: int = 20) -> list:
    name = clean_channel(channel)
    if not name:
        return []
    url = f"https://t.me/s/{name}"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    title_el = soup.select_one(".tgme_channel_info_header_title")
    author = title_el.get_text(" ", strip=True) if title_el else name

    posts: list = []
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
            date = t["datetime"][:10]  # YYYY-MM-DD

        link = ""
        for a in msg.find_all("a", href=True):
            href = a["href"].split("?")[0]
            if href.startswith(("http://", "https://")):
                href = urlparse(href).path
            if _LINK_RE.match(href):
                link = "https://t.me" + href
                break

        posts.append(Post(
            platform="telegram",
            text=text,
            author=author,
            date=date,
            link=link,
        ))
        if len(posts) >= limit:
            break
    return posts


def collect(channels_file: Path = CONFIG / "telegram_channels.txt", limit: int = 30) -> list:
    """Main entry — scheduler/run_all.py yahi call karta hai."""
    posts: list = []
    channels_file = Path(channels_file)
    if not channels_file.exists():
        print("  [warn] config/telegram_channels.txt nahi mila")
        return posts
    for line in channels_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name = clean_channel(line)
        print(f"  channel: t.me/s/{name}")
        try:
            got = collect_channel(name, limit=limit)
        except Exception as e:
            print(f"  [warn] {name}: {type(e).__name__}: {e}")
            got = []
        posts += got
        time.sleep(2.0)  # polite delay
    return posts

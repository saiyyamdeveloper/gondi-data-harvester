"""WhatsApp chat export (.txt) parse karta hai.

Kaise export karein (WhatsApp mobile app):
    Group kholo → upar group name par tap → group info → ⋮ (three dots)
    → "Export chat" → "Without media"
    Ek .txt file banegi — use yahan import karo.

⚠️ PRIVACY (bohot zaroori):
    - Sirf aise groups import karo jinke aap MEMBER ho
    - Yeh corpus PUBLIC hai (GitHub + Cloudflare Pages) — kisi ki private
      baat, photo ya personal data yahan KABHI nahi
    - Export files repo mein commit NAHI hoti (exports/ gitignored hai)
"""
from __future__ import annotations

import re
from pathlib import Path

from database.models import Post

# "11/09/2026, 12:34:56 PM - Name: message"
# (classic 4-digit year aur naya 2-digit year format dono)
LINE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),\s+[\d:]+(?:\s*[APap][Mm])?\s*-\s*([^:]+):\s?(.*)$")


def parse_export_file(path: Path, group_name: str = "") -> list:
    """Ek WhatsApp export .txt -> list[Post]"""
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"[error] file nahi mili: {path}")
    group = group_name or path.stem.replace("_", " ").strip()

    posts: list = []
    cur: dict | None = None

    def flush() -> None:
        nonlocal cur
        if cur and cur["text"].strip():
            posts.append(Post(
                platform="whatsapp",
                author=group,
                date=cur["date"],
                text=cur["text"].strip(),
                link="",
            ))
        cur = None

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if m:
            flush()
            day, mon, year, _sender, text = m.groups()
            if len(year) == 2:
                year = "20" + year
            cur = {"date": f"{int(year):04d}-{int(mon):02d}-{int(day):02d}", "text": text}
        elif line.strip().startswith("["):
            # system message (jaise "X added to group") — skip
            flush()
        elif cur is not None:
            # multi-line message ka aage ka hissa
            cur["text"] += " " + line.strip()
    flush()
    return posts

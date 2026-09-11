"""Phase 8: Duplicate Cleaner.

Ek hi text baar-baar aaye (same platform ya alag platform) to sirf pehli
copy rehti hai. Decision text ke normalise SHA-256 hash par hoti hai —
case/whitespace se nahi rehta.
"""
from __future__ import annotations

from database.models import content_hash


def dedup_posts(posts: list) -> tuple:
    """Returns: (unique_posts, removed_count)"""
    seen: set = set()
    unique: list = []
    removed = 0
    for p in posts:
        h = content_hash(p.text) if p.text else ""
        if not h:
            unique.append(p)
            continue
        if h in seen:
            removed += 1
            continue
        seen.add(h)
        unique.append(p)
    return unique, removed

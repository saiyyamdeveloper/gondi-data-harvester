#!/usr/bin/env python3
"""Pipeline ke core tests:  python tests/test_pipeline.py"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.corpus import load_corpus, merge, save_corpus  # noqa: E402
from database.models import Post  # noqa: E402
from filters.dedup import dedup_posts  # noqa: E402
from filters.gondi_detector import detect  # noqa: E402

failures: list = []


def check(name: str, cond: bool) -> None:
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        failures.append(name)


print("== Detector (Phase 7) ==")
check("masaram gondi (Unicode) detect",
      detect("𑴤𑴤 𑵀")["language"] == "masaram_gondi")
check("gunjala gondi (Unicode) detect",
      detect("𑵶𑶕𑶂𑶋")["language"] == "gunjala_gondi")
check("roman gondi detect",
      detect("Sab maane aru bhayi — koitor bhasha jeevan badhe.")["language"] == "roman_gondi")
check("devanagari gondi (mixed) detect",
      detect("सब् माने कुन् गौरव् अरु अधिकार् ना मांला ते बराबर् ता हक् पुट्ताल।")["language"] == "devanagari_gondi")
check("non-gondi -> other",
      detect("Aaj hum baat karenge Hindi grammar ke baare mein.")["language"] == "other")
check("single ambiguous word -> not roman_gondi",
      detect("Maine yeh video sabke liye banayi hai.")["language"] in ("other", "possible_gondi"))

print("== Dedup (Phase 8) ==")
a = Post(platform="youtube", text="Hello gondi duniya")
b = Post(platform="telegram", text="  hello   GONDI duniya  ")
c = Post(platform="instagram", text="alag text hai yeh")
u, removed = dedup_posts([a, b, c])
check("cross-platform duplicate hataya (case+whitespace se)",
      removed == 1 and len(u) == 2)

print("== Corpus (Phase 2) ==")
tmp = Path(tempfile.mkdtemp())
cs, cj = tmp / "c.csv", tmp / "c.json"
posts = [
    Post(platform="youtube", text="test one", author="x"),
    Post(platform="telegram", text="test two", author="y"),
]
save_corpus(posts, cs, cj)
loaded = load_corpus(cj, cs)
check("save+load count", len(loaded) == 2)
check("text preserved", loaded[0].text == "test one")
m, added, skipped = merge(loaded, [Post(platform="facebook", text="test one")])
check("merge: same text alag platform se -> duplicate",
      added == 0 and skipped == 1 and len(m) == 2)
m2, added2, skipped2 = merge(loaded, [Post(platform="facebook", text="naya text")])
check("merge: naya text add hua", added2 == 1 and len(m2) == 3)

print()
if failures:
    print(f"FAILED: {failures}")
    sys.exit(1)
print("ALL TESTS PASSED")

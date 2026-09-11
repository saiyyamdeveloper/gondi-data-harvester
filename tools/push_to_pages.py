#!/usr/bin/env python3
"""Cloudflare Pages par Gondi dashboard deploy karta hai (Wrangler ke saath).

Env vars (local export se, ya GitHub Secrets se):
    CLOUDFLARE_API_TOKEN    -> token ko "Pages:Edit" permission chahiye
    CLOUDFLARE_ACCOUNT_ID   -> Account > API Tokens page se

Requirements:
    npm (wrangler npx se chalta hai)

Usage:
    python tools/push_to_pages.py              # production deploy
    python tools/push_to_pages.py --preview    # preview URL (test ke liye)
    python tools/push_to_pages.py --name xyz   # project ka naam

Flow:
    1. tools/build_site.py  -> deploy/site/ (index.html + data/)
    2. npx wrangler pages deploy deploy/site --project-name gondi-corpus
    3. Output URL print hota hai

GitHub Actions mein yahi script roz subah harvest ke baad chalti hai
(.github/workflows/daily-harvest.yml) — dashboard hamesha latest rehta hai.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def main() -> None:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not token or not account:
        raise SystemExit("[error] CLOUDFLARE_API_TOKEN aur CLOUDFLARE_ACCOUNT_ID set karo")

    name = "gondi-corpus"
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]
    preview = "--preview" in sys.argv

    # 1) Site folder banao
    from build_site import build  # noqa: E402
    build()

    # 2) Wrangler se deploy
    branch = "preview" if preview else "main"
    cmd = [
        "npx", "--yes", "wrangler", "pages", "deploy", "deploy/site",
        f"--project-name={name}",
        f"--branch={branch}",
        "--commit-dirty=true",
    ]
    env = dict(os.environ)
    env["CLOUDFLARE_API_TOKEN"] = token
    env["CLOUDFLARE_ACCOUNT_ID"] = account
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, env=env, text=True)
    if r.returncode != 0:
        raise SystemExit(f"[error] wrangler deploy failed (exit {r.returncode})")
    print("\n✅ Deploy complete — upar 'Upload Complete' / URL lines dekho.")


if __name__ == "__main__":
    main()

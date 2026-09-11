#!/usr/bin/env python3
"""Dashboard serve karta hai.

Usage:  python tools/serve_dashboard.py [port]
Phir browser mein: http://localhost:8080
"""
from __future__ import annotations

import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.path = "/dashboard/index.html"
        return super().do_GET()

    def log_message(self, fmt, *args):  # quiet logs
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"Gondi Dashboard: http://0.0.0.0:{port}/")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

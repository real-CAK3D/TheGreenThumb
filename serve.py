#!/usr/bin/env python3
"""The Green Thumb web server (Tailscale-only; mounted at /green-thumb/ under the Newsstand).

  GET/PUT /api/yp/vault      the password locker — ENCRYPTED in the browser with CAK3D's passphrase; the server never sees a password
  GET/POST /api/yp/entries   listings CAK3D added himself (no passwords)
Usage: serve.py <site_dir> <host> <port>
"""
import os, subprocess, sys

import gardenweb as gw
from gardenweb import jload, jsave, LOCK

ROOT = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.path.join(ROOT, "private")


class Handler(gw.Handler):
    ROOT = ROOT

    def get_api(self, p):
        if p == "/api/yp/vault":
            self.json(200, jload(os.path.join(PRIVATE, "vault.json"), {}))
            return True
        if p == "/api/yp/entries":
            self.json(200, jload(os.path.join(PRIVATE, "entries.json"), {"entries": []}))
            return True

    def post_api(self, p):
        if p == "/api/yp/vault":
            v = self.body(2_000_000)
            assert set(v) >= {"v", "salt", "iter", "iv", "ct"} and all(isinstance(v[k], str) for k in ("salt", "iv", "ct"))
            with LOCK:
                jsave(os.path.join(PRIVATE, "vault.json"), {k: v[k] for k in ("v", "salt", "iter", "iv", "ct")})
            self.json(200, {"ok": True})
            return True
        if p == "/api/yp/entries":
            ents = self.body(500_000).get("entries")
            assert isinstance(ents, list) and len(ents) < 1000
            keep = ("id", "name", "device", "category", "url", "ip", "ssh", "tailscale", "notes")
            with LOCK:
                jsave(os.path.join(PRIVATE, "entries.json"), {"entries": [{k: str(x.get(k) or "")[:500] for k in keep} for x in ents if isinstance(x, dict)]})
                subprocess.run([sys.executable, os.path.join(ROOT, "build_green_thumb.py"), "--offline"], capture_output=True, timeout=120)   # reprint the book
            self.json(200, {"ok": True})
            return True


if __name__ == "__main__":
    gw.run(Handler, sys.argv[1], sys.argv[2], int(sys.argv[3]))

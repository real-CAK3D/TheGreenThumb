#!/usr/bin/env python3
"""The Green Thumb: copy the directory from the vault (00_Command/The Green Thumb.json — agents keep it current, never with
passwords) and write the page. Runs hourly (green-thumb-sync.timer) and on demand."""
import html, json, os, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
VAULT_FILE = "/home/ubuntu/CAK3D_Garden_Wiki/00_Command/The Green Thumb.json"


def sync():
    r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "cak3d", "cat '%s'" % VAULT_FILE],
                       capture_output=True, text=True, timeout=60)
    data = json.loads(r.stdout)
    assert isinstance(data.get("entries"), list)
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    out = os.path.join(SITE, "data", "green-thumb.json")
    tmp = out + ".tmp"
    json.dump(data, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    return len(data["entries"])


def page():
    css = open(os.path.join(ROOT, "green-thumb.css")).read()
    body = ('<header class="stand-top"><a class="stand-home" href="/" aria-label="The Newsstand">🏪</a><div><h1>The Green Thumb</h1>'
            '<div class="stand-sub">the Garden&#39;s directory</div></div><a class="stand-home" href="/double-wide/" aria-label="The Double Wide">🗞</a></header>'
            '<main class="paper yp"><div class="yp-head"><div class="yp-title">The Green Thumb</div>'
            '<div class="yp-sub">Every device, app, site and project in the Garden network</div></div>'
            '<div class="yp-tools"><input id="yp-q" type="search" placeholder="Search: a name, device, IP, port…" aria-label="Search">'
            '<button type="button" class="btn" id="yp-lock">🔒 Unlock passwords</button>'
            '<button type="button" class="btn ghost" id="yp-add">＋ Add a listing</button></div>'
            '<p class="small" id="yp-msg"></p><div id="yp-list"><p class="small">Opening the book…</p></div>'
            '<p class="small yp-foot">Passwords are locked with your own passphrase and scrambled on this device before they are saved — '
            'the Garden only ever stores scrambled text. Forget the passphrase and they can\'t be recovered, so pick one you\'ll remember.</p></main>')
    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>The Green Thumb</title><link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#3f7d3a">'
           '<link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/icon-192.png">'
           '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">'
           '<style>%s</style><script src="/app.js" defer></script></head><body class="stand yp-page">%s<script src="js/yp.js"></script></body></html>' % (css, body))
    open(os.path.join(SITE, "index.html"), "w").write(doc)


if __name__ == "__main__":
    try:
        n = sync()
        print("green thumb: %d listings" % n)
        json.dump({"paper": "The Green Thumb", "date": __import__("datetime").date.today().isoformat(), "title": "%d listings" % n, "url": ""},
                  open(os.path.join(SITE, "latest.json"), "w"))
    except Exception as ex:
        print("green thumb: vault sync failed (%s) — keeping the last copy" % type(ex).__name__)
    page()

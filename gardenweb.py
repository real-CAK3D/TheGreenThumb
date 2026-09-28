"""Tiny web server kit for the Garden's paper apps (Tailscale-only; HTTPS comes from `tailscale serve`).

Static files with no-cache headers, a same-origin/header check for writes, JSON helpers and Web Push
subscriptions (push/subs.json, keys made by notify.py --init). Each app subclasses Handler and adds routes.
"""
import datetime as dt, functools, http.server, json, os, re, threading

LOCK = threading.Lock()


def jload(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def jsave(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


class Handler(http.server.SimpleHTTPRequestHandler):
    ROOT = "."            # the app's folder (push/ lives here)
    HOST_ORIGIN = None
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json", ".js": "text/javascript", ".json": "application/json"}

    # ---- plumbing
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        if self.path.split("?")[0] == "/sw.js":
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, *a):
        pass

    def json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def trusted(self):
        origin = self.headers.get("Origin")
        ok = not origin or origin == self.HOST_ORIGIN or re.fullmatch(r"https?://terminal-vnic(\.[\w-]+)*(:\d+)?", origin)
        return "1" in (self.headers.get("X-Garden-App"), self.headers.get("X-Double-Wide")) and bool(ok)

    def body(self, limit=4096):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ValueError("too big")
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- routes: subclasses override get_api / post_api and return True when handled
    def get_api(self, path):
        return False

    def post_api(self, path):
        return False

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/push/key":
            return self.json(200, {"key": jload(os.path.join(self.ROOT, "push", "vapid.json"), {}).get("public", "")})
        if p.startswith("/api/"):
            try:
                if self.get_api(p):
                    return
            except Exception:
                return self.json(400, {"ok": False})
            return self.json(404, {"ok": False})
        return super().do_GET()

    def do_PUT(self):
        return self.do_POST()

    def do_POST(self):
        p = self.path.split("?")[0]
        if not p.startswith("/api/"):
            return self.json(404, {"ok": False})
        if not self.trusted():
            return self.json(403, {"ok": False, "message": "Not from the app."})
        try:
            if p == "/api/push/subscribe":
                sub = self.body().get("subscription") or {}
                assert str(sub.get("endpoint", "")).startswith("https://") and (sub.get("keys") or {}).get("p256dh")
                f = os.path.join(self.ROOT, "push", "subs.json")
                with LOCK:
                    subs = [s for s in jload(f, []) if s.get("endpoint") != sub["endpoint"]]
                    subs.append({"endpoint": sub["endpoint"], "keys": sub["keys"], "at": dt.datetime.now().isoformat(timespec="seconds")})
                    jsave(f, subs)
                return self.json(200, {"ok": True, "message": "Notices are on."})
            if self.post_api(p):
                return
        except Exception:
            return self.json(400, {"ok": False, "message": "That request didn't make sense."})
        return self.json(404, {"ok": False})


def run(handler_cls, site, host, port):
    handler_cls.HOST_ORIGIN = "http://%s:%d" % (host, port)
    http.server.ThreadingHTTPServer((host, port), functools.partial(handler_cls, directory=os.path.abspath(site))).serve_forever()


WALLET = os.path.expanduser("~/.hermes/garden/tip-sheet/private/wallet.json")


def wallet_tx(fn):
    """Garden Bucks (pretend money) are one wallet shared by Dime Bags and The Corner Chronicle's seed counter: every change runs
    under a file lock so the two servers and the nightly settle never step on each other. fn(wallet) may edit it; its result is returned."""
    import fcntl
    os.makedirs(os.path.dirname(WALLET), exist_ok=True)
    with open(WALLET + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        w = jload(WALLET, {"balance": 1000, "bets": []})
        out = fn(w)
        jsave(WALLET, w)
        return out

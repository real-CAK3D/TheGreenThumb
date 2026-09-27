#!/usr/bin/env python3
"""The Green Thumb: the Garden's directory, printed as a flip-through phone book (a green hemp pack on the outside).

Copies the directory from the vault (00_Command/The Green Thumb.json — agents keep it current, never with passwords), adds the
listings CAK3D added himself (private/entries.json), and prints one or more pages per device. The password locker (js/gt.js) fills
logins into the cards after CAK3D unlocks it on his own device. Runs hourly (green-thumb-sync.timer), after every added listing,
and on demand. Use --offline to skip the vault copy.
"""
import datetime as dt, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
VAULT_FILE = "/home/ubuntu/CAK3D_Garden_Wiki/00_Command/The Green Thumb.json"
ROOTS_FILE = "/home/ubuntu/CAK3D_Garden_Wiki/00_Command/Bedded Roots.json"
sys.path.insert(0, ROOT)
import flipbook as fb   # noqa: E402
from flipbook import e, page, SEAL, back_codes, mug   # noqa: E402

fb.CSS_FILE = "green-thumb.css"
PER_PAGE = 6


def load(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default if default is not None else {}


def sync():
    r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "cak3d", "cat '%s'" % VAULT_FILE],
                       capture_output=True, text=True, timeout=60)
    data = json.loads(r.stdout)
    assert isinstance(data.get("entries"), list)
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    out = os.path.join(SITE, "data", "green-thumb.json")
    json.dump(data, open(out + ".tmp", "w"), ensure_ascii=False, indent=1)
    os.replace(out + ".tmp", out)
    try:   # Bedded Roots notes (quirks, trouble signs, history) — CHRONIC keeps them in the vault
        r = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "cak3d", "cat '%s'" % ROOTS_FILE], capture_output=True, text=True, timeout=60)
        notes = json.loads(r.stdout)
        json.dump(notes, open(os.path.join(SITE, "data", "roots-notes.json"), "w"), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return len(data["entries"])


def roots_pages(groups, start):
    """BEDDED ROOTS — the field guide: a page per machine (specs, services, quirks, trouble signs, history) and the agents."""
    specs = load(os.path.join(SITE, "data", "roots.json"), {})
    notes = load(os.path.join(SITE, "data", "roots-notes.json"), {}) or load(os.path.join(ROOT, "roots.seed.json"), {})
    machines = specs.get("machines") or {}
    names = list(dict.fromkeys(list(machines) + list(notes.get("devices") or {})))
    pages, index = [], []
    opener = ('<div class="br-open"><div class="br-kicker">The Field Guide</div><h2 class="br-title">Bedded Roots</h2>'
              '<p class="br-intro">Everything growing in the Garden, down to the roots: what each machine is, what it runs, how it behaves, and what it looks like when it\'s sick. '
              'Specs are probed every week%s; quirks and history are kept by CHRONIC.</p><ol class="gt-index">%s<li><a data-goto="%d">The Agents</a></li></ol></div>'
              % ((" (last: %s)" % e(specs.get("probed", "")[:16].replace("T", " "))) if specs.get("probed") else "",
                 "".join('<li><a data-goto="%d">%s</a></li>' % (start + 1 + i, e(nm)) for i, nm in enumerate(names)), start + 1 + len(names)))
    pages.append(page("Bedded Roots", opener, " br-page"))
    for nm in names:
        m, nt = machines.get(nm) or {}, (notes.get("devices") or {}).get(nm) or {}
        rows = [(k, m.get(v)) for k, v in (("Hostname", "host"), ("System", "os"), ("Kernel", "kernel"), ("Architecture", "arch"), ("Processor", "cpu"),
                                            ("Cores", "cores"), ("Memory", "mem_mb"), ("Disk", "disk"), ("Up", "up"), ("Temperature", "temp"), ("Root filesystem", "root"))]
        spec = "".join('<tr><th>%s</th><td>%s</td></tr>' % (e(k), e(("%s MB" % v) if k == "Memory" and v else v)) for k, v in rows if v)
        if m and not m.get("reachable"):
            spec = '<tr><td colspan="2">Couldn\'t reach it at the last probe.</td></tr>'
        if m.get("root") == "ro":
            spec += '<tr><th>⚠</th><td><b>Root filesystem is READ-ONLY</b></td></tr>'
        svc = "".join('<li>%s%s</li>' % (e(x.get("name")), (' <code>%s</code>' % e(x.get("url") or x.get("ip"))) if (x.get("url") or x.get("ip")) else "")
                      for x in groups.get(nm, []) if x.get("category") != "device")
        cont = m.get("containers", "").split()
        lis = lambda xs: "".join("<li>%s</li>" % e(x) for x in xs or [])
        hist = "".join('<li><b>%s</b> %s</li>' % (e(h.get("date")), e(h.get("what"))) for h in nt.get("history") or [] if isinstance(h, dict))
        pages.append(page("Bedded Roots: %s" % nm, ('<div class="br-dev"><div class="br-kicker">Bedded Roots · Machines</div><h2 class="yp-letter">%s</h2><p class="br-role">%s</p>'
                                                   '<div class="br-cols"><div><h4>Specs</h4><table class="br-spec">%s</table>%s</div>'
                                                   '<div>%s%s%s%s</div></div></div>')
                          % (e(nm), e(nt.get("role") or ""), spec or '<tr><td colspan="2">Not probed yet.</td></tr>',
                             ('<h4>Running containers</h4><p class="small">%s</p>' % e(", ".join(cont))) if cont else "",
                             ('<h4>What it runs</h4><ul>%s</ul>' % svc) if svc else "", ('<h4>Quirks</h4><ul>%s</ul>' % lis(nt.get("quirks"))) if nt.get("quirks") else "",
                             ('<h4>Trouble signs</h4><ul class="br-trouble">%s</ul>' % lis(nt.get("trouble_signs"))) if nt.get("trouble_signs") else "",
                             ('<h4>History</h4><ul>%s</ul>' % hist) if hist else "")))
        index.append({"id": "roots-" + nm, "page": start + len(pages) - 1, "name": "Bedded Roots: " + nm,
                      "find": ("bedded roots field guide " + nm + " " + " ".join(str(v) for v in m.values()) + " " + " ".join(nt.get("quirks") or [])).lower()})
    ag = specs.get("agents") or {}
    notes_ag = notes.get("agents") or {}
    cards = "".join('<div class="br-agent"><div class="br-ah">%s<b>%s</b></div><table class="br-spec">%s</table>%s</div>'
                    % (mug(nm, "mug sm"), e(nm), "".join('<tr><th>%s</th><td>%s</td></tr>' % (e(k), e(v)) for k, v in
                                                      (("Jobs", ", ".join(a.get("jobs") or []) or "—"), ("Model", " · ".join(x for x in (a.get("provider"), a.get("model")) if x) or "—"),
                                                       ("Shift", "; ".join(a.get("schedule") or []) or "on call"), ("Gateway", a.get("gateway") or "—"),
                                                       ("Pay this month", ("$%.2f" % a["pay_month"]) if isinstance(a.get("pay_month"), (int, float)) else "—"))),
                       ('<ul>%s</ul>' % "".join("<li>%s</li>" % e(q) for q in (notes_ag.get(nm) or {}).get("quirks") or [])) if (notes_ag.get(nm) or {}).get("quirks") else "")
                    for nm, a in ag.items())
    pages.append(page("Bedded Roots: The Agents", '<div class="br-dev"><div class="br-kicker">Bedded Roots · The Agents</div><h2 class="yp-letter">The Agents</h2><div class="br-agents">%s</div></div>'
                      % (cards or '<p class="small">Not probed yet.</p>')))
    return pages, index


def card(x):
    href = x.get("url") or ""
    if href and not href.startswith(("http://", "https://")):
        href = "http://" + href
    rows = []
    if x.get("url"):
        rows.append('<div class="yp-row"><span>Web</span><a href="%s" target="_blank" rel="noopener">%s</a></div>' % (e(href), e(x["url"])))
    for label, k in (("IP", "ip"), ("Tailscale", "tailscale")):
        if x.get(k):
            rows.append('<div class="yp-row"><span>%s</span><code>%s</code></div>' % (label, e(x[k])))
    if x.get("ssh"):
        rows.append('<div class="yp-row"><span>SSH</span><code>%s</code><button type="button" class="yp-mini" data-copy="%s">📋</button></div>' % (e(x["ssh"]), e(x["ssh"])))
    locked = '<div class="yp-row locked"><span>Password</span><code>🔒 ••••••••</code></div>' if x.get("has_login") else ""
    return ('<div class="yp-card" data-id="%s" data-find="%s"><div class="yp-name"><b>%s</b>%s</div>%s%s<div class="yp-creds" data-id="%s">%s</div></div>'
            % (e(x.get("id")), e(" ".join(str(x.get(k) or "") for k in ("name", "device", "category", "url", "ip", "ssh", "tailscale", "notes")).lower()),
               e(x.get("name")), ('<span class="tag">%s</span>' % e(x["category"])) if x.get("category") else "",
               ('<div class="small">%s</div>' % e(x["notes"])) if x.get("notes") else "", "".join(rows), e(x.get("id")), locked))


def build():
    data = load(os.path.join(SITE, "data", "green-thumb.json"), {"entries": []})
    mine = load(os.path.join(ROOT, "private", "entries.json"), {"entries": []}).get("entries") or []
    entries = [x for x in (data.get("entries") or []) + mine if isinstance(x, dict) and x.get("name")]
    groups = {}
    for x in entries:   # keep the book's order: devices in the order the directory lists them
        groups.setdefault(x.get("device") or "Other", []).append(x)
    today = dt.date.today()
    # page 1 = the cover, 2 = how to use, then the sections: work out where each one starts so the index can turn to it
    starts, index, n = {}, [], 3
    for g, items in groups.items():
        starts[g] = n
        n += (len(items) + PER_PAGE - 1) // PER_PAGE
    pages = [page("How to Use", '<div class="box gt-howto"><h2>How to use The Green Thumb</h2><ul>'
                  '<li><b>Search</b> above the book — it turns straight to the page and lights up the listing.</li>'
                  '<li><b>🔒 Unlock passwords</b> with your own passphrase: logins appear on the cards, hidden behind •••••••• until you tap 👁 View.</li>'
                  '<li><b>⬆ Import</b> a password-manager export (.csv) once unlocked — it is read and scrambled on your device, never uploaded as-is.</li>'
                  '<li><b>＋ Add a listing</b> for anything the agents haven&#39;t filed yet. The agents add new apps and devices on their own.</li></ul>'
                  '<h4>In this book — tap a section</h4><ol class="gt-index">%s</ol></div>'
                  % ("".join('<li><a data-goto="%d">%s <span class="small">(%d)</span></a></li>' % (starts[g], e(g), len(v)) for g, v in groups.items())
                     + '<li><a data-goto="%d"><b>🌱 Bedded Roots — the field guide</b></a></li>' % n))]
    for g, items in groups.items():
        for n in range(0, len(items), PER_PAGE):
            part = items[n:n + PER_PAGE]
            title = g if len(items) <= PER_PAGE else "%s (%d of %d)" % (g, n // PER_PAGE + 1, (len(items) + PER_PAGE - 1) // PER_PAGE)
            for x in part:
                index.append({"id": x.get("id"), "page": starts[g] + n // PER_PAGE, "name": x.get("name"),
                              "find": " ".join(str(x.get(k) or "") for k in ("name", "device", "category", "url", "ip", "ssh", "tailscale", "notes")).lower()})
            pages.append(page(title, '<h2 class="yp-letter">%s</h2><div class="yp-grid">%s</div>' % (e(title), "".join(card(x) for x in part))))
    roots, roots_index = roots_pages(groups, len(pages) + 2)   # the field guide follows the directory
    pages += roots
    index += roots_index
    seal = '<a class="seal" href="/" aria-label="Back to The Corner Chronicle" title="Back to The Corner Chronicle">%s</a>' % SEAL
    front = page("The Green Thumb", (
        '<div class="gum"><span>ORGANIC · THE GARDEN DIRECTORY · %d LISTINGS</span></div>'
        '<div class="pc-top">%s<div class="ear">N° %d<br>%s<br><b>%s</b><br>%s</div></div>'
        '<div class="flag"><div class="est">ORGANIC · GROWN IN THE GARDEN</div><h1>The Green<br>Thumb</h1><div class="motto hemp">EVERY DEVICE · APP · LOGIN</div></div>'
        '<div class="pc-band"><span>DEVICES</span><span>APPS</span><span>LOGINS</span></div>'
        '<div class="pc-teaser"><div class="kicker">In this book</div><b>%d listings across %d sections</b></div><div class="pc-open">Let your fingers do the walking ›</div>')
        % (len(entries), seal, len(entries), today.strftime("%a"), today.strftime("%b %-d"), today.strftime("%Y"), len(entries), len(groups)), " hardcover")
    back = page("Back Page", (
        '<div class="gum"><span>THE GREEN THUMB · THE GARDEN</span></div>'
        '<div class="pb-body">%s<h2 class="pb-title">The Green Thumb</h2>'
        '<p>Kept current by the Garden\'s agents from the vault.<br>Passwords live only in your locker — scrambled on your device, never in the book.</p>'
        '%s<p class="pb-code">Updated %s</p></div>')
        % (seal, back_codes("https://github.com/real-CAK3D/TheGreenThumb", "TheGreenThumb"), today.isoformat()), " hardcover back")
    toolbar = ('<div class="gt-tools"><input id="yp-q" type="search" placeholder="Search: a name, device, IP, port…" aria-label="Search">'
               '<button type="button" class="btn" id="yp-lock">🔒 Unlock passwords</button>'
               '<button type="button" class="btn ghost" id="yp-add">＋ Add a listing</button><span class="small" id="yp-msg"></span></div>')
    html = fb.book([front] + pages + [back], date=today.isoformat(), no=len(entries), lists={}, paper="The Green Thumb",
                   motto="Every device, app & login in the Garden", gum="ORGANIC · THE GARDEN DIRECTORY", price="PRICE: FREE TO GROW",
                   delivered="KEPT BY THE AGENTS", flap="The Green Thumb · the Garden's directory", body_class="pub-gt",
                   est="ORGANIC · GROWN IN THE GARDEN", toolbar=toolbar, scripts='<script>window.GT_INDEX = %s;</script><script src="js/gt.js"></script>' % json.dumps(index).replace("<", "\\u003c"))
    open(os.path.join(SITE, "index.html"), "w").write(html.replace('href="../', 'href="').replace('src="../', 'src="'))
    json.dump({"paper": "The Green Thumb", "date": today.isoformat(), "title": "%d listings" % len(entries), "url": ""},
              open(os.path.join(SITE, "latest.json"), "w"))
    return len(entries)


if __name__ == "__main__":
    if "--offline" not in sys.argv:
        try:
            print("green thumb: %d listings from the vault" % sync())
        except Exception as ex:
            print("green thumb: vault sync failed (%s) — keeping the last copy" % type(ex).__name__)
    print("green thumb: printed %d listings" % build())

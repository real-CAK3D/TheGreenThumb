#!/usr/bin/env python3
"""Render an edition of THE DOUBLE WIDE (CAK3D's morning paper) as a turn.js flipbook.

Usage: render_double_wide.py <edition.json>
Writes site/editions/<date>.html, refreshes site/index.html (latest) and site/archive.html.
Edition JSON is written each morning by Ganja; weather comes from site/data/weather-<date>.json.
Pages turn with turn.js (personal-use license, loaded from cdnjs) — desktop shows two-page spreads,
phones one page; drag a corner, swipe, or use the arrow buttons. Job Listings are clickable
(approve / mark done / not now) via serve.py's /api/jobs.
"""
import datetime as dt, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
CSS_FILE = "double-wide.css"   # sister papers that reuse this flipbook point this at their own stylesheet
AGENTS = {
    "Ganja": "ganja", "The Gardiner": "gardener", "Gardiner": "gardener", "CHRONIC": "chronic", "Chronic": "chronic",
    "Maple": "maple", "Herbie": "herbie", "Homie": "homie", "Ibby": "ibby", "Disco Stu": "discostu", "BAK3R": "bak3r",
    "CYPH3R": "cyph3r", "Clydius": "clydius", "tinyZ": "tinyz", "tiny-Z": "tinyz", "Fat Man": "fatman", "Little Boy": "littleboy", "B.I.G": "big",
}
COMIC_BG = ["#ffd84d", "#7fd3f7", "#ff9fb2", "#b7e36b", "#ffb347", "#c9a7ff"]
e = lambda s: html.escape(str(s or ""))


def para(text):
    out = []
    for p in re.split(r"\n\s*\n", str(text or "").strip()):
        if p:
            p = e(p).replace("\n", "<br>")
            out.append("<p>" + re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p) + "</p>")
    return "".join(out)


def mug(agent, cls="mug"):
    slug = AGENTS.get(str(agent or "").strip())
    if slug and os.path.exists(os.path.join(SITE, "img", slug + ".png")):
        return '<img class="%s" src="../img/%s.png" alt="%s">' % (cls, slug, e(agent))
    if agent:
        return '<span class="%s mono" aria-hidden="true">%s</span>' % (cls, e(str(agent)[:1]))
    return ""


def story(s, lead=False):
    if not isinstance(s, dict):
        return ""
    tag = '<div class="kicker">%s</div>' % e(s.get("tag")) if s.get("tag") else ""
    by = '<div class="byline">%s<span>By %s</span></div>' % (mug(s.get("agent")), e(s.get("agent"))) if s.get("agent") else ""
    dek = '<p class="dek">%s</p>' % e(s.get("dek")) if s.get("dek") else ""
    return '<article class="%s">%s<h3>%s</h3>%s%s%s</article>' % (
        "story lead" if lead else "story", tag, e(s.get("title")), dek, by, para(s.get("body")))


WX_ICONS = [("thunder", "⛈"), ("snow", "❄"), ("sleet", "🌨"), ("rain", "🌧"), ("shower", "🌦"), ("drizzle", "🌦"),
            ("fog", "🌫"), ("partly", "⛅"), ("mostly cloudy", "☁"), ("cloudy", "☁"), ("overcast", "☁"),
            ("mostly sunny", "🌤"), ("sunny", "☀"), ("clear", "☀"), ("wind", "💨")]


def wx_icon(text):
    t = str(text or "").lower()
    return next((i for k, i in WX_ICONS if k in t), "🌤")


def weather_block(date):
    try:
        w = json.load(open(os.path.join(SITE, "data", "weather-%s.json" % date)))
    except Exception:
        return '<div class="box weather"><h2>Weather</h2><p>The weather desk overslept.</p></div>'
    now = w.get("now") or {}
    days = w.get("days") or []
    if not days:  # older weather files: build day cards from the forecast periods
        ps = w.get("periods") or []
        days = [{"name": p.get("name"), "high": p.get("temp"), "low": None, "short": p.get("short")}
                for p in ps if "night" not in str(p.get("name", "")).lower()][:3]
    cards = "".join(
        '<div class="wx-day"><div class="wx-dname">%s</div><div class="wx-icon">%s</div>'
        '<div class="wx-hl"><b>%s°</b>%s</div><div class="wx-short">%s</div>%s</div>'
        % (e(str(d.get("name", ""))[:3].upper() if d.get("name") not in ("Today", "Tonight", "This Afternoon") else "TODAY"),
           wx_icon(d.get("short")), e(d.get("high")), (" / %s°" % e(d.get("low"))) if d.get("low") is not None else "",
           e(d.get("short")), ('<div class="wx-pop">💧 %s%%</div>' % e(d.get("pop"))) if d.get("pop") else "")
        for d in days[:3])
    return ('<div class="box weather"><h2>Weather</h2><div class="wx-now"><span class="wx-bigicon">%s</span>'
            '<span class="wx-temp">%s°</span><span>%s<br><small>%s · humidity %s%%</small></span></div>'
            '<div class="wx-3day"><div class="wx-label">3-Day Forecast</div><div class="wx-days">%s</div></div>'
            '<p class="small">%s</p></div>'
            % (wx_icon(now.get("text")), e(now.get("temp_f")), e(now.get("text")), e(w.get("place")), e(now.get("humidity")),
               cards, e((w.get("today") or {}).get("detail"))))


def jobs_block(items):
    rows = []
    for i, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        rows.append(
            '<button type="button" class="ad job" data-idx="%d">%s<div class="job-txt"><b>%s</b>%s'
            '<div>%s</div>%s<div class="job-status" data-status="open">Tap to approve or handle ›</div></div></button>'
            % (i, mug(it.get("agent"), "mug sm"), e(it.get("title")),
               (' <span class="tag">%s</span>' % e(it.get("agent"))) if it.get("agent") else "",
               e(it.get("details") or it.get("text")),
               ('<div class="ask">➜ %s</div>' % e(it.get("ask"))) if it.get("ask") else ""))
    return "".join(rows) or '<p class="small">No job listings today. Everybody\'s employed.</p>'


def ads_block(items):
    rows = []
    for it in items or []:
        if isinstance(it, dict):
            rows.append('<div class="ad">%s<div><b>%s</b>%s<div>%s</div></div></div>'
                        % (mug(it.get("agent"), "mug sm"), e(it.get("title")),
                           (' <span class="tag">%s</span>' % e(it.get("agent"))) if it.get("agent") else "",
                           e(it.get("details") or it.get("text"))))
    return "".join(rows) or '<p class="small">No want ads today.</p>'


def comic(fun):
    panels = []
    for i, p in enumerate(fun.get("panels") or []):
        if not isinstance(p, dict):
            p = {"caption": p}
        cast = p.get("cast") or ([{"agent": p.get("agent"), "says": p.get("says") or p.get("caption")}] if p.get("agent") else [])
        narr = p.get("caption") if p.get("cast") or p.get("says") else (p.get("narration") or "")
        people = "".join(
            '<div class="actor">%s%s</div>' % (
                ('<div class="bubble">%s</div>' % e(c.get("says"))) if c.get("says") else "", mug(c.get("agent"), "mug toon"))
            for c in cast if isinstance(c, dict))
        panels.append(
            '<div class="cpanel" style="--bg:%s">%s%s<div class="stage">%s</div></div>'
            % (COMIC_BG[i % len(COMIC_BG)], ('<div class="narr">%s</div>' % e(narr)) if narr else "",
               ('<div class="sfx">%s</div>' % e(p.get("sfx"))) if p.get("sfx") else "", people))
    return ('<div class="sunday"><div class="sunday-head"><span>THE</span> SUNDAY FUNNIES</div>'
            '<div class="comic-title">%s</div><div class="cpanels">%s</div>%s</div>'
            % (e(fun.get("title")), "".join(panels), ('<p class="joke">%s</p>' % e(fun.get("joke"))) if fun.get("joke") else ""))



def _streak(h):
    if not h:
        return ""
    d, hh = int(h // 24), int(h % 24)
    return ("%dd %dh" % (d, hh)) if d else ("%dh" % hh)


def coming_block(items):
    rows = "".join('<li><span class="cu-when">%s</span>%s<span>%s</span></li>' % (e(x.get("when")), mug(x.get("agent"), "mug xs"), e(x.get("what")))
                   for x in items or [] if isinstance(x, dict))
    return '<div class="box coming"><h2>Coming Up</h2><ul class="cu">%s</ul></div>' % (rows or "<li>Nothing on the calendar. Enjoy it.</li>")


def market_block(m):
    items = [x for x in (m or []) if isinstance(x, dict)]
    if not items:
        return ('<div class="market-teaser"><div class="kicker">Coming soon</div><h3>B.I.G opens for business</h3>'
                '<p>The Budding Investment Garden is setting up shop. Once B.I.G is online, this page carries fresh ways to make quick cash '
                'and resale finds every morning — each one with what it takes and what it might pay.</p>'
                '<p class="small">Until then, this shelf stays empty on purpose: no made-up money tips.</p></div>')
    return "".join('<div class="ad">%s<div><b>%s</b>%s<div>%s</div>%s</div></div>'
                   % (mug(x.get("agent") or "B.I.G", "mug sm"), e(x.get("title")),
                      (' <span class="tag">%s</span>' % e(x.get("tag"))) if x.get("tag") else "", e(x.get("text")),
                      ('<div class="ask">➜ %s</div>' % e(x.get("payoff"))) if x.get("payoff") else "") for x in items)



def _k(n):
    n = float(n or 0)
    return ("%.1fM" % (n / 1e6)) if n >= 1e6 else ("%.0fk" % (n / 1e3)) if n >= 1e3 else "%d" % n


def tokens_block(date):
    try:
        u = json.load(open(os.path.join(SITE, "data", "usage-%s.json" % date)))
    except Exception:
        return '<div class="box tokens"><h2>Token Tracker</h2><p class="small">No usage figures today.</p></div>'
    hrs = u.get("hours") or [0] * 24
    top = max(hrs) or 1
    peak = max(range(24), key=lambda h: hrs[h])
    bars = "".join('<div class="tk-bar%s" title="%s:00 — %s tokens"><span style="height:%d%%"></span><i>%s</i></div>'
                   % (" peak" if h == peak and hrs[h] else "", h, _k(hrs[h]), max(2, round(hrs[h] / top * 100)) if hrs[h] else 0,
                      (str(h % 12 or 12) + ("a" if h < 12 else "p")) if h % 3 == 0 else "") for h in range(24))
    def table(title, d, is_agent=False):
        d = d or {}
        mx = max(d.values()) if d else 1
        rows = "".join('<li>%s<span class="tk-name">%s</span><span class="tk-meter"><span style="width:%d%%"></span></span><b>%s</b></li>'
                       % (mug(k, "mug xs") if is_agent else "", e(k), max(3, round(v / mx * 100)), _k(v)) for k, v in list(d.items())[:10])
        return '<div class="tk-list"><h4>%s</h4><ul>%s</ul></div>' % (title, rows or "<li>—</li>")
    return ('<div class="box tokens"><h2>Token Tracker</h2>'
            '<div class="tk-sum"><div><b>%s</b><small>tokens</small></div><div><b>%s</b><small>cached reads</small></div>'
            '<div><b>~%s</b><small>Hermes API calls</small></div><div><b>%s:00</b><small>busiest hour</small></div></div>'
            '<div class="tk-chart">%s</div>'
            '<div class="tk-grid">%s%s%s</div><p class="small">%s%s</p></div>'
            % (_k(u.get("total")), _k(u.get("cache_read")), e(u.get("calls")), peak, bars,
               table("By agent", u.get("by_agent"), True), table("By model", u.get("by_model")), table("By provider", u.get("by_provider")),
               e(u.get("note")), "" if u.get("pc_included") else " PC usage (Claude Code / Codex) not included today."))




# ---------------------------------------------------------------- newspaper sections
def sec(name, kicker=""):
    return ('<div class="sec-banner"><span class="sec-name">%s</span>%s</div>'
            % (e(name), ('<span class="sec-kick">%s</span>' % e(kicker)) if kicker else ""))


# ---------------------------------------------------------------- Section B: the Garden Token Average (a DOW for tokens)
SYMBOLS = {"Ganja": "GNJA", "The Gardiner": "GRDN", "CHRONIC": "CHRN", "Maple": "MAPL", "Herbie": "HRBE", "Homie": "HOMY", "Ibby": "IBBY",
           "Disco Stu": "STU", "BAK3R": "BAKR", "CYPH3R": "CYPH", "Clydius": "CLYD", "tinyZ": "TNYZ", "Fat Man": "FATM", "Little Boy": "LTLB",
           "B.I.G": "BIG"}


def sym(name):
    return SYMBOLS.get(name) or (re.sub(r"[^A-Za-z]", "", str(name)).upper()[:4] or "?")


def _chg(now, before):
    if not before:
        return "new", "flat", "—"
    pct = (now - before) / before * 100
    cls = "up" if pct > 0.5 else "down" if pct < -0.5 else "flat"
    return "%s%.1f%%" % ("▲" if pct > 0 else "▼" if pct < 0 else "", abs(pct)), cls, ("%+.0fk" % ((now - before) / 1000))


AGENT_COLORS = ["#1f3a5f", "#b3261e", "#1f7a3a", "#c77d12", "#6a3d9a", "#0f7c8c", "#8c564b", "#d4508a"]


def _axis_k(v):
    return ("%.1fM" % (v / 1e6)) if v >= 1e6 else ("%dk" % round(v / 1e3)) if v >= 1e3 else "%d" % v


def _nice_top(v):
    if v <= 0:
        return 1
    mag = 10 ** (len(str(int(v))) - 1)
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * mag >= v:
            return m * mag
    return v


def market_chart(u, pu):
    """Intraday chart like a stock page: cumulative tokens stacked by the top agents, yesterday's session dashed for
    comparison, hourly volume in a lower pane coloured by the hour's biggest burner with a 3-hour moving average,
    and the day's peak marked."""
    hrs = u.get("hours") or [0] * 24
    ah = u.get("agent_hours") or {}
    top = [k for k, _ in sorted(((k, sum(v)) for k, v in ah.items()), key=lambda kv: -kv[1])[:6]]
    series = [(k, ah[k]) for k in top]
    other = [max(0, hrs[i] - sum(v[i] for _, v in series)) for i in range(24)]
    if sum(other) > 0:
        series.append(("everyone else", other))
    if not series:
        series = [("all agents", hrs)]
    color = {k: (AGENT_COLORS[i % len(AGENT_COLORS)] if k != "everyone else" else "#9a8f7e") for i, (k, _) in enumerate(series)}
    cum = [sum(hrs[:i + 1]) for i in range(24)]
    pcum = [sum((pu.get("hours") or [0] * 24)[:i + 1]) for i in range(24)] if pu else None
    ymax = _nice_top(max(cum[-1], (pcum[-1] if pcum else 0)) * 1.05)
    W, L, R, T, H1, GAP, H2 = 900, 58, 12, 16, 250, 34, 90
    PAD = (W - L - R) / 48.0
    X = lambda i: L + PAD + i * (W - L - R - 2 * PAD) / 23.0
    Y = lambda v: T + H1 - v / ymax * H1
    out = []
    for g in range(5):   # price gridlines + labels
        v = ymax * g / 4
        out.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text class="yl" x="%d" y="%.1f">%s</text>' % (L, W - R, Y(v), Y(v), L - 6, Y(v) + 4, _axis_k(v)))
    for i in range(0, 24, 3):
        out.append('<line class="grid v" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (X(i), X(i), T, T + H1 + GAP + H2))
    base = [0.0] * 24   # stacked cumulative areas, biggest agent at the bottom
    for k, v in series:
        run, top_line = 0, []
        for i in range(24):
            run += v[i]
            top_line.append(base[i] + run)
        pts = " ".join("%.1f,%.1f" % (X(i), Y(top_line[i])) for i in range(24))
        back = " ".join("%.1f,%.1f" % (X(i), Y(base[i])) for i in range(23, -1, -1))
        out.append('<polygon class="stack" fill="%s" points="%s %s"><title>%s: %s</title></polygon>' % (color[k], pts, back, e(k), _axis_k(sum(v))))
        base = top_line
    if pcum:
        out.append('<polyline class="prev" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), Y(pcum[i])) for i in range(24)))
    out.append('<polyline class="close" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), Y(cum[i])) for i in range(24)))
    peak = max(range(24), key=lambda h: hrs[h])
    out.append('<circle class="pk" cx="%.1f" cy="%.1f" r="5"/><text class="note" x="%.1f" y="%.1f">Peak hour %s · %s</text>'
               % (X(peak), Y(cum[peak]), min(X(peak) + 8, W - 160), max(Y(cum[peak]) - 8, T + 12), (str(peak % 12 or 12) + ("a" if peak < 12 else "p")), _axis_k(hrs[peak])))
    out.append('<text class="note end" x="%d" y="%.1f">Close %s</text>' % (W - R - 2, Y(cum[-1]) - 8 if Y(cum[-1]) > T + 20 else Y(cum[-1]) + 16, _axis_k(cum[-1])))
    vt = _nice_top(max(hrs) or 1)
    y0 = T + H1 + GAP
    for g in (0, 0.5, 1):
        out.append('<text class="yl" x="%d" y="%.1f">%s</text>' % (L - 6, y0 + H2 - H2 * g + 4, _axis_k(vt * g)))
    bw = (W - L - R - 2 * PAD) / 24.0
    for i in range(24):
        if hrs[i]:
            who = max(series, key=lambda kv: kv[1][i])[0]
            hgt = hrs[i] / vt * H2
            out.append('<rect class="vbar" x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"><title>%s:00 — %s (mostly %s)</title></rect>'
                       % (X(i) - bw * 0.38, y0 + H2 - hgt, bw * 0.76, hgt, color[who], i, _axis_k(hrs[i]), e(who)))
    ma = [sum(hrs[max(0, i - 2):i + 1]) / len(hrs[max(0, i - 2):i + 1]) for i in range(24)]
    out.append('<polyline class="ma" points="%s"/>' % " ".join("%.1f,%.1f" % (X(i), y0 + H2 - ma[i] / vt * H2) for i in range(24)))
    out.append('<text class="pane" x="%d" y="%d">VOLUME · tokens per hour · line = 3-hr moving average</text>' % (L + 4, y0 - 6))
    for i in range(0, 24, 3):
        out.append('<text class="xl" x="%.1f" y="%d">%s</text>' % (X(i), y0 + H2 + 16, (str(i % 12 or 12) + ("a" if i < 12 else "p"))))
    legend = "".join('<span><i style="background:%s"></i>%s</span>' % (color[k], e(k)) for k, _ in series)
    legend += '<span><i class="lg-close"></i>Close (all agents)</span>' + ('<span><i class="lg-prev"></i>Yesterday</span>' if pcum else "")
    return ('<svg class="mkt" viewBox="0 0 %d %d" role="img" aria-label="tokens through the day by agent">%s</svg><div class="mkt-legend">%s</div>'
            % (W, y0 + H2 + 24, "".join(out), legend))


def spark(v):
    if not v or not sum(v):
        return ""
    m = max(v)
    return '<svg class="spark" viewBox="0 0 48 14" preserveAspectRatio="none"><polyline points="%s"/></svg>' % " ".join(
        "%.1f,%.1f" % (i * 2, 13 - x / m * 12) for i, x in enumerate(v))


def tokens_dow(date):
    try:
        u = json.load(open(os.path.join(SITE, "data", "usage-%s.json" % date)))
    except Exception:
        return '<div class="box dow"><h2>The Garden Token Average</h2><p class="small">The market was closed — no usage figures today.</p></div>'
    prev_day = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    try:
        pu = json.load(open(os.path.join(SITE, "data", "usage-%s.json" % prev_day)))
    except Exception:
        pu = {}
    total, ptotal = u.get("total") or 0, pu.get("total") or 0
    pct, cls, delta = _chg(total, ptotal)
    hrs = u.get("hours") or [0] * 24
    live = [h for h in hrs if h]
    first = next((i for i in range(24) if hrs[i]), 0)
    peak = max(range(24), key=lambda h: hrs[h])
    ah = u.get("agent_hours") or {}

    def movers(cur, old, is_agent):
        rows = []
        for k, v in sorted((cur or {}).items(), key=lambda kv: -kv[1])[:12]:
            pc, c, d = _chg(v, (old or {}).get(k, 0))
            share = v / total * 100 if total else 0
            rows.append('<tr class="%s"><td class="sym">%s</td><td class="nm">%s%s</td><td class="num">%s</td><td class="num chg">%s</td><td class="num">%.0f%%</td><td>%s</td></tr>'
                        % (c, e(sym(k)) if is_agent else "", mug(k, "mug xs") if is_agent else "", e(k), _k(v), pc, share, spark(ah.get(k)) if is_agent else ""))
        return "".join(rows) or '<tr><td colspan="6">—</td></tr>'
    tape = " ".join('<span class="%s">%s %s %s</span>' % (_chg(v, (pu.get("by_agent") or {}).get(k, 0))[1], e(sym(k)), _k(v),
                                                          _chg(v, (pu.get("by_agent") or {}).get(k, 0))[0])
                    for k, v in sorted((u.get("by_agent") or {}).items(), key=lambda kv: -kv[1]))
    lead = max((u.get("by_agent") or {"—": 0}).items(), key=lambda kv: kv[1])
    return ('<div class="dow"><div class="ticker"><div class="tape">%s &nbsp;·&nbsp; %s</div></div>'
            '<div class="dow-head"><div><div class="dow-name">The Garden Token Average</div><div class="small">GTA · tokens burned across the Garden · session of %s</div></div>'
            '<div class="dow-quote %s"><b>%s</b><span>%s</span><small>%s vs. yesterday\'s close</small></div></div>'
            '<div class="dow-stats"><div><small>Open</small><b>%s</b><em>first hour %d:00</em></div><div><small>High (peak hour)</small><b>%s</b><em>at %d:00</em></div>'
            '<div><small>Low (quietest live hour)</small><b>%s</b><em>%d live hours</em></div><div><small>Close</small><b>%s</b><em>prev. %s</em></div>'
            '<div><small>Volume (API calls)</small><b>~%s</b><em>cached reads %s</em></div><div><small>Market leader</small><b>%s</b><em>%s · %.0f%% of volume</em></div></div>'
            '%s'
            '<div class="dow-tables"><div><h4>Most Active — by agent</h4><table class="quotes"><thead><tr><th>Sym</th><th>Agent</th><th>Tokens</th><th>Chg</th><th>Share</th><th>Day</th></tr></thead><tbody>%s</tbody></table></div>'
            '<div><h4>Sectors — by model</h4><table class="quotes"><thead><tr><th></th><th>Model</th><th>Tokens</th><th>Chg</th><th>Share</th><th></th></tr></thead><tbody>%s</tbody></table>'
            '<h4>Exchanges — by provider</h4><table class="quotes"><thead><tr><th></th><th>Provider</th><th>Tokens</th><th>Chg</th><th>Share</th><th></th></tr></thead><tbody>%s</tbody></table></div></div>'
            '<p class="small">▲ red = burned more than yesterday · ▼ green = leaner. %s%s</p></div>'
            % (tape, tape, e(u.get("day") or prev_day), cls, _k(total), pct, delta,
               _k(hrs[first]), first, _k(hrs[peak]), peak, _k(min(live) if live else 0), len(live), _k(total), _k(ptotal) if ptotal else "—",
               e(u.get("calls")), _k(u.get("cache_read")), e(sym(lead[0])), e(lead[0]), (lead[1] / total * 100) if total else 0,
               market_chart(u, pu), movers(u.get("by_agent"), pu.get("by_agent"), True), movers(u.get("by_model"), pu.get("by_model"), False),
               movers(u.get("by_provider"), pu.get("by_provider"), False),
               e(u.get("note")), "" if u.get("pc_included") else " PC usage (Claude Code / Codex) not included today."))


# ---------------------------------------------------------------- Section C: the Sports Section
def _sports_data(date):
    try:
        up = json.load(open(os.path.join(SITE, "data", "uptime-%s.json" % date)))
    except Exception:
        up = {}
    try:
        pay = json.load(open(os.path.join(SITE, "data", "payroll-%s.json" % date)))
    except Exception:
        pay = {}
    return up, pay


def auto_sports(up, pay):
    """The sports desk's fallback: a game story, league notes, injury report and power rankings written from the real numbers."""
    rows = [r for r in pay.get("rows") or [] if r.get("jobs")]
    agents = {a["name"]: a for a in up.get("agents") or []}
    if not rows and not agents:
        return {}
    ranked = sorted(rows, key=lambda r: (-{"A": 4, "B": 3, "C": 2, "D": 1}.get(r.get("grade"), 0), -r.get("today", 0)))
    eotd = (pay.get("employee_of_the_day") or {}).get("agent") or (ranked[0]["agent"] if ranked else "")
    busts = [r for r in rows if r.get("grade") == "F"]
    lean = min(rows, key=lambda r: float(str(r.get("per_job") or "999k").rstrip("k") or 999)) if rows else None
    total_pay = sum(r.get("today", 0) for r in rows)
    graded_a = [r["agent"] for r in rows if r.get("grade") == "A"]
    paras = []
    if eotd:
        paras.append("**%s** was the story of the night shift, turning in the most efficient outing on the card%s. The Garden League went %d-for-%d "
                     "on the night, with %d players grading out at an A and the whole roster pulling in $%.2f in pretend pay."
                     % (eotd, (" at %s tokens a job" % lean["per_job"]) if lean and lean["agent"] == eotd else "", len(rows) - len(busts), len(rows),
                        len(graded_a), total_pay))
    if lean and lean["agent"] != eotd:
        paras.append("Lean-burn honors went to %s, who needed just %s tokens per job — the kind of economy that keeps the front office happy." % (lean["agent"], lean["per_job"]))
    if busts:
        paras.append("It wasn't a clean sheet. %s came up empty with an F, and the dugout will be looking for answers before the next shift."
                     % " and ".join(r["agent"] for r in busts))
    best = up.get("longest") or {}
    if best:
        paras.append("Meanwhile %s keeps the longest active streak in the league alive at %s without a stumble." % (best.get("name"), _streak(best.get("streak_h"))))
    inj = []
    for a in agents.values():
        st = str(a.get("status", ""))
        if "error" in st or st == "down":
            inj.append({"agent": a["name"], "status": "Out" if st == "down" else "Day-to-day", "note": "shift error last night" if "error" in st else "offline"})
    for m in up.get("machines") or []:
        if m.get("status") != "up":
            inj.append({"agent": m["name"], "status": "Out", "note": "machine offline"})
    atl = []
    for r in sorted(rows, key=lambda r: -r.get("today", 0))[1:5]:
        atl.append("%s: %s job%s, grade %s, $%.2f on the night." % (r["agent"], r["jobs"], "" if r["jobs"] == 1 else "s", r.get("grade"), r.get("today", 0)))
    return {"recap": "\n\n".join(paras), "around_the_league": atl, "injury_report": inj[:6],
            "power_rankings": [{"agent": r["agent"], "note": "grade %s · %s tokens/job" % (r.get("grade"), r.get("per_job"))} for r in ranked[:5]]}


def sports_block(date, sp):
    """Page one of Sports: the game story, the quote, around the league, the injury report and the power rankings
    (written by Ganja's sports desk in the edition's "sports" object), with Player of the Game and Streak Watch."""
    up, pay = _sports_data(date)
    sp = dict(auto_sports(up, pay), **{k: v for k, v in (sp if isinstance(sp, dict) else {}).items() if v})
    eotd, best = pay.get("employee_of_the_day") or {}, up.get("longest") or {}
    head = sp.get("headline") or (("%s takes Player of the Game" % eotd["agent"]) if eotd.get("agent") else "Quiet night in the Garden League")
    q = sp.get("quote") or {}
    inj = "".join('<tr><td class="team">%s<span>%s</span></td><td class="st %s">%s</td><td>%s</td></tr>'
                  % (mug(x.get("agent"), "mug xs"), e(x.get("agent")), e(str(x.get("status", "")).lower().split()[0] if x.get("status") else ""),
                     e(x.get("status")), e(x.get("note"))) for x in sp.get("injury_report") or [] if isinstance(x, dict))
    pr = "".join('<li>%s<div><b>%s</b> <span class="small">%s</span></div></li>' % (mug(x.get("agent"), "mug xs"), e(x.get("agent")), e(x.get("note")))
                 for x in (sp.get("power_rankings") or [])[:5] if isinstance(x, dict))
    atl = "".join("<li>%s</li>" % e(x) for x in sp.get("around_the_league") or [] if x)
    return ('<div class="sports"><h2 class="sp-head">%s</h2>%s'
            '<div class="sp-grid"><article class="sp-story">%s%s%s</article><aside class="sp-side">%s%s%s%s%s</aside></div></div>'
            % (e(head), ('<p class="sp-deck">%s</p>' % e(sp["deck"])) if sp.get("deck") else "",
               ('<div class="byline">%s<span>By %s · Sports Desk</span></div>' % (mug(sp.get("byline") or "Disco Stu"), e(sp.get("byline") or "Disco Stu"))),
               para(sp.get("recap")) or "<p>No game story tonight — the press box was empty.</p>",
               ('<blockquote class="sp-quote">“%s”<cite>— %s</cite></blockquote>' % (e(q.get("text")), e(q.get("agent")))) if q.get("text") else "",
               ('<div class="sp-mvp">%s<div><span class="kicker">Player of the Game</span><b>%s</b><div>%s</div></div></div>' % (mug(eotd["agent"], "mug"), e(eotd["agent"]), e(eotd.get("why")))) if eotd.get("agent") else "",
               ('<div class="sp-streak"><span class="kicker">Streak Watch</span><b>%s</b><div>%s straight without a stumble</div></div>' % (e(best.get("name")), e(_streak(best.get("streak_h"))))) if best else "",
               ('<h4>Power Rankings</h4><ol class="sp-pr">%s</ol>' % pr) if pr else "",
               ('<h4>Around the League</h4><ul class="sp-atl">%s</ul>' % atl) if atl else "",
               ('<h4>Injury Report</h4><table class="agate inj"><tbody>%s</tbody></table>' % inj) if inj else ""))


def scoreboard_block(date):
    """Page two of Sports: standings, box score, facilities (agate type)."""
    up, pay = _sports_data(date)
    prow = {r.get("agent"): r for r in pay.get("rows") or []}
    teams = []
    for a in up.get("agents") or []:
        st = str(a.get("status", ""))
        light = "up" if st in ("up", "shift ok") else ("warn" if st.startswith("shift") and "error" not in st else "down")
        r = prow.get(a["name"], {})
        teams.append((a.get("streak_h") or 0, '<tr><td class="team">%s<span>%s</span></td><td><span class="light %s"></span></td><td class="num">%s</td>'
                      '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                      % (mug(a["name"], "mug xs"), e(a["name"]), light, e(_streak(a.get("streak_h")) or st), e(r.get("jobs", "—")),
                         e(r.get("grade", "—")), ("$%.2f" % r["week"]) if "week" in r else "—")))
    teams.sort(key=lambda t: -t[0])
    box = "".join('<tr><td class="team">%s<span>%s</span></td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td><td class="num">$%.2f</td></tr>'
                  % (mug(r["agent"], "mug xs"), e(r["agent"]), e(r.get("jobs")), e(r.get("per_job")), e(r.get("grade")), r.get("today", 0))
                  for r in pay.get("rows") or [] if r.get("jobs"))
    fac = "".join('<tr><td class="team">🖥 <span>%s</span></td><td><span class="light %s"></span></td><td class="num">%s</td><td>%s</td></tr>'
                  % (e(m["name"]), "up" if m.get("status") == "up" else "down", e(_streak(m.get("streak_h")) or m.get("status")), e(m.get("kind") or ""))
                  for m in up.get("machines") or [])
    return ('<div class="sports"><h2 class="sp-head small">Scoreboard</h2><div class="sp-cols"><div><h4>Garden League Standings</h4>'
            '<table class="agate"><thead><tr><th>Team</th><th></th><th>Streak</th><th>Jobs</th><th>Grade</th><th>Pay wk</th></tr></thead><tbody>%s</tbody></table></div>'
            '<div><h4>Last Night\'s Box Score</h4><table class="agate"><thead><tr><th>Player</th><th>Jobs</th><th>Tok/job</th><th>Grade</th><th>Pay</th></tr></thead>'
            '<tbody>%s</tbody></table><h4>Facilities Report</h4><table class="agate"><thead><tr><th>Machine</th><th></th><th>Up</th><th></th></tr></thead><tbody>%s</tbody></table></div></div></div>'
            % ("".join(t[1] for t in teams) or '<tr><td colspan="6">No standings today.</td></tr>',
               box or '<tr><td colspan="5">No games last night.</td></tr>', fac or '<tr><td colspan="4">—</td></tr>'))


# ---------------------------------------------------------------- QR code (drawn here, so it's on the page however the book loads)
def qr_svg(text):
    try:
        import qrcode
    except ImportError:   # the system python borrows the Hermes venv's pure-python qrcode package
        import glob as _g
        sys.path.extend(_g.glob(os.path.expanduser("~/.hermes/hermes-agent/venv/lib/python3*/site-packages")))
        import qrcode
    q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(text)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    cells = "".join('<rect x="%d" y="%d" width="1" height="1"/>' % (x, y) for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return ('<svg class="qr-svg" viewBox="0 0 %d %d" shape-rendering="crispEdges" role="img" aria-label="QR code: %s"><rect width="%d" height="%d" fill="#fff"/>'
            '<g fill="#000">%s</g></svg>' % (n, n, e(text), n, n, cells))


def back_codes(repo, label):
    """Barcode + QR code for a paper's back cover, both pointing at its GitHub repo."""
    return ('<div class="codes"><a class="bc-wrap" href="%s" title="%s on GitHub">%s</a><a class="qr" href="%s" title="%s on GitHub">%s</a></div>'
            '<p class="pb-code">scan me · %s</p>' % (e(repo), e(label), code128_svg(repo), e(repo), e(label), qr_svg(repo), e(repo.replace("https://", ""))))


# ---------------------------------------------------------------- the front page, like a real front page
def front_page(ed, date, goto):
    head = ed.get("headline") or {}
    try:
        w = json.load(open(os.path.join(SITE, "data", "weather-%s.json" % date)))
    except Exception:
        w = {}
    now = w.get("now") or {}
    days = w.get("days") or []
    ear_l = ('<div class="fp-ear"><b>%s %s°</b><span>%s</span><span>%s</span><a data-goto="%s">Full forecast ›</a></div>'
             % (wx_icon(now.get("text")), e(now.get("temp_f", "?")), e(now.get("text")),
                e(" · ".join("%s %s°" % (str(d.get("name", ""))[:3], d.get("high")) for d in days[1:3])), goto.get("Weather & Almanac", "")))
    inside = "".join('<li><a data-goto="%s"><span>%s</span>%s</a></li>' % (n, e(t), ('<i>%s</i>' % e(k)) if k.lower() != t.lower() else "")
                     for t, k, n in goto.get("_index", []))
    ear_r = '<div class="fp-ear"><b>INSIDE TODAY</b><ul class="fp-inside">%s</ul></div>' % inside
    briefs = []
    for s_ in ed.get("sections") or []:
        for st in (s_.get("stories") or [])[:1]:
            first = re.split(r"(?<=[.!?])\s", str(st.get("body") or "").strip(), 1)[0]
            briefs.append('<div class="brief"><span class="kicker">%s</span><b>%s</b><p>%s</p><a data-goto="%s">Story on the %s page ›</a></div>'
                          % (e(s_.get("name")), e(st.get("title")), e(re.sub(r"\*\*", "", first)), goto.get(s_.get("name"), ""), e(s_.get("name"))))
    lead_body = para(head.get("body"))
    return ('<div class="fp"><div class="fp-ears">%s<div class="fp-date">%s · Lewiston, Maine</div>%s</div>'
            '<div class="fp-kicker">%s</div><h2 class="fp-banner">%s</h2><p class="fp-dek">%s</p>'
            '<div class="fp-grid"><article class="fp-lead">%s%s</article><aside class="fp-rail"><div class="box keys"><h2>Logins &amp; Keys</h2>%s</div>%s</aside></div>'
            '<div class="fold"><span>— fold —</span></div><h3 class="fp-below">In Brief</h3><div class="fp-briefs">%s</div></div>'
            % (ear_l, e(dt.date.fromisoformat(date).strftime("%A, %B %-d, %Y")), ear_r, e(head.get("tag") or "Top story"), e(head.get("title")),
               e(head.get("dek")), ('<div class="byline">%s<span>By %s</span></div>' % (mug(head.get("agent")), e(head.get("agent")))) if head.get("agent") else "",
               lead_body, para(ed.get("logins_and_keys")) or "<p>No report.</p>", coming_block((ed.get("coming_up") or [])[:4]),
               "".join(briefs[:6]) or '<p class="small">A quiet night on every desk.</p>'))


def opinion_block(ed):
    ed_ = ed.get("editorial") or {}
    sug = [x for x in (ed.get("suggestions") or []) if isinstance(x, dict)]
    if not (ed_.get("body") or sug):
        return ""
    letters = "".join('<div class="letter"><p>%s</p><span>— %s</span><b>%s</b></div>' % (e(x.get("text")), e(x.get("agent")), e(x.get("title"))) for x in sug)
    return ('<div class="op"><div class="op-ed">%s</div><div class="op-letters"><h2>Letters to the Editor</h2><p class="small">Ideas for the paper — tell Ganja which ones to keep</p>%s</div></div>'
            % (('<h2 class="op-title">%s</h2><div class="byline">%s<span>The Editorial Board · Ganja, editor</span></div>%s'
                % (e(ed_.get("title") or "From the Editor"), mug("Ganja"), para(ed_.get("body")))) if ed_.get("body") else
               '<h2 class="op-title">From the Editor</h2><p class="small">No editorial today.</p>', letters or '<p class="small">No letters today.</p>'))


# ---------------------------------------------------------------- the centerfold: the Garden at a glance
def centerfold_block(date):
    def load(name):
        try:
            return json.load(open(os.path.join(SITE, "data", "%s-%s.json" % (name, date))))
        except Exception:
            return {}
    u, up, pay = load("usage"), load("uptime"), load("payroll")
    ah = u.get("agent_hours") or {}
    rows = sorted(ah.items(), key=lambda kv: -sum(kv[1]))[:14]
    top = max([max(v) for _, v in rows] + [1])
    heat = "".join('<tr><th>%s<span>%s</span></th>%s<td class="tot">%s</td></tr>'
                   % (mug(k, "mug xs"), e(k), "".join('<td style="--a:%.2f" title="%s:00 — %s"></td>' % ((x / top) ** .5 if x else 0, h, _k(x)) for h, x in enumerate(v)),
                      _k(sum(v))) for k, v in rows)
    hours = "".join("<th>%s</th>" % ((str(h % 12 or 12) + ("a" if h < 12 else "p")) if h % 3 == 0 else "") for h in range(24))
    machines = "".join('<div class="cf-mach %s"><b>%s</b><span>%s</span><small>%s</small></div>'
                       % ("up" if m.get("status") == "up" else "down", e(m["name"]), "UP" if m.get("status") == "up" else "DOWN",
                          e(_streak(m.get("streak_h")) or "")) for m in up.get("machines") or [])
    agents_up = sum(1 for a in up.get("agents") or [] if str(a.get("status")) in ("up", "shift ok"))
    jobs = sum(r.get("jobs", 0) for r in pay.get("rows") or [])
    pay_t = sum(r.get("today", 0) for r in pay.get("rows") or [])
    nums = [("Tokens burned", _k(u.get("total"))), ("API calls", "~%s" % (u.get("calls") or 0)), ("Agents on the clock", "%d / %d" % (agents_up, len(up.get("agents") or []))),
            ("Relay jobs", str(jobs)), ("Pretend payroll", "$%.2f" % pay_t), ("Longest streak", "%s · %s" % ((up.get("longest") or {}).get("name", "—"), _streak((up.get("longest") or {}).get("streak_h"))))]
    return ('<div class="cf"><div class="cf-title"><span>THE GARDEN</span><span>AT A GLANCE</span></div>'
            '<div class="cf-nums">%s</div>'
            '<h4>Who worked when — tokens by agent, hour by hour</h4><div class="cf-heatwrap"><table class="cf-heat"><thead><tr><th></th>%s<th>Total</th></tr></thead><tbody>%s</tbody></table></div>'
            '<h4>The machines</h4><div class="cf-machines">%s</div></div>'
            % ("".join('<div><small>%s</small><b>%s</b></div>' % (e(a), e(b)) for a, b in nums), hours,
               heat or '<tr><td>No hourly figures today.</td></tr>', machines or '<p class="small">No machine report.</p>'))


# ---------------------------------------------------------------- puzzles: a word search from the day's news + Garden-scopes
def wordsearch(words, seed, size=12):
    import random
    rnd = random.Random(seed)
    grid = [[""] * size for _ in range(size)]
    placed = []
    dirs = [(0, 1), (1, 0), (1, 1), (-1, 1)]
    for w in sorted({re.sub(r"[^A-Z]", "", x.upper()) for x in words if x}, key=len, reverse=True):
        if not 3 <= len(w) <= size or len(placed) >= 10:
            continue
        for _ in range(200):
            dy, dx = rnd.choice(dirs)
            y0, x0 = rnd.randrange(size), rnd.randrange(size)
            cells = [(y0 + dy * i, x0 + dx * i) for i in range(len(w))]
            if all(0 <= y < size and 0 <= x < size and grid[y][x] in ("", w[i]) for i, (y, x) in enumerate(cells)):
                for i, (y, x) in enumerate(cells):
                    grid[y][x] = w[i]
                placed.append(w)
                break
    for y in range(size):
        for x in range(size):
            grid[y][x] = grid[y][x] or rnd.choice("ABCDEFGHIKLMNOPRSTUWY")
    return grid, placed


def puzzles_block(ed, date):
    words = ["GANJA", "CHRONIC", "MAPLE", "HERBIE", "HOMIE", "IBBY", "BAKER", "CYPHER", "CLYDIUS", "GARDEN", "RELAY", "VAULT", "TOKENS"]
    text = " ".join([str((ed.get("headline") or {}).get("title") or "")] + [str(st.get("title")) for s_ in ed.get("sections") or [] for st in s_.get("stories") or []])
    news = [w for w in re.findall(r"(?<![A-Za-z0-9])[A-Za-z]{5,9}(?![A-Za-z0-9])", text) if w.lower() not in ("their", "there", "after", "about", "which", "garden", "still", "going")]
    grid, placed = wordsearch(news[:6] + words, date)
    table = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in row) for row in grid)
    scopes = "".join('<div class="scope">%s<div><b>%s</b><p>%s</p></div></div>' % (mug(x.get("agent"), "mug sm"), e(x.get("agent")), e(x.get("text")))
                     for x in ed.get("horoscopes") or [] if isinstance(x, dict))
    return ('<div class="pz"><div class="pz-ws"><h2>Word Search</h2><p class="small">Every word is from today\'s paper. Tap letters to circle them.</p>'
            '<table class="ws">%s</table><ul class="ws-words">%s</ul></div>'
            '<div class="pz-scopes"><h2>Garden-scopes</h2><p class="small">What the stars (and the cron jobs) hold today</p>%s</div></div>'
            % (table, "".join("<li>%s</li>" % w for w in sorted(placed)), scopes or '<p class="small">The stars were quiet today.</p>'))


# ---------------------------------------------------------------- listings (jobs + want ads), clickable
def listing_block(items, kind):
    """Job Listings (kind='job') and Want Ads (kind='want') are both tappable: approve / handle / not now (+ link)."""
    rows = []
    for i, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        rows.append(
            '<button type="button" class="ad job" data-kind="%s" data-idx="%d">%s<div class="job-txt"><b>%s</b>%s'
            '<div>%s</div>%s<div class="job-status" data-status="open">%s</div></div></button>'
            % (kind, i, mug(it.get("agent"), "mug sm"), e(it.get("title")),
               (' <span class="tag">%s</span>' % e(it.get("agent"))) if it.get("agent") else "",
               e(it.get("details") or it.get("text")),
               ('<div class="ask">➜ %s</div>' % e(it.get("ask"))) if it.get("ask") else "",
               "Tap to approve or handle ›" if kind == "job" else "Tap to answer this ad ›"))
    empty = "No job listings today. Everybody's employed." if kind == "job" else "No want ads today."
    return "".join(rows) or '<p class="small">%s</p>' % e(empty)


def followups_block(date):
    """Results of listings CAK3D approved in the last few editions (filled in by serve.py when the agent finishes)."""
    rows = []
    jd = os.path.join(ROOT, "jobs")
    for f in sorted(glob.glob(os.path.join(jd, "*.json")))[-4:]:
        try:
            st = json.load(open(f))
        except Exception:
            continue
        for k, v in st.items():
            if v.get("status") != "approved":
                continue
            res = v.get("result_status")
            icon = {"ok": "✅", "failed": "❌", "needs": "👉"}.get(res, "⏳")
            rows.append('<li><span class="fu-icon">%s</span><div><b>%s</b> <span class="small">(approved %s)</span><div class="small">%s</div></div></li>'
                        % (icon, e(v.get("title")), e(str(v.get("at", ""))[:10]),
                           e(v.get("result") or "Still working on it — the report posts in Ganja's channel when it's done.")))
    if not rows:
        return ""
    return '<div class="followups"><h2>Follow-ups</h2><p class="small">What happened to the jobs you approved</p><ul class="fu">%s</ul></div>' % "".join(rows[-8:])


# ---------------------------------------------------------------- B.I.G's catalog
def catalog_block(items):
    items = [x for x in (items or []) if isinstance(x, dict)]
    if not items:
        return ('<div class="market-teaser"><div class="kicker">Coming soon</div><h3>B.I.G opens for business</h3>'
                '<p>The Budding Investment Garden is setting up shop. Once B.I.G files his first catalog, this page lists quick-cash ideas '
                'and side gigs — each with its price tag, what it takes, what it might pay, and the risk.</p>'
                '<p class="small">Until then, this shelf stays empty on purpose: no made-up money tips.</p></div>')
    cards = []
    for i, x in enumerate(items):
        cards.append(
            '<button type="button" class="cat-item" data-idx="%d"><span class="burst"><span>%s</span></span>'
            '<span class="cat-no">ITEM No. %s</span><b class="cat-title">%s</b>%s<span class="cat-desc">%s</span>'
            '<span class="cat-meta"><span>⏱ %s</span><span>⚠ %s risk</span></span><span class="cat-more">See details ›</span></button>'
            % (i, e(x.get("price") or x.get("income_week") or "?"), e(x.get("item_no") or "%03d-%02d" % (27 + i, i + 1)),
               e(x.get("title")), ('<span class="cat-tag">%s</span>' % e(x.get("tag"))) if x.get("tag") else "",
               e(x.get("desc") or x.get("text")), e(x.get("tend") or "?"), e((x.get("risk") or "?").split(" ")[0])))
    return ('<div class="catalog-head"><span>B.I.G\'s</span> Wish-Book of Quick Cash<small>All prices are weekly estimates · tap any item for the full tag</small></div>'
            '<div class="catalog">%s</div>' % "".join(cards))


# ---------------------------------------------------------------- newspaper comic strips
def strips_block(fun):
    strips = fun.get("strips") or []
    if not strips and fun.get("panels"):   # older single-strip editions
        strips = [{"title": fun.get("title"), "panels": fun.get("panels")}]
    out = []
    for s in strips[:4]:
        if not isinstance(s, dict):
            continue
        if s.get("image"):   # drawn by draw_funnies.py: one inked strip, lettering included
            said = " / ".join("%s: %s" % (c.get("agent"), c.get("says")) for p in (s.get("panels") or []) if isinstance(p, dict)
                              for c in (p.get("cast") or []) if isinstance(c, dict) and c.get("says"))
            out.append('<figure class="strip-art"><a href="%s" target="_blank" rel="noopener"><img src="%s" loading="lazy" alt="%s"></a></figure>'
                       % (e(s["image"]), e(s["image"]), e("%s %s. %s" % (s.get("title") or "", s.get("byline") or "", said))))
            continue
        panels = []
        for p in (s.get("panels") or [])[:4]:
            if not isinstance(p, dict):
                p = {"caption": p}
            cast = p.get("cast") or ([{"agent": p.get("agent"), "says": p.get("says") or p.get("caption")}] if p.get("agent") else [])
            narr = p.get("caption") if (p.get("cast") or p.get("says")) else (p.get("narration") or "")
            people = "".join('<div class="ink-actor">%s%s</div>' % (('<div class="balloon">%s</div>' % e(c.get("says"))) if c.get("says") else "",
                                                                       mug(c.get("agent"), "mug ink"))
                             for c in cast if isinstance(c, dict))
            panels.append('<div class="ink-panel">%s%s<div class="ink-stage">%s</div></div>'
                          % (('<div class="ink-narr">%s</div>' % e(narr)) if narr else "",
                             ('<div class="ink-sfx">%s</div>' % e(p.get("sfx"))) if p.get("sfx") else "", people))
        out.append('<div class="strip-row"><div class="strip-name">%s<span>%s</span></div><div class="ink-panels">%s</div></div>'
                   % (e(s.get("title")), e(s.get("byline") or "by the Garden Gang"), "".join(panels)))
    joke = ('<p class="joke">%s</p>' % e(fun.get("joke"))) if fun.get("joke") else ""
    return '<div class="funnies-news"><div class="fn-head">The Funnies</div>%s%s</div>' % ("".join(out), joke)


# ---------------------------------------------------------------- the almanac
def almanac_block(date, notes, numbers):
    try:
        a = json.load(open(os.path.join(SITE, "data", "almanac-%s.json" % date)))
    except Exception:
        a = {}
    notes = notes if isinstance(notes, dict) else {}
    sky = a.get("sky") or {}
    season = a.get("season") or {}
    records = a.get("records") or {}
    def lis(xs):
        return "".join("<li>%s</li>" % e(x) for x in xs if x)
    sky_html = lis([
        sky.get("sunrise") and "Sunrise %s · Sunset %s" % (sky.get("sunrise"), sky.get("sunset")),
        sky.get("daylength") and "Daylight %s (%s since yesterday)" % (sky.get("daylength"), sky.get("daydelta")),
        sky.get("moon") and "Moon: %s, %s%% lit" % (sky.get("moon"), sky.get("illum")),
        sky.get("next_full") and "Next full moon %s · next new moon %s" % (sky.get("next_full"), sky.get("next_new")),
    ])
    season_html = lis(season.get("lines") or [])
    records_html = lis(records.get("lines") or [])
    nums = "".join("<li><b>%s</b> %s</li>" % (e(k), e(v)) for k, v in (numbers or {}).items())
    col = lambda title, body: ('<div class="alm-sec"><h4>%s</h4><ul>%s</ul></div>' % (title, body)) if body else ""
    return ('<div class="almanac-page"><div class="alm-head">The Garden Almanac<small>for the year 2026 · calculated for Lewiston, Maine</small></div>'
            '<div class="alm-cols">%s%s%s%s%s%s%s</div>%s</div>'
            % (col("The Sky", sky_html), col("The Season", season_html), col("Garden Records", records_html),
               col("Predictions &amp; Outlook", lis(notes.get("predictions") or [])),
               col("On This Day", lis(notes.get("on_this_day") or [])),
               col("Planting &amp; Tending", lis(notes.get("tending") or [])),
               col("By the Numbers", nums),
               ('<div class="alm-foot">%s%s</div>' % (('<p class="alm-saying">“%s”</p>' % e(notes.get("saying"))) if notes.get("saying") else "",
                                                     ('<p class="small">Oddity of the day: %s</p>' % e(notes.get("oddity"))) if notes.get("oddity") else ""))))


# ---------------------------------------------------------------- payroll
def payroll_block(date):
    try:
        p = json.load(open(os.path.join(SITE, "data", "payroll-%s.json" % date)))
    except Exception:
        return '<div class="box payroll"><h2>Payroll</h2><p class="small">Payroll office closed today.</p></div>'
    rows = "".join(
        '<tr><td>%s<span>%s</span></td><td>%s</td><td>%s</td><td>%s</td><td class="pay">$%s</td><td>$%s</td><td>$%s</td></tr>'
        % (mug(r["agent"], "mug xs"), e(r["agent"]), e(r.get("jobs")), e(r.get("grade")), e(r.get("per_job")),
           e("%.2f" % r.get("today", 0)), e("%.2f" % r.get("week", 0)), e("%.2f" % r.get("month", 0)))
        for r in p.get("rows") or [])
    eotd = p.get("employee_of_the_day")
    return ('<div class="box payroll"><h2>Payroll</h2><p class="small">Pretend pay, real scorekeeping: base pay per job, bonuses for finishing fast and '
            'lean on tokens, docked for errors, reruns or lost context. %s</p>%s'
            '<table class="paytab"><thead><tr><th>Agent</th><th>Jobs</th><th>Grade</th><th>Tokens/job</th><th>Today</th><th>Week</th><th>Month</th></tr></thead>'
            '<tbody>%s</tbody></table></div>'
            % (e(p.get("period")), ('<p class="eotd">🏅 Employee of the Day: <b>%s</b> — %s</p>' % (e(eotd.get("agent")), e(eotd.get("why")))) if eotd else "", rows))


# ---------------------------------------------------------------- a real, scannable barcode (Code 128-B)
_C128 = ["212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213", "221312", "231212", "112232",
         "122132", "122231", "113222", "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131", "311222", "321122",
         "321221", "312212", "322112", "322211", "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311",
         "211313", "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331", "231131", "213113",
         "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224", "111422",
         "121124", "121421", "141122", "141221", "112214", "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111",
         "241112", "134111", "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141", "214121",
         "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
         "211214", "211232", "2331112"]


def code128_svg(text):
    codes = [104] + [ord(ch) - 32 for ch in text]
    check = (codes[0] + sum(i * c for i, c in enumerate(codes[1:], 1))) % 103
    pattern = "".join(_C128[c] for c in codes + [check]) + _C128[106]
    x, bars = 10, []
    for i, w in enumerate(pattern):
        w = int(w)
        if i % 2 == 0:
            bars.append('<rect x="%d" y="0" width="%d" height="60"/>' % (x, w))
        x += w
    return ('<svg class="barcode-svg" viewBox="0 0 %d 60" preserveAspectRatio="none" role="img" aria-label="barcode: %s">%s</svg>'
            % (x + 10, e(text), "".join(bars)))


def page(title, inner, extra=""):
    return '<div class="pg" data-title="%s"><div class="page-in%s">%s</div></div>' % (e(title), extra, inner)


def render(ed):
    date = ed.get("date") or dt.date.today().isoformat()
    d = dt.date.fromisoformat(date)
    no = ed.get("edition_no") or (d - dt.date(2026, 9, 26)).days + 1
    head = ed.get("headline") or {}
    fun = ed.get("funnies") or {}
    market = ed.get("market") or []
    try:   # B.I.G's catalog is copied in by the collector; never retyped by the editor
        market = market or json.load(open(os.path.join(SITE, "data", "market-%s.json" % date))).get("items") or []
    except Exception:
        pass
    keys = para(ed.get("logins_and_keys")) or "<p>No report.</p>"
    blotter = "".join('<li>%s<span><b>%s</b> %s</span></li>' % (mug(b.get("agent"), "mug xs"), e(b.get("time")), e(b.get("text")))
                      for b in ed.get("police_blotter") or [] if isinstance(b, dict))
    almanac = "".join("<li><b>%s</b> %s</li>" % (e(k), e(v)) for k, v in (ed.get("almanac") or {}).items())
    # laid out like a real paper: front page, news, opinion, business, the centerfold, sports, classifieds, weather, puzzles
    body = []   # (title, html, extra, index label or None)
    for s_ in ed.get("sections") or []:
        if isinstance(s_, dict) and s_.get("stories"):
            body.append((s_.get("name"), sec("News", s_.get("name")) + '<div class="desk"><h2 class="desk-name">%s</h2><div class="cols">%s</div></div>'
                         % (e(s_.get("name")), "".join(story(x) for x in s_["stories"])), "", "News"))
    op = opinion_block(ed)
    if op:
        body.append(("Opinion", sec("Opinion", "Editorial · Letters") + op, " opinion", "Opinion"))
    body.append(("The Garden Token Average", sec("Business", "Markets") + tokens_dow(date), " biz", "Business"))
    body.append(("Payroll", sec("Business", "Payroll") + payroll_block(date)
                 + '<a class="reup-plug biz-plug" href="/roach-clips/">B.I.G\'s Wish-Book of side gigs runs in <i>Roach Clips</i> ›</a>', " biz", None))
    body.append(("Centerfold: The Garden at a Glance", centerfold_block(date), " centerfold", "Centerfold"))
    body.append(("Sports", sec("Sports", "The Garden League") + sports_block(date, ed.get("sports")), " sports-page", "Sports"))
    body.append(("Sports: Scoreboard", sec("Sports", "Standings · Box score") + scoreboard_block(date), " sports-page", None))
    body.append(("Classifieds", sec("Classifieds") + '<div class="lower three"><div class="box blotter"><h2>Police Blotter</h2><ul>%s</ul></div>'
                 '<div class="box jobs"><h2>Job Listings</h2><p class="small">Help wanted — tap one to approve it or handle it yourself</p>%s</div>'
                 '<div class="box fu-box">%s<a class="reup-plug" href="/re-up/"><b>Want ads</b> are in <i>The Re-Up</i> ›</a></div></div>'
                 % (blotter or "<li>A quiet night. Nobody got arrested, not even the cron jobs.</li>",
                    listing_block(ed.get("job_listings"), "job"), followups_block(date) or '<h2>Follow-ups</h2><p class="small">Nothing approved lately.</p>'), "", "Classifieds"))
    body.append(("Weather & Almanac", sec("Weather", "Forecast · Sky · Season") + '<div class="wx-page">%s%s</div>' % (weather_block(date), coming_block(ed.get("coming_up")))
                 + almanac_block(date, ed.get("almanac_notes"), ed.get("almanac")), " weather-page", "Weather"))
    body.append(("Puzzles & Garden-scopes", sec("Puzzles", "Word search · Garden-scopes") + puzzles_block(ed, date)
                 + '<p class="small center">That\'s the whole pack. <a href="../archive.html">Back issues →</a> · <a href="/">🏠 The Newsstand →</a></p>', " puzzles", "Puzzles"))
    goto, index = {}, []
    for i, (t, _, _, label) in enumerate(body):   # page 1 = the pack, 2 = the front page, then the body
        goto.setdefault(t, i + 3)
        if label and label not in [x[0] for x in index]:
            index.append((label, "Garden news" if label == "News" else t.split(":")[0], i + 3))
    goto["_index"] = index
    front = page("Front Page", sec("News", "Today's top story") + '<div class="front"><div class="front-lead">%s</div><aside class="front-side">%s'
                 '<div class="box keys"><h2>Logins &amp; Keys</h2>%s</div></aside></div>' % (story(head, lead=True), weather_block(date), keys))
    pages = [front] + [page(t, h, x) for t, h, x, _ in body]
    # hard covers = the outside of the rolling-paper pack
    front_cover = page("The Pack", (
        '<div class="gum"><span>GUMMED · DOUBLE WIDE · 1¼ · SLOW BURNING</span></div>'
        '<div class="pc-top"><a class="seal" href="/" aria-label="Back to the Newsstand" title="Back to the Newsstand">%s</a><div class="ear">No. %s<br>%s<br><b>%s</b><br>%s</div></div>'
        '<div class="flag"><div class="est">EST. 2026 · THE GARDEN · LEWISTON, ME</div><h1>The Double<br>Wide</h1>'
        '<div class="motto">“All the news that\'s fit to roll”</div></div>'
        '<div class="pc-band"><span>1¼ SIZE</span><span>32 LEAVES</span><span>SLOW BURNING</span></div>'
        '<div class="pc-teaser"><div class="kicker">Today\'s headline</div><b>%s</b></div>'
        '<div class="pc-open">Open the pack ›</div>')
        % (SEAL, e(no), d.strftime("%a"), d.strftime("%b %-d"), d.strftime("%Y"), e(head.get("title"))), " hardcover")
    back_cover = page("Back of the Pack", (
        '<div class="gum"><span>MADE IN THE GARDEN · ROLLED BY GANJA</span></div>'
        '<div class="pb-body"><a class="seal" href="/" aria-label="Back to the Newsstand" title="Back to the Newsstand">%s</a><h2 class="pb-title">The Double Wide</h2>'
        '<p>Printed at dawn on The Garden.<br>Compiled by The Gardiner · Rolled by Ganja.</p>'
        '<p class="pb-warn">CAUTION: contents may contain cron jobs, read-only filesystems and strong opinions.</p>'
        '%s<p class="pb-code">%s · No. %s</p>'
        '<p><a href="../archive.html">Back issues ›</a> · <a href="/">🏠 The Newsstand</a></p></div>') % (SEAL, back_codes(REPO, "TheDoubleWide"), date, e(no)), " hardcover back")
    pages = [front_cover] + pages + [back_cover]
    pick = lambda xs, keys: [{k: x.get(k) for k in keys} for x in (xs or []) if isinstance(x, dict)]
    lists = {"job": pick(ed.get("job_listings"), ("title", "agent", "details", "text", "ask", "url")),
             "market": pick(market, MARKET_KEYS)}
    return book(pages, date=date, no=no, lists=lists)


MARKET_KEYS = ("title", "tag", "price", "desc", "text", "how", "income_week", "tend", "upfront", "weekly_cost", "risk", "links", "item_no")


def book(pages, date, no, lists, paper="The Double Wide", motto="“All the news that's fit to roll”",
         gum="GUMMED · DOUBLE WIDE · 1¼ · SLOW BURNING · 32 LEAVES · MADE IN THE GARDEN", price="PRICE: ONE PINCH",
         delivered="DELIVERED BY GANJA", flap="Printed at dawn on The Garden · Compiled by The Gardiner · Rolled by Ganja",
         body_class="pub-dw", est="EST. 2026 · THE GARDEN · LEWISTON, ME", toolbar="", scripts=""):
    """Wrap finished pages in the flipbook page (masthead, pager, tap-to-open cards, app hookups)."""
    d = dt.date.fromisoformat(date)
    css = open(os.path.join(ROOT, CSS_FILE)).read()
    list_json = json.dumps(lists, ensure_ascii=False).replace("</", "<\\/")
    out = TEMPLATE
    for k, v in (("@@CSS@@", css), ("@@PAPER@@", e(paper)), ("@@MOTTO@@", e(motto)), ("@@GUM@@", e(gum)), ("@@PRICE@@", e(price)),
                 ("@@DELIVERED@@", e(delivered)), ("@@FLAP@@", e(flap)), ("@@BODYCLASS@@", e(body_class)), ("@@EST@@", e(est)),
                 ("@@DATE_LONG@@", d.strftime("%A, %B %-d, %Y")), ("@@NO@@", e(no)), ("@@DOW@@", d.strftime("%a")),
                 ("@@MD@@", d.strftime("%b %-d")), ("@@YEAR@@", d.strftime("%Y")), ("@@SEAL@@", SEAL),
                 ("@@PAGES@@", "\n".join(pages)), ("@@DATE@@", date), ("@@JOBS@@", list_json), ("@@TOOLBAR@@", toolbar), ("@@SCRIPTS@@", scripts)):
        out = out.replace(k, v)
    return out


REPO = "https://github.com/real-CAK3D/TheDoubleWide"

SEAL = ('<svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="4"/>'
        '<path d="M24 78h72v-22l-36-18-36 18z" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"/>'
        '<rect x="36" y="60" width="14" height="18" fill="currentColor"/><rect x="62" y="60" width="20" height="10" fill="currentColor"/>'
        '<path d="M74 38c4-8 12-8 10-16M82 36c6-6 12-4 12-12" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>')

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@PAPER@@ — @@DATE_LONG@@</title>
<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#2a1a10">
<link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/icon-192.png">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><script src="/app.js" defer></script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Abril+Fatface&family=Rye&family=UnifrakturMaguntia&family=Bangers&family=Patrick+Hand+SC&family=Oswald:wght@400;600;700&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>@@CSS@@</style></head><body class="@@BODYCLASS@@">
<div class="pack">
  <div class="gum"><span>@@GUM@@</span></div>
  <header class="cover">
    <a class="seal" href="/" aria-label="Back to the Newsstand" title="Back to the Newsstand">@@SEAL@@</a>
    <div class="flag"><div class="est">@@EST@@</div><h1>@@PAPER@@</h1>
      <div class="motto">@@MOTTO@@</div></div>
    <div class="ear">No. @@NO@@<br>@@DOW@@<br><b>@@MD@@</b><br>@@YEAR@@</div>
  </header>
  <div class="strip"><span>@@DATE_LONG@@</span><span>@@PRICE@@</span><span>@@DELIVERED@@</span></div>@@TOOLBAR@@
  <div class="book-wrap" id="bookwrap"><div id="flipbook">
@@PAGES@@
  </div></div>
  <nav class="pager" aria-label="Turn the pages">
    <button type="button" id="prev" aria-label="Previous page">‹</button>
    <div class="where"><span id="leafname">The Pack</span><span class="dots" id="dots"></span><span class="swipe-hint">⟵ swipe, or grab the page edge to turn ⟶</span></div>
    <button type="button" id="next" aria-label="Next page">›</button>
  </nav>
  <footer class="flap"><span>@@FLAP@@</span><a href="../archive.html">Back issues</a></footer>
</div>
<div class="modal" id="jobmodal" hidden><div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="jm-title">
  <button type="button" class="modal-x" id="jm-close" aria-label="Close">×</button>
  <div class="jm-head"><span id="jm-mug"></span><div><div class="kicker" id="jm-kind">Job Listing</div><h3 id="jm-title"></h3></div></div>
  <div id="jm-body"></div><div id="jm-links" class="jm-links"></div>
  <div class="jm-actions">
    <button type="button" class="btn go" data-d="approve" id="jm-go">✅ Approve</button>
    <button type="button" class="btn" data-d="done" id="jm-self">🛠 I'll do it myself — mark done</button>
    <button type="button" class="btn ghost" data-d="dismiss">Not now</button>
  </div><p class="small" id="jm-msg"></p></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="../js/turn-edge.js"></script>
<script>
(function () {
  var DATE = "@@DATE@@", LIST = @@JOBS@@;
  var BASE = location.pathname.replace(/\/(editions|issues|guides)\/[^\/]*$/, '/').replace(/[^\/]*$/, '');
  var book = document.getElementById('flipbook'), wrap = document.getElementById('bookwrap');
  var pages = Array.prototype.slice.call(book.querySelectorAll('.pg'));
  var nameEl = document.getElementById('leafname'), dotsEl = document.getElementById('dots');
  var turning = false, hasTurn = !!(window.jQuery && jQuery.fn.turn);
  function dims() {   // one full-width page at a time, so the classic newspaper layout fits
    var w = wrap.clientWidth;
    var h = Math.round(Math.max(560, Math.min(innerHeight - 40, 1100)));
    return { w: w, h: h };
  }
  pages.forEach(function (pg, i) {
    var b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', pg.dataset.title);
    b.onclick = function () { if (hasTurn && !turning) jQuery(book).turn('page', i + 1); };
    dotsEl.appendChild(b);
  });
  function label(p) {
    document.body.classList.toggle('on-cover', p === 1 || p === pages.length);   // closed book: the cover is the pack
    nameEl.textContent = (pages[p - 1] ? pages[p - 1].dataset.title : '') + '  ·  ' + p + ' of ' + pages.length;
    Array.prototype.forEach.call(dotsEl.children, function (d, i) { d.classList.toggle('on', i === p - 1); });
  }
  if (hasTurn) {
    var d = dims();
    jQuery(book).turn({ width: d.w, height: d.h, display: 'single', acceleration: true, gradients: true, duration: 950,
      when: { turning: function () { turning = true; }, turned: function (ev, p) { turning = false; label(p); if (window.__repaint) window.__repaint(); } } });
    var start = parseInt((location.hash.match(/page-(\d+)/) || [])[1] || '1', 10);
    if (start > 1) jQuery(book).turn('page', start);
    label(jQuery(book).turn('page'));
    var go = function (dir) { if (!turning) jQuery(book).turn(dir > 0 ? 'next' : 'previous'); };
    document.getElementById('prev').onclick = function () { go(-1); };
    document.getElementById('next').onclick = function () { go(1); };
    addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') go(1); if (e.key === 'ArrowLeft') go(-1); });
    var x0 = null, y0 = null;   // phones: swipe anywhere on the page (dragging a corner also works)
    book.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    book.addEventListener('touchend', function (e) {
      if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0; x0 = null;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.4) setTimeout(function () { go(dx < 0 ? 1 : -1); }, 30);
    });
    var t; addEventListener('resize', function () { clearTimeout(t); t = setTimeout(function () {
      var n = dims(); jQuery(book).turn('size', n.w, n.h); label(jQuery(book).turn('page')); }, 200); });
  } else { document.body.classList.add('noturn'); nameEl.textContent = 'All pages'; }

  // ---- Job Listings, Want Ads and B.I.G's catalog: tap → details → approve / handle / not now ----
  var modal = document.getElementById('jobmodal'), cur = null;
  var LAST_ST = null;
  window.__repaint = function () { if (LAST_ST) paintStatus(LAST_ST); if (typeof paintPlans === 'function') paintPlans(); };
  function paintStatus(st) {
    LAST_ST = st;
    Array.prototype.forEach.call(document.querySelectorAll('.job, .cat-item, .coupon'), function (b) {
      var kind = b.dataset.kind || 'market', key = (kind === 'job' ? '' : kind + ':') + b.dataset.idx, s = st[key];
      var el = b.querySelector('.job-status') || b.querySelector('.cat-more');
      if (!s || !el) return; b.classList.add('st-' + s.status);
      el.textContent = s.status === 'approved' ? (s.result_status === 'ok' ? '✅ Done — ' + (s.result || 'it worked') :
                                                   s.result_status === 'failed' ? '❌ Didn\'t work — ' + (s.result || 'see Discord') :
                                                   s.result_status === 'needs' ? '👉 Needs you — ' + (s.result || 'see Discord') :
                                                   '⏳ Approved — ' + (s.agent || 'Ganja') + ' is on it') :
                       s.status === 'done' ? '🛠 Done (by you)' : s.status === 'clipped' ? '✂ Clipped — saved for later' : s.status === 'dismissed' ? 'Not now' : el.textContent;
    });
  }
  var PLANS = {};
  function paintPlans() {
    Array.prototype.forEach.call(document.querySelectorAll('.cat-item'), function (b) {
      var j = (LIST.market || [])[+b.dataset.idx] || {}, p = PLANS[j.item_no], el = b.querySelector('.cat-more');
      if (!p || !el) return;
      el.textContent = p.status === 'ready' ? '📋 Full plan ready ›' : p.status === 'writing' ? '✍️ B.I.G is writing the plan…' : el.textContent;
    });
  }
  function load() {
    fetch(BASE + 'api/jobs?date=' + DATE, { cache: 'no-store' }).then(function (r) { return r.json(); }).then(paintStatus).catch(function () {});
    if (LIST.market && LIST.market.length) fetch(BASE + 'api/plans', { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (p) { PLANS = p || {}; paintPlans(); }).catch(function () {});
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function row(label, val) { return val ? '<div class="tag-row"><span>' + esc(label) + '</span><b>' + esc(val) + '</b></div>' : ''; }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.job, .cat-item, .coupon'); if (!b) return;
    ev.stopPropagation();
    var kind = b.dataset.kind || 'market', j = (LIST[kind] || [])[+b.dataset.idx] || {};
    cur = { kind: kind, idx: +b.dataset.idx };
    document.getElementById('jm-kind').textContent = kind === 'job' ? 'Job Listing' : kind === 'want' ? 'Want Ad' : kind === 'coupon' ? 'The Couponer · ' + (j.category || 'coupon') : 'B.I.G\'s Catalog · Item No. ' + (j.item_no || '');
    document.getElementById('jm-title').textContent = j.title || '';
    var body = '';
    if (kind === 'market') {
      body = '<div class="burst big"><span>' + esc(j.price || j.income_week || '?') + '</span></div><p>' + esc(j.desc || j.text) + '</p>' +
             (j.how ? '<p><b>How it pays:</b> ' + esc(j.how) + '</p>' : '') +
             '<div class="tag-card">' + row('Potential income / week', j.income_week) + row('Time to keep it going', j.tend) +
             row('Up-front cost', j.upfront) + row('Weekly cost', j.weekly_cost) + row('Risk of loss', j.risk) + '</div>';
    } else if (kind === 'coupon') {
      body = '<div class="burst big coupon-price"><span>' + esc(j.price || 'FREE') + '</span></div><p>' + esc(j.what) + '</p>' +
             (j.why ? '<p><b>Why it fits your setup:</b> ' + esc(j.why) + '</p>' : '') +
             '<div class="tag-card">' + row('Works with', j.fits) + row('Deal', j.deal) + row('Good through', j.expires) +
             row('Time to try it', j.time) + row('Difficulty', j.difficulty) + '</div>';
    } else {
      body = '<p>' + esc(j.details || j.text) + '</p>' + (j.ask ? '<p class="ask">➜ ' + esc(j.ask) + '</p>' : '');
    }
    document.getElementById('jm-body').innerHTML = body;
    var links = (j.links || []).slice(); if (j.url) links.unshift({ label: 'Open', url: j.url });
    document.getElementById('jm-links').innerHTML = links.filter(function (l) { return /^https?:\/\//.test(l.url || ''); })
      .map(function (l) { return '<a class="btn link" target="_blank" rel="noopener" href="' + esc(l.url) + '">🔗 ' + esc(l.label || l.url) + '</a>'; }).join('');
    var go = document.getElementById('jm-go'), self = document.getElementById('jm-self');
    go.dataset.d = 'approve'; self.dataset.d = 'done'; self.style.display = '';
    if (kind === 'market') {
      var p = PLANS[j.item_no] || {};
      go.dataset.d = p.status === 'ready' ? 'read' : 'plan'; go.dataset.url = p.url || '';
      go.innerHTML = p.status === 'ready' ? '📖 Read B.I.G\'s full start-to-finish plan' : p.status === 'writing' ? '✍️ B.I.G is writing the plan — check back soon'
                   : '📋 Have B.I.G write the full plan: every step, site, account &amp; legal need';
      self.style.display = 'none';
    } else if (kind === 'coupon') {
      go.innerHTML = '🛠 Have the Garden set it up'; self.innerHTML = '✂ Clip it — save for later'; self.dataset.d = 'clip';
    } else {
      go.innerHTML = (kind === 'want' ? '✅ Yes — have ' : '✅ Approve — have ') + esc(j.agent || 'the agent') + ' handle it';
      self.innerHTML = '🛠 I\'ll do it myself — mark done';
    }
    var m = b.querySelector('.mug'); document.getElementById('jm-mug').innerHTML = m ? m.outerHTML : '';
    document.getElementById('jm-msg').textContent = ''; modal.hidden = false;
  }, true);
  function close() { modal.hidden = true; }
  document.getElementById('jm-close').onclick = close;
  modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
  ['touchstart', 'touchmove', 'wheel', 'mousedown', 'mousemove'].forEach(function (t) { modal.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: true }); });
  Array.prototype.forEach.call(modal.querySelectorAll('.btn[data-d]'), function (btn) {
    btn.onclick = function () {
      var msg = document.getElementById('jm-msg');
      if (btn.dataset.d === 'read') { location.href = BASE + btn.dataset.url; return; }
      msg.textContent = 'Sending…';
      if (btn.dataset.d === 'plan') {
        fetch(BASE + 'api/plan', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Double-Wide': '1' },
          body: JSON.stringify({ date: LIST.market_date || DATE, idx: cur.idx }) })
          .then(function (r) { return r.json(); })
          .then(function (res) { msg.textContent = res.message || 'Sent.'; if (res.status === 'ready' && res.url) location.href = BASE + res.url; load(); })
          .catch(function () { msg.textContent = 'Could not reach the Garden — try again in a minute.'; });
        return;
      }
      fetch(BASE + 'api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Double-Wide': '1' },
        body: JSON.stringify({ date: DATE, kind: cur.kind, idx: cur.idx, decision: btn.dataset.d }) })
        .then(function (r) { return r.json(); })
        .then(function (res) { msg.textContent = res.message || 'Saved.'; load(); if (res.ok) setTimeout(close, 1600); })
        .catch(function () { msg.textContent = 'Could not reach the Garden — try again in a minute.'; });
    };
  });
  // ---- back cover QR code (the barcode beside it encodes the same link) ----
  // ---- links that turn the book to a page (front-page index, "story on the … page"), and word-search taps ----
  document.addEventListener('click', function (ev) {
    var g = ev.target.closest && ev.target.closest('[data-goto]');
    if (g && g.dataset.goto && hasTurn) { ev.preventDefault(); ev.stopPropagation(); jQuery(book).turn('page', +g.dataset.goto); return; }
    var c = ev.target.closest && ev.target.closest('.ws td');
    if (c) c.classList.toggle('on');
  }, true);
  load();
})();
</script>@@SCRIPTS@@</body></html>"""


def main():
    ed = json.load(open(sys.argv[1]))
    date = ed.get("date") or dt.date.today().isoformat()
    os.makedirs(os.path.join(SITE, "editions"), exist_ok=True)
    pg = render(ed)
    open(os.path.join(SITE, "editions", date + ".html"), "w").write(pg)
    print("rendered %s: editions/%s.html" % (date, date))
    if "--no-build" not in sys.argv:   # home page (latest issue), back issues, B.I.G's catalog + plans
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT, "build_extras.py")], check=False)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render the profile README cards (SVG) for github.com/Adekunes.

Static cards (hero, pillars, repos) come from profile.json.
Live cards (heatmap, stats) come from the GitHub GraphQL contribution calendar.

Usage: GITHUB_TOKEN=... python scripts/build_cards.py
Needs: fonttools, brotli (text measurement against the embedded fonts).
"""
import base64, datetime as dt, json, os, subprocess, urllib.request
from collections import OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "cards"
CFG = json.loads((ROOT / "profile.json").read_text())

INK, BONE, LIME = "#0C0C0D", "#F4F1EA", "#C9FF3D"
INK_EDGE, BONE_EDGE = "#2A2B27", "#E2DDD1"
W = 840

# ---------- fonts ----------
FONT_FILES = {
    "sg400": "SpaceGrotesk-400.woff2", "sg500": "SpaceGrotesk-500.woff2",
    "sg700": "SpaceGrotesk-700.woff2", "sm400": "SpaceMono-400.woff2",
    "sm700": "SpaceMono-700.woff2",
}
_metrics = {}


def _font(key):
    if key not in _metrics:
        f = TTFont(FONTS / FONT_FILES[key])
        _metrics[key] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    return _metrics[key]


def measure(text, key, size, tracking=0.0):
    cmap, hmtx, upm = _font(key)
    total = 0
    for ch in text:
        g = cmap.get(ord(ch))
        total += hmtx[g][0] if g else upm * 0.5
    return total * size / upm + tracking * max(len(text) - 1, 0)


def wrap(text, key, size, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if measure(trial, key, size) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def font_css(*keys):
    fam = {"sg": "SG", "sm": "SM"}
    rules = []
    for k in keys:
        data = base64.b64encode((FONTS / FONT_FILES[k]).read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{fam[k[:2]]}';font-weight:{k[2:]};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
        )
    return "<style>" + "".join(rules) + (
        ".sg{font-family:'SG',sans-serif}.sm{font-family:'SM',monospace}"
    ) + "</style>"


def svg(w, h, body, fonts, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>{font_css(*fonts)}{body}</svg>\n"
    )


def card_bg(w, h, theme):
    fill = {"ink": INK, "bone": BONE, "lime": LIME}[theme]
    edge = {"ink": INK_EDGE, "bone": BONE_EDGE, "lime": "#B4E636"}[theme]
    return (f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" '
            f'fill="{fill}" stroke="{edge}"/>')


def arrow(x, y, color, size=12, diagonal=False):
    """Right arrow (or north-east arrow) drawn as a path; fonts lack the glyph."""
    s = size
    if diagonal:
        d = f"M{x} {y+s} L{x+s} {y} M{x+s*0.35} {y} L{x+s} {y} L{x+s} {y+s*0.65}"
    else:
        d = f"M{x} {y+s/2} L{x+s} {y+s/2} M{x+s*0.55} {y+s*0.1} L{x+s} {y+s/2} L{x+s*0.55} {y+s*0.9}"
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'


def kicker_dot(x, y, on="bone"):
    stroke = INK if on in ("bone", "lime") else LIME
    fill = LIME if on != "lime" else INK
    return f'<rect x="{x}" y="{y}" width="9" height="9" rx="1.5" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'


# ---------- static cards ----------
def hero():
    h, c = 330, CFG["hero"]
    body = [card_bg(W, h, "bone")]
    # ascii portrait, bleeding off the bottom right
    rows = (ROOT / "assets" / "portrait.txt").read_text().splitlines()
    fs, lh = 5.6, 5.6 * 1.2
    px, py = 498, 18
    body.append(f'<clipPath id="pc"><rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="18"/></clipPath>')
    body.append(f'<g clip-path="url(#pc)" class="sm" font-size="{fs}" fill="{INK}" fill-opacity="0.78">')
    for i, r in enumerate(rows):
        if r.strip():
            body.append(f'<text x="{px}" y="{py + (i+1)*lh:.1f}" xml:space="preserve">{escape(r)}</text>')
    body.append("</g>")
    # kicker
    body.append(kicker_dot(40, 40))
    body.append(f'<text x="58" y="49" class="sm" font-size="11.5" letter-spacing="1.6" fill="{INK}" fill-opacity="0.62">{escape(c["kicker"])}</text>')
    # name
    body.append(f'<text x="36" y="138" class="sg" font-weight="700" font-size="82" letter-spacing="-2.5" fill="{INK}">{escape(c["first"])}</text>')
    body.append(f'<text x="36" y="214" class="sg" font-weight="700" font-size="82" letter-spacing="-2.5" fill="{INK}">{escape(c["last"])}</text>')
    cx = 36 + measure(c["last"], "sg700", 82, -2.5) + 10
    body.append(
        f'<rect x="{cx:.1f}" y="156" width="20" height="62" fill="{LIME}" stroke="{INK}" stroke-width="1.5">'
        '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" repeatCount="indefinite"/></rect>'
    )
    # blurb
    for i, line in enumerate(wrap(c["blurb"], "sg400", 15.5, 420)):
        body.append(f'<text x="40" y="{254 + i*22}" class="sg" font-size="15.5" fill="{INK}" fill-opacity="0.82">{escape(line)}</text>')
    lw = measure(c["link"], "sm400", 12)
    body.append(f'<text x="40" y="306" class="sm" font-size="12" fill="{INK}">{escape(c["link"])}</text>')
    body.append(f'<rect x="40" y="310" width="{lw:.1f}" height="1.4" fill="{INK}"/>')
    body.append(arrow(40 + lw + 7, 297, INK, 9, diagonal=True))
    return svg(W, h, "".join(body), ["sg400", "sg700", "sm400"], f'{c["first"]} {c["last"]}, {c["kicker"]}')


def pillar(p):
    w, h = 272, 210
    t = p["theme"]
    fg = INK if t in ("lime", "bone") else BONE
    accent = INK if t == "lime" else (LIME if t == "ink" else INK)
    b = [card_bg(w, h, t)]
    b.append(f'<text x="24" y="38" class="sm" font-weight="700" font-size="11.5" letter-spacing="1.8" fill="{accent}">{escape(p["kicker"])}</text>')
    b.append(arrow(w - 38, 27, accent, 13))
    size = 27
    while measure(p["title"], "sg700", size, -0.8) > w - 48 and size > 18:
        size -= 1
    b.append(f'<text x="22" y="96" class="sg" font-weight="700" font-size="{size}" letter-spacing="-0.8" fill="{fg}">{escape(p["title"])}</text>')
    for i, line in enumerate(wrap(p["body"], "sg400", 14, w - 48)):
        b.append(f'<text x="24" y="{130 + i*20}" class="sg" font-size="14" fill="{fg}" fill-opacity="0.8">{escape(line)}</text>')
    return svg(w, h, "".join(b), ["sg400", "sg700", "sm700"], f'{p["kicker"]}: {p["title"]}. {p["body"]}')


def section(title, right):
    h = 64
    b = [card_bg(W, h, "ink")]
    b.append(f'<text x="28" y="41" class="sg" font-weight="500" font-size="23" letter-spacing="-0.4" fill="{BONE}">{escape(title)}</text>')
    rw = measure(right, "sm700", 11, 1.6)
    b.append(f'<text x="{W - 52 - rw:.1f}" y="37" class="sm" font-weight="700" font-size="11" letter-spacing="1.6" fill="{LIME}">{escape(right)}</text>')
    b.append(arrow(W - 44, 27, LIME, 12))
    return svg(W, h, "".join(b), ["sg500", "sm700"], title)


def repo(r):
    w, h = 272, 176
    b = [card_bg(w, h, "bone")]
    b.append(kicker_dot(22, 26))
    name = r["name"]
    size = 14
    while measure(name, "sm700", size) > w - 70 and size > 10:
        size -= 0.5
    b.append(f'<text x="40" y="35" class="sm" font-weight="700" font-size="{size}" fill="{INK}">{escape(name)}</text>')
    b.append(arrow(w - 36, 24, INK, 11, diagonal=True))
    for i, line in enumerate(wrap(r["body"], "sg400", 14, w - 44)):
        b.append(f'<text x="22" y="{72 + i*20}" class="sg" font-size="14" fill="{INK}" fill-opacity="0.8">{escape(line)}</text>')
    b.append(f'<line x1="22" y1="140" x2="{w-22}" y2="140" stroke="{INK}" stroke-opacity="0.12"/>')
    b.append(f'<text x="22" y="160" class="sm" font-size="11" fill="{INK}" fill-opacity="0.6">{escape(r["meta"])}</text>')
    return svg(w, h, "".join(b), ["sg400", "sm400", "sm700"], f'{name}: {r["body"]}')


# ---------- live data ----------
def token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def calendar():
    q = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"login": CFG["login"]}}).encode(),
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def today():
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=CFG["timezone_offset_hours"])).date()


def levels(days):
    nz = sorted(d["contributionCount"] for d in days if d["contributionCount"] > 0)
    if not nz:
        return lambda c: 0
    qs = [nz[min(len(nz) - 1, int(len(nz) * f))] for f in (0.25, 0.5, 0.75)]

    def lvl(c):
        if c <= 0:
            return 0
        return 1 + sum(c > q for q in qs)
    return lvl


def heatmap(weeks):
    h = 224
    days = [d for w in weeks for d in w["contributionDays"]]
    lvl = levels(days)
    pal = ["#1C1D1A", "#3B4719", "#6A8A20", "#9FCB2C", LIME]
    b = [card_bg(W, h, "ink")]
    b.append(f'<text x="32" y="50" class="sg" font-weight="500" font-size="25" letter-spacing="-0.4" fill="{BONE}">Every day, <tspan fill="{LIME}" font-weight="700">in lime</tspan></text>')
    lab = "REFRESHED DAILY"
    b.append(f'<text x="{W - 32 - measure(lab, "sm400", 10.5, 1.6):.1f}" y="46" class="sm" font-size="10.5" letter-spacing="1.6" fill="{BONE}" fill-opacity="0.5">{lab}</text>')
    n = len(weeks)
    step = (W - 64) / n
    cell = step * 0.78
    y0 = 76
    last_month = None
    legend_x = W - 32 - 5 * 14 - 70
    for wi, wk in enumerate(weeks):
        x = 32 + wi * step
        for d in wk["contributionDays"]:
            y = y0 + d["weekday"] * step
            c = pal[lvl(d["contributionCount"])]
            b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2" fill="{c}"><title>{d["date"]}: {d["contributionCount"]}</title></rect>')
        first = wk["contributionDays"][0]["date"]
        m = first[5:7]
        if m != last_month:
            if last_month is not None and x + 24 < legend_x - 8:
                mon = dt.date.fromisoformat(first).strftime("%b")
                b.append(f'<text x="{x:.1f}" y="{y0 + 7*step + 16:.1f}" class="sm" font-size="10" fill="{BONE}" fill-opacity="0.45">{mon}</text>')
            last_month = m
    # legend
    lx = W - 32 - 5 * 14 - 70
    ly = y0 + 7 * step + 6
    b.append(f'<text x="{lx}" y="{ly + 10:.1f}" class="sm" font-size="10" fill="{BONE}" fill-opacity="0.45">less</text>')
    for i, c in enumerate(pal):
        b.append(f'<rect x="{lx + 32 + i*14}" y="{ly:.1f}" width="11" height="11" rx="2" fill="{c}"/>')
    b.append(f'<text x="{lx + 32 + 5*14 + 4}" y="{ly + 10:.1f}" class="sm" font-size="10" fill="{BONE}" fill-opacity="0.45">more</text>')
    return svg(W, h, "".join(b), ["sg500", "sg700", "sm400"], "Contribution heatmap, last 12 months")


def streaks(days, now):
    counts = {d["date"]: d["contributionCount"] for d in days}
    ordered = sorted(counts)
    longest = run = 0
    for k in ordered:
        run = run + 1 if counts[k] > 0 else 0
        longest = max(longest, run)
    cur = 0
    day = now
    if counts.get(day.isoformat(), 0) == 0:
        day -= dt.timedelta(days=1)
    while counts.get(day.isoformat(), 0) > 0:
        cur += 1
        day -= dt.timedelta(days=1)
    return cur, longest


def stats(total, weeks):
    h = 284
    now = today()
    start = (now - dt.timedelta(days=364)).isoformat()
    days = [d for w in weeks for d in w["contributionDays"] if start <= d["date"] <= now.isoformat()]
    months = OrderedDict()
    y, m = now.year, now.month
    for _ in range(12):
        months[f"{y:04d}-{m:02d}"] = 0
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months = OrderedDict(reversed(list(months.items())))
    for d in days:
        k = d["date"][:7]
        if k in months:
            months[k] += d["contributionCount"]
    cur, longest = streaks(days, now)
    active = sum(1 for d in days if d["contributionCount"] > 0)
    busiest = max((d["contributionCount"] for d in days), default=0)

    b = [card_bg(W, h, "bone")]
    b.append(kicker_dot(36, 34))
    b.append(f'<text x="54" y="43" class="sm" font-size="11" letter-spacing="1.6" fill="{INK}" fill-opacity="0.6">THE LAST 12 MONTHS ON GITHUB</text>')
    num = f"{total:,}"
    b.append(f'<text x="34" y="96" class="sg" font-size="40" letter-spacing="-1" fill="{INK}"><tspan font-weight="700">{num}</tspan><tspan font-weight="400"> contributions</tspan></text>')
    # bars
    bx, by, bw_total, bh = 36, 238, 500, 100
    mx = max(months.values()) or 1
    slot = bw_total / 12
    bwid = slot * 0.66
    peak = max(months, key=months.get) if any(months.values()) else None
    for i, (k, v) in enumerate(months.items()):
        x = bx + i * slot
        hh = max(2, bh * v / mx) if v else 2
        if k == peak:
            b.append(f'<rect x="{x:.1f}" y="{by - hh:.1f}" width="{bwid:.1f}" height="{hh:.1f}" rx="2" fill="{LIME}" stroke="{INK}" stroke-width="1.4"/>')
            b.append(f'<text x="{x + bwid/2:.1f}" y="{by - hh - 7:.1f}" text-anchor="middle" class="sm" font-weight="700" font-size="10.5" fill="{INK}">{v}</text>')
        else:
            op = "0.88" if v else "0.15"
            b.append(f'<rect x="{x:.1f}" y="{by - hh:.1f}" width="{bwid:.1f}" height="{hh:.1f}" rx="2" fill="{INK}" fill-opacity="{op}"/>')
        mon = dt.date.fromisoformat(k + "-01").strftime("%b")
        b.append(f'<text x="{x + bwid/2:.1f}" y="{by + 18}" text-anchor="middle" class="sm" font-size="9.5" fill="{INK}" fill-opacity="0.5">{mon}</text>')
    # right column
    rx = 590
    rows = [
        (f"{cur}", " days" if cur != 1 else " day", f"CURRENT STREAK · LONGEST {longest}"),
        (f"{active}", f" / {len(days)}", "DAYS WITH A CONTRIBUTION"),
        (f"{busiest}", "", "ON THE BUSIEST DAY"),
    ]
    for i, (big, small, lab) in enumerate(rows):
        y = 92 + i * 66
        if i:
            b.append(f'<line x1="{rx}" y1="{y - 42}" x2="{W - 36}" y2="{y - 42}" stroke="{INK}" stroke-opacity="0.12"/>')
        b.append(f'<text x="{rx}" y="{y}" class="sg" font-size="30" letter-spacing="-0.6" fill="{INK}"><tspan font-weight="700">{big}</tspan><tspan font-weight="400" fill-opacity="0.45">{small}</tspan></text>')
        b.append(f'<text x="{rx}" y="{y + 18}" class="sm" font-size="9.5" letter-spacing="1.2" fill="{INK}" fill-opacity="0.55">{lab}</text>')
    return svg(W, h, "".join(b), ["sg400", "sg700", "sm400", "sm700"], f"{total} contributions in the last 12 months")


def main():
    OUT.mkdir(exist_ok=True)
    files = {"hero.svg": hero(), "section-building.svg": section("What I'm building", "ALL REPOS")}
    for p in CFG["pillars"]:
        files[f'pillar-{p["slug"]}.svg'] = pillar(p)
    for r in CFG["repos"]:
        files[f'repo-{r["slug"]}.svg'] = repo(r)
    total, weeks = calendar()
    files["heatmap.svg"] = heatmap(weeks)
    files["stats.svg"] = stats(total, weeks)
    for name, content in files.items():
        (OUT / name).write_text(content)
        print(f"wrote cards/{name} ({len(content)//1024} KB)")


if __name__ == "__main__":
    main()

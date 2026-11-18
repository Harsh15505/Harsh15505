#!/usr/bin/env python3
"""
Pokemon-themed profile README generator for Harsh15505.

  python scripts/profile.py build   # daily: every card, incl. private-repo stats
                                    # needs GH_STATS_TOKEN (classic PAT: repo, read:user)
  python scripts/profile.py catch   # issue-triggered: one Poke Ball throw
                                    # needs GITHUB_TOKEN, ISSUE_NUMBER, ISSUE_USER, GITHUB_REPOSITORY

Everything is drawn as self-contained SVG (sprites and font embedded), so
the cards render on GitHub without any external service. Private repo names
never appear in the output, only totals.

Sprites: PokeAPI (https://github.com/PokeAPI/sprites). Font: Press Start 2P (OFL).
Pokemon is (c) Nintendo / Game Freak / The Pokemon Company. Fan-made, non-commercial.
"""

import base64
import datetime as dt
import hashlib
import math
import html
import json
import os
import random
import struct
import sys
import textwrap
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
STATE_FILE = ROOT / "data" / "game.json"
FONT_B64 = base64.b64encode((ROOT / "scripts" / "fonts" / "PressStart2P-latin.woff2").read_bytes()).decode()
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
UA = {"User-Agent": "pokemon-profile-generator"}
MAX_DEX = 649  # gen 1-5: classic animated pixel sprites

# ---------------------------------------------------------------- content
# Hand-written facts. {commits:<repo>} is filled in from the repo at build time.
PROFILE = {
    "name": "HARSH BHAVSAR",
    "id": "15505",
    "class": "Backend Engineer",
    "region": "Ahmedabad, India",
    "money": "₹50L+ processed",
    "badges": ["MCP", "POS", "REALTIME", "OAUTH", "DOCKER", "ML", "IEEE", "SQL"],
    "partner": 727,  # Incineroar
    "parade": [25, 133, 1, 4, 7, 94, 448, 151],
    "dialog": ["HARSH builds backend systems that real", "businesses run on: POS, live queues & AI."],
}

# (pokemon id, tech, role, role colour type)
PARTY = [
    (233, "TypeScript", "LANGUAGE", "Water"),
    (1, "Node.js", "RUNTIME", "Grass"),
    (121, "React", "UI", "Psychic"),
    (197, "Next.js", "FRAMEWORK", "Dark"),
    (4, "Firebase", "REALTIME", "Fire"),
    (23, "Python", "LANGUAGE", "Poison"),
]

DEX = [
    dict(name="CHASKA POS", pid=143, types=[("REALTIME", "Electric"), ("MOBILE", "Grass")],
         desc="Hybrid Android POS working in 6 branches across Ahmedabad.",
         moves=["Firestore-transaction ordering", "Bluetooth ESC/POS printing", "OTA updates + UPI QR billing"],
         tiles=[("25,000+", "BILLS PLACED"), ("₹50L+", "REVENUE"), ("6", "BRANCHES")],
         stack="Next.js · Capacitor · Firebase", status="IN PRODUCTION"),
    dict(name="MCP SERVERS", pid=479, types=[("AI", "Psychic"), ("INTEGRATION", "Steel")],
         desc="Lets AI assistants work inside HubSpot, Zoho CRM and Shopify.",
         moves=["OAuth 2.0 + REST integrations", "Sandboxed runs: Docker + gVisor", "Redis + BullMQ task queues"],
         tiles=[("236", "TOOLS"), ("3", "SERVERS"), ("3", "PLATFORMS")],
         stack="TypeScript · Node.js · MCP SDK", status="CHAINTECH"),
    dict(name="MANGLESHWAR POS", pid=685, types=[("BACKEND", "Steel"), ("REALTIME", "Electric")],
         desc="Cloud POS and franchise ordering for a multi-branch bakery.",
         moves=["Role-based access per branch", "Live inventory + kitchen display", "Async printing, WhatsApp alerts"],
         tiles=[("{commits:mangleshwar-puff-pos}", "COMMITS"), ("KDS", "KITCHEN SCREEN"), ("RBAC", "ACCESS")],
         stack="Next.js · Supabase · PostgreSQL", status="IN PRODUCTION"),
    dict(name="KETLI VAAR?", pid=79, types=[("REALTIME", "Electric"), ("SAAS", "Fairy")],
         desc="Restaurant waitlists without pen and paper.",
         moves=["Join the queue by scanning a QR", "Live queue sync for staff", "WhatsApp 'your table is ready'"],
         tiles=[("{commits:ketli-vaar}", "COMMITS"), ("QR", "JOIN FLOW"), ("LIVE", "QUEUE")],
         stack="Next.js 16 · Supabase · Tailwind", status="PRIVATE"),
    dict(name="SHAHI SIGDI", pid=324, types=[("OFFLINE", "Rock"), ("REALTIME", "Electric")],
         desc="Restaurant POS that runs on the local network, no internet.",
         moves=["Express + Socket.io LAN server", "SQLite on-site storage", "Electron desktop billing"],
         tiles=[("{commits:Shahi-Sigdi}", "COMMITS"), ("LAN", "ONLY"), ("3", "SCREENS")],
         stack="Next.js · Express · SQLite · Electron", status="CLIENT"),
    dict(name="PRITI SALES", pid=52, types=[("MOBILE", "Grass"), ("BACKEND", "Steel")],
         desc="Android retail-sales app for a distribution business.",
         moves=["Capacitor Android app", "Supabase backend + auth", "Over-the-air updates"],
         tiles=[("{commits:Priti_sales_corporation}", "COMMITS"), ("OTA", "UPDATES"), ("APK", "ANDROID")],
         stack="React · Capacitor · Supabase", status="CLIENT"),
]

RESEARCH = dict(
    pid=110,
    title=["Evaluating the Association Between Ambient Air Pollution and",
           "Pediatric Respiratory Admissions Using Explainable ML"],
    venue="IEEE ICE2NT 2026 · ACCEPTED",
    tiles=[("1,110", "PATIENT RECORDS"), ("0.775", "AUC-ROC"), ("XGBOOST", "+ SHAP"), ("OPENAQ", "AIR DATA")],
)

# ---------------------------------------------------------------- palette
INK, MUTED, CREAM, LINE = "#222222", "#6B6B6B", "#FFFBEF", "#2B2B2B"
RED, RED_D, LCD = "#E3350D", "#A8250A", "#E4F3D3"
TYPE = {"Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0", "Electric": "#E8B90E", "Grass": "#62B23A",
        "Ice": "#5FC9C4", "Fighting": "#C22E28", "Poison": "#A33EA1", "Ground": "#D5A845", "Flying": "#8F78E8",
        "Psychic": "#F95587", "Bug": "#A6B91A", "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC",
        "Dark": "#705746", "Steel": "#8A8AA8", "Fairy": "#D685AD"}
LANG_TYPE = {"TypeScript": "Water", "Python": "Electric", "JavaScript": "Ground", "CSS": "Psychic",
             "Java": "Fire", "HTML": "Fire", "PLpgSQL": "Steel", "PHP": "Ghost"}


# ---------------------------------------------------------------- io
def fetch(url, data=None, headers=None, method=None):
    if os.environ.get("USE_CURL") and data is None:  # local fallback where Python's DNS misbehaves
        import subprocess
        args = ["curl", "-sfL", "--max-time", "60"]
        for k, v in {**UA, **(headers or {})}.items():
            args += ["-H", f"{k}: {v}"]
        return subprocess.run(args + [url], capture_output=True, check=True).stdout
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def gql(token, query, variables=None):
    body = json.loads(fetch("https://api.github.com/graphql",
                            json.dumps({"query": query, "variables": variables or {}}).encode(),
                            {"Authorization": f"bearer {token}"}))
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def rest(token, path, payload, method="POST"):
    return fetch(f"https://api.github.com{path}", json.dumps(payload).encode(),
                 {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, method)


# ---------------------------------------------------------------- sprites
SPRITE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/"
_sprites = {}


def sprite_url(pid, back=False):
    if pid <= MAX_DEX:
        return f"{SPRITE}versions/generation-v/black-white/animated/{'back/' if back else ''}{pid}.gif"
    return f"{SPRITE}other/showdown/{'back/' if back else ''}{pid}.gif"


def sprite(pid, back=False):
    key = (pid, back)
    if key not in _sprites:
        b = fetch(sprite_url(pid, back))
        w, h = struct.unpack("<HH", b[6:10])
        _sprites[key] = ("data:image/gif;base64," + base64.b64encode(b).decode(), w, h)
    return _sprites[key]


def img(pid, cx, base_y, scale=1.0, back=False, cls="", fit=None):
    """Sprite centred on cx, feet on base_y. fit=(max_w, max_h) caps the size."""
    uri, w, h = sprite(pid, back)
    if fit:
        scale = min(scale, fit[0] / w, fit[1] / h)
    W, H = w * scale, h * scale
    c = f' class="{cls}"' if cls else ""
    return (f'<image{c} href="{uri}" x="{cx - W / 2:.1f}" y="{base_y - H:.1f}" width="{W:.1f}" '
            f'height="{H:.1f}" style="image-rendering:pixelated"/>')


def species(pid):
    d = json.loads(fetch(f"https://pokeapi.co/api/v2/pokemon-species/{pid}"))
    name = next((n["name"] for n in d["names"] if n["language"]["name"] == "en"), d["name"])
    return name.upper(), d["capture_rate"]


# ---------------------------------------------------------------- svg helpers
BASE_CSS = (
    "@font-face{font-family:'PS2P';src:url(data:font/woff2;base64,%FONT%) format('woff2')}"
    ".px{font-family:'PS2P',ui-monospace,monospace}"
    ".sn{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif}"
    ".grow{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:grow 1.1s ease-out .3s forwards}"
    ".fade{opacity:0;animation:fade .5s ease forwards}"
    "@keyframes grow{to{transform:scaleX(1)}}"
    "@keyframes fade{to{opacity:1}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}.grow{transform:none}.fade{opacity:1}}"
)


def svg(w, h, body, css="", title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f'<style>{BASE_CSS.replace("%FONT%", FONT_B64)}{css}</style>{body}</svg>')


def esc(s):
    return html.escape(str(s), quote=True)


def t(x, y, s, size=12, fill=INK, cls="px", anchor="start", weight=None, extra=""):
    wt = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}"{wt} {extra}>{esc(s)}</text>')


def chip(x, y, label, typ, size=9):
    w = len(label) * size + 16
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{size + 11}" rx="{(size + 11) / 2}" fill="{TYPE[typ]}" '
            f'stroke="rgba(0,0,0,.25)"/>' + t(x + w / 2, y + size + 5, label, size, "#FFFFFF", anchor="middle"), w)


def panel(x, y, w, h, fill=CREAM, stroke=LINE, rx=12, sw=3):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def write(name, content):
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- cards
def header_svg(info):
    W, H = 1000, 440
    defs = ('<defs><linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#93C8FF"/>'
            '<stop offset="1" stop-color="#4C80D6"/></linearGradient>'
            f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="24"/></clipPath>'
            '<pattern id="grass" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="24" height="24" fill="#7CC657"/>'
            '<path d="M4 17l3-7 3 7M14 22l3-7 3 7" stroke="#55A536" stroke-width="2" fill="none"/></pattern></defs>')
    p = [defs, '<g clip-path="url(#clip)">', f'<rect width="{W}" height="{H}" fill="url(#card)"/>',
         f'<rect width="{W}" height="56" fill="#2C5AA0"/>',
         t(30, 37, "TRAINER CARD", 18, "#FFFFFF"), t(W - 30, 37, f"IDNo.{info['id']}", 14, "#FFE27A", anchor="end")]
    # details
    p.append(panel(24, 74, 652, 196, CREAM, "#2C5AA0", 14, 4))
    rows = [("NAME", info["name"]), ("CLASS", info["class"]), ("REGION", info["region"]),
            ("POKéDEX", f"{info['repos']} repositories"), ("MONEY", info["money"]), ("STARTED", info["started"])]
    for i, (k, v) in enumerate(rows):
        y = 106 + i * 29
        p.append(f'<g class="fade" style="animation-delay:{.1 * i:.1f}s">' + t(48, y, k, 11, MUTED) + t(214, y, v, 13) +
                 f'<line x1="48" y1="{y + 9}" x2="652" y2="{y + 9}" stroke="#E5DCC3" stroke-width="2" stroke-dasharray="4 4"/></g>')
    # partner pokemon (the profile photo already sits next to the README)
    p.append(panel(696, 74, 280, 196, CREAM, "#2C5AA0", 14, 4))
    p.append(f'<rect x="716" y="88" width="240" height="168" rx="10" fill="{LCD}" stroke="{LINE}" stroke-width="3"/>')
    p.append(t(836, 110, "PARTNER", 10, MUTED, anchor="middle"))
    p.append('<ellipse cx="836" cy="232" rx="70" ry="12" fill="#BFE3A6"/>')
    p.append(img(info["partner"], 836, 238, 2.0, fit=(200, 120)))
    # badges
    p.append(panel(24, 286, 952, 52, "#24467F", "#183563", 12, 3))
    p.append(t(44, 318, "BADGES", 11, "#FFE27A"))
    colors = ["#F95587", "#EE8130", "#E8B90E", "#62B23A", "#6390F0", "#A33EA1", "#B6A136", "#5FC9C4"]
    for i, b in enumerate(info["badges"]):
        x, cy = 150 + i * 103, 312
        n = 4 + i % 4

        pts = " ".join(f"{x + 12 + 11 * math.cos(math.pi * 2 * k / n - math.pi / 2):.1f},"
                       f"{cy + 11 * math.sin(math.pi * 2 * k / n - math.pi / 2):.1f}" for k in range(n))
        p.append(f'<g class="fade" style="animation-delay:{.5 + .08 * i:.2f}s"><polygon points="{pts}" fill="{colors[i]}" stroke="#FFFFFF" stroke-width="2"/>'
                 f'<circle cx="{x + 9}" cy="{cy - 4}" r="2.5" fill="#FFFFFF" opacity=".8"/>' + t(x + 30, cy + 4, b, 8, "#FFFFFF") + '</g>')
    # parade on the grass
    p.append(f'<rect x="0" y="352" width="{W}" height="{H - 352}" fill="url(#grass)"/>')
    p.append(f'<rect x="0" y="352" width="{W}" height="6" fill="#4E9A31"/>')
    group = []
    for i, pid in enumerate(info["parade"]):
        cx = 62 + i * (W / len(info["parade"]))
        group.append(f'<ellipse cx="{cx:.1f}" cy="428" rx="26" ry="6" fill="rgba(0,0,0,.18)"/>')
        group.append(img(pid, cx, 430, 1.0, fit=(96, 82)))
    # one copy of the sprites, drawn twice: a seamless conveyor belt
    p.append('<defs><g id="row">' + "".join(group) + '</g></defs>'
             f'<g class="walk"><use href="#row"/><use href="#row" x="{W}"/></g>')
    p.append("</g>")
    css = ".walk{animation:walk 34s linear infinite}@keyframes walk{from{transform:translateX(0)}to{transform:translateX(-1000px)}}"
    return svg(W, H, "".join(p), css, "Trainer card: Harsh Bhavsar, Backend Engineer")


def dialog_svg(lines):
    W, H, size = 1000, 132, 16
    p = [panel(6, 6, W - 12, H - 12, "#FFFFFF", "#3A3A3A", 16, 5),
         f'<rect x="16" y="16" width="{W - 32}" height="{H - 32}" rx="9" fill="none" stroke="#7FA4D8" stroke-width="3"/>']
    p.append(f'<clipPath id="box" clipPathUnits="userSpaceOnUse"><rect x="20" y="20" width="{W - 40}" height="{H - 40}"/></clipPath>')
    css, delay = [], 0.3
    for i, line in enumerate(lines):
        y = 60 + i * 38
        dur = len(line) * 0.045
        p.append(t(44, y, line, size))
        # white cover that slides right one character at a time = typewriter
        p.append(f'<g clip-path="url(#box)"><rect class="c{i}" x="40" y="{y - size - 4}" width="{len(line) * size + 24}" height="{size + 12}" fill="#FFFFFF"/></g>')
        css.append(f".c{i}{{animation:ty{i} {dur:.2f}s steps({len(line)}) {delay:.2f}s forwards}}"
                   f"@keyframes ty{i}{{to{{transform:translateX({len(line) * size}px)}}}}")
        delay += dur + 0.2
    last_x = 44 + len(lines[-1]) * size + 16
    p.append(f'<path class="arrow" d="M{last_x} {84} h14 l-7 9z" fill="{RED}"/>')
    css.append(f".arrow{{opacity:0;animation:blink .9s steps(1) {delay:.2f}s infinite}}@keyframes blink{{50%{{opacity:1}}}}")
    return svg(W, H, "".join(p), "".join(css), " ".join(lines))


def party_svg(members):
    rows = (len(members) + 1) // 2
    W, H = 1000, 70 + rows * 104
    p = [f'<rect width="{W}" height="{H}" rx="22" fill="#2E6FBF"/>',
         f'<rect x="10" y="10" width="{W - 20}" height="{H - 20}" rx="16" fill="none" stroke="#7FB2F0" stroke-width="2" stroke-dasharray="6 6"/>',
         t(32, 44, "MY PARTY", 16, "#FFFFFF"), t(W - 32, 44, "Lv. = repos that use it", 9, "#CFE3FF", anchor="end")]
    top = max(m["lv"] for m in members) or 1
    for i, m in enumerate(members):
        c, r = i % 2, i // 2
        x, y, w, h = 22 + c * 488, 62 + r * 104, 468, 92
        hp = m["lv"] / top
        bar = "#4CD964" if hp > .5 else "#F6C343" if hp > .2 else "#F0544F"
        g = [panel(x, y, w, h, "#E6F6FF", "#173D73", 14, 3),
             f'<ellipse cx="{x + 62}" cy="{y + 76}" rx="40" ry="9" fill="#B7DDF5"/>',
             img(m["pid"], x + 62, y + 82, 1.0, fit=(100, 84)),
             t(x + 124, y + 27, m["poke"], 9, MUTED),
             t(x + 124, y + 52, m["tech"], 15),
             t(x + w - 18, y + 27, f"Lv.{m['lv']}", 12, INK, anchor="end")]
        cp, cw = chip(x + 124, y + 62, m["role"], m["type"], 8)
        g.append(cp)
        bx = x + 124 + cw + 14
        g.append(t(bx, y + 77, "HP", 8, "#E5A100"))
        g.append(f'<rect x="{bx + 22}" y="{y + 68}" width="{x + w - 18 - bx - 22}" height="10" rx="5" fill="#4A4A4A"/>')
        g.append(f'<rect class="grow" x="{bx + 24}" y="{y + 70}" width="{(x + w - 18 - bx - 26) * max(hp, .04):.1f}" height="6" rx="3" fill="{bar}"/>')
        p.append(f'<g class="fade" style="animation-delay:{.08 * i:.2f}s">' + "".join(g) + "</g>")
    return svg(W, H, "".join(p), "", "My party: " + ", ".join(m["tech"] for m in members))


def dex_svg(no, e, commits):
    W, H = 490, 340

    def fill(v):
        if v.startswith("{commits:"):
            return f"{commits.get(v[9:-1], 0):,}"
        return v

    p = [f'<rect width="{W}" height="{H}" rx="20" fill="{RED}"/>', f'<rect x="0" y="{H - 18}" width="{W}" height="18" rx="0" fill="{RED_D}" opacity=".35"/>',
         t(22, 34, f"No.{no:03d}", 11, "#FFE0D6"), t(110, 34, e["name"], 14, "#FFFFFF"),
         '<circle class="led" cx="438" cy="28" r="7" fill="#7CF2FF" stroke="#FFFFFF" stroke-width="2"/>',
         '<circle cx="458" cy="28" r="4" fill="#FFD43B"/><circle cx="472" cy="28" r="4" fill="#5EE36B"/>',
         panel(14, 52, W - 28, H - 70, CREAM, "#7A1A06", 14, 3),
         f'<rect x="28" y="66" width="150" height="138" rx="10" fill="{LCD}" stroke="{LINE}" stroke-width="3"/>',
         '<ellipse cx="103" cy="186" rx="52" ry="10" fill="#BFE3A6"/>',
         img(e["pid"], 103, 190, 1.25, fit=(140, 118))]
    x = 194
    for label, typ in e["types"]:
        c, w = chip(x, 68, label, typ, 8)
        p.append(c)
        x += w + 8
    for i, line in enumerate(textwrap.wrap(e["desc"], 38)[:2]):
        p.append(t(194, 112 + i * 18, line, 13, INK, "sn", weight=600))
    for i, mv in enumerate(e["moves"]):
        p.append(f'<rect x="194" y="{146 + i * 20}" width="6" height="6" fill="{RED}"/>' + t(208, 153 + i * 20, mv, 12, "#444444", "sn"))
    tw = (W - 28 - 28 - 16) / 3
    for i, (v, lab) in enumerate(e["tiles"]):
        tx = 28 + i * (tw + 8)
        p.append(f'<g class="fade" style="animation-delay:{.3 + .12 * i:.2f}s">' + panel(tx, 218, tw, 56, "#FFFFFF", "#E3D7BA", 10, 2) +
                 t(tx + tw / 2, 245, fill(v), 13, INK, anchor="middle") + t(tx + tw / 2, 264, lab, 7, MUTED, anchor="middle") + "</g>")
    p.append(t(28, 302, e["stack"], 12, MUTED, "sn", weight=600))
    sw = len(e["status"]) * 7 + 16
    p.append(f'<rect x="{W - 28 - sw}" y="289" width="{sw}" height="18" rx="9" fill="{INK}"/>' +
             t(W - 28 - sw / 2, 302, e["status"], 7, "#FFFFFF", anchor="middle"))
    css = ".led{animation:led 2.4s ease-in-out infinite}@keyframes led{50%{fill:#C8FBFF}}"
    return svg(W, H, "".join(p), css, f"Pokedex No.{no:03d}: {e['name']}. {e['desc']}")


def research_svg(r):
    W, H = 1000, 236
    lines = "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#D9E6F5" stroke-width="1.5"/>' for y in range(40, H, 26))
    p = [f'<clipPath id="nb"><rect width="{W}" height="{H}" rx="18"/></clipPath><g clip-path="url(#nb)">',
         f'<rect width="{W}" height="{H}" fill="#FFFDF5"/>', lines,
         '<line x1="200" y1="0" x2="200" y2="236" stroke="#F2A0A0" stroke-width="2"/>', "</g>",
         f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="18" fill="none" stroke="{LINE}" stroke-width="3"/>',
         f'<rect x="28" y="40" width="150" height="150" rx="10" fill="{LCD}" stroke="{LINE}" stroke-width="3"/>',
         '<ellipse cx="103" cy="172" rx="52" ry="10" fill="#BFE3A6"/>', img(r["pid"], 103, 176, 1.3, fit=(140, 132)),
         t(226, 44, "PROF. NOTES", 12, RED), t(W - 28, 44, r["venue"], 10, MUTED, anchor="end")]
    for i, line in enumerate(r["title"]):
        p.append(t(226, 84 + i * 26, line, 18, INK, "sn", weight=700))
    tw = (W - 226 - 28 - 36) / 4
    for i, (v, lab) in enumerate(r["tiles"]):
        tx = 226 + i * (tw + 12)
        p.append(f'<g class="fade" style="animation-delay:{.2 + .1 * i:.1f}s">' + panel(tx, 140, tw, 62, "#FFFFFF", "#D8CFB6", 10, 2) +
                 t(tx + tw / 2, 170, v, 14, INK, anchor="middle") + t(tx + tw / 2, 190, lab, 7, MUTED, anchor="middle") + "</g>")
    return svg(W, H, "".join(p), "", "Research: " + " ".join(r["title"]))


def stats_svg(s, langs):
    W, H = 1000, 316
    p = [panel(2, 2, W - 4, H - 4, "#FFF9EC", LINE, 20, 3),
         f'<rect x="26" y="26" width="230" height="264" rx="14" fill="{LCD}" stroke="{LINE}" stroke-width="3"/>',
         t(141, 56, "PARTNER", 10, MUTED, anchor="middle"),
         '<ellipse cx="141" cy="236" rx="72" ry="14" fill="#BFE3A6"/>', img(25, 141, 242, 2.0, fit=(190, 170)),
         t(141, 274, "PIKACHU", 12, INK, anchor="middle"),
         t(290, 56, "BASE STATS", 14), t(760, 56, "incl. private repos", 9, MUTED, anchor="end")]
    rows = [("HP", "contributions", s["contrib"], 2000, "#FF5959"),
            ("ATTACK", "commits", s["commits"], 2000, "#F5AC78"),
            ("DEFENSE", "longest streak", s["longest"], 60, "#FAE078"),
            ("SP. ATK", "repositories", s["repos"], 100, "#9DB7F5"),
            ("SP. DEF", "live deployments", s["live"], 50, "#A7DB8D"),
            ("SPEED", "current streak", s["current"], 30, "#FA92B2")]
    for i, (k, desc, v, cap, col) in enumerate(rows):
        y = 92 + i * 34
        p.append(t(290, y, k, 10, INK) + t(290, y + 14, desc, 11, MUTED, "sn"))
        p.append(t(498, y + 4, f"{v:,}", 13, INK, anchor="end"))
        p.append(f'<rect x="514" y="{y - 8}" width="246" height="12" rx="6" fill="#ECE3CC"/>')
        p.append(f'<rect class="grow" style="animation-delay:{.2 + .1 * i:.1f}s" x="514" y="{y - 8}" '
                 f'width="{246 * min(1, max(v / cap, .03)):.1f}" height="12" rx="6" fill="{col}"/>')
    p.append(f'<line x1="790" y1="30" x2="790" y2="286" stroke="#E5DCC3" stroke-width="3" stroke-dasharray="5 5"/>')
    p.append(t(816, 56, "TYPES", 14))
    for i, (name, pct) in enumerate(langs[:6]):
        y = 80 + i * 34
        c, _ = chip(816, y, name.upper()[:10], LANG_TYPE.get(name, "Normal"), 8)
        p.append(f'<g class="fade" style="animation-delay:{.3 + .08 * i:.2f}s">{c}' + t(972, y + 14, f"{pct:.0f}%", 10, INK, anchor="end") + "</g>")
    p.append(t(816, 296, f"updated {s['updated']}", 8, MUTED))
    return svg(W, H, "".join(p), "", f"Base stats: {s['contrib']} contributions, {s['commits']} commits, {s['repos']} repositories")


def route_svg(weeks, total):
    W = 1000
    cell, gap = 15, 3
    gx, gy = (W - len(weeks) * (cell + gap) + gap) / 2, 92
    H = gy + 7 * (cell + gap) + 86
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"])
    q = [counts[int(len(counts) * f)] if counts else 1 for f in (.25, .5, .75)]
    shades = ["#E9DDB1", "#BFE48A", "#8CCB52", "#5BA834", "#2F7A1F"]
    p = [panel(2, 2, W - 4, H - 4, "#F4F9EC", LINE, 20, 3),
         '<rect x="28" y="22" width="190" height="40" rx="6" fill="#9C6B3C" stroke="#5E3B1C" stroke-width="3"/>',
         '<rect x="116" y="62" width="14" height="18" fill="#7A522C"/>', t(123, 48, "ROUTE 15505", 12, "#FFF3D6", anchor="middle"),
         t(W - 28, 40, f"{total:,} contributions in the last year", 13, INK, "sn", "end", 700),
         t(W - 28, 60, "each patch of grass is a day · taller grass, more commits", 11, MUTED, "sn", "end")]
    months, last = [], None
    for wi, w in enumerate(weeks):
        x = gx + wi * (cell + gap)
        m = w["contributionDays"][0]["date"][5:7]
        if m != last:
            months.append(t(x, gy - 8, dt.date(2000, int(m), 1).strftime("%b").upper(), 7, MUTED))
            last = m
        for d in w["contributionDays"]:
            c = d["contributionCount"]
            lvl = 0 if c == 0 else 1 + sum(c > v for v in q)
            y = gy + dt.date.fromisoformat(d["date"]).isoweekday() % 7 * (cell + gap)
            p.append(f'<rect x="{x:.1f}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{shades[lvl]}"/>')
            if lvl >= 3:
                p.append(f'<path d="M{x + 3:.1f} {y + 12}l2-6 2 6M{x + 8:.1f} {y + 12}l2-6 2 6" stroke="#245E17" stroke-width="1.4" fill="none"/>')
    p += months
    lane = gy + 7 * (cell + gap) + 10
    p.append(f'<rect x="20" y="{lane}" width="{W - 40}" height="58" rx="12" fill="#E9DDB1"/>')
    walkers = [133, 25]
    group = []
    for i, pid in enumerate(walkers):
        cx = 200 + i * 90
        group.append(f'<ellipse cx="{cx}" cy="{lane + 50}" rx="22" ry="5" fill="rgba(0,0,0,.15)"/>' + img(pid, cx, lane + 52, .8, fit=(70, 56)))
    p.append(f'<defs><g id="wk">' + "".join(group) + '</g></defs>'
             f'<clipPath id="ln"><rect x="20" y="{lane - 30}" width="{W - 40}" height="88"/></clipPath>'
             f'<g clip-path="url(#ln)"><g class="walk"><use href="#wk"/><use href="#wk" x="{W}"/></g></g>')
    css = ".walk{animation:walk 26s linear infinite}@keyframes walk{from{transform:translateX(0)}to{transform:translateX(-1000px)}}"
    return svg(W, H, "".join(p), css, f"Contribution graph: {total} contributions in the last year")


def encounter_svg(state):
    W, H = 1000, 340
    td = state["today"]
    p = ['<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#BFE9FF"/>'
         '<stop offset=".55" stop-color="#E9F8FF"/><stop offset=".56" stop-color="#A7DB7E"/><stop offset="1" stop-color="#86C95A"/></linearGradient>'
         f'<clipPath id="sc"><rect x="0" y="0" width="640" height="{H}" rx="20"/></clipPath></defs>',
         f'<rect width="{W}" height="{H}" rx="20" fill="#FFF9EC" stroke="{LINE}" stroke-width="3"/>',
         '<g clip-path="url(#sc)">', f'<rect width="640" height="{H}" fill="url(#sky)"/>',
         '<ellipse cx="470" cy="160" rx="110" ry="22" fill="#6FB548" stroke="#4E8F30" stroke-width="3"/>',
         '<ellipse cx="160" cy="262" rx="130" ry="24" fill="#6FB548" stroke="#4E8F30" stroke-width="3"/>',
         '<g class="appear">' + img(td["id"], 470, 166, 2.0, fit=(220, 150)) + "</g>",
         img(25, 160, 270, 2.2, back=True, fit=(170, 150)), "</g>",
         f'<line x1="640" y1="0" x2="640" y2="{H}" stroke="{LINE}" stroke-width="3"/>']
    # wild HP box
    p.append(panel(24, 22, 300, 70, "#FFFBEF", LINE, 12, 3))
    p.append(t(42, 50, td["name"][:12], 13) + t(306, 50, f"Lv.{td['level']}", 11, INK, anchor="end"))
    p.append(t(42, 76, "HP", 9, "#E5A100") + '<rect x="70" y="66" width="236" height="12" rx="6" fill="#4A4A4A"/>'
             '<rect x="73" y="69" width="230" height="6" rx="3" fill="#4CD964"/>')
    # dialog
    msg = f"A wild {td['name']} appeared!"
    p.append(panel(14, 284, 612, 44, "#FFFFFF", "#3A3A3A", 10, 4))
    p.append(t(32, 312, msg, 12) + f'<clipPath id="dl"><rect x="20" y="290" width="600" height="32"/></clipPath><g clip-path="url(#dl)"><rect class="cv" x="28" y="296" width="{len(msg) * 12 + 16}" height="24" fill="#FFFFFF"/></g>')
    # visitor dex
    dex = state["dex"]
    p.append(t(668, 46, "VISITOR DEX", 14) + t(668, 66, "caught by people visiting this page", 11, MUTED, "sn"))
    rows = [("SPECIES", f"{len(dex)} / {MAX_DEX}"), ("THROWS", f"{state['throws']:,}"), ("TRAINERS", f"{len(state['trainers']):,}"),
            ("TODAY", f"{sum(v == 'caught' for v in td['throws'].values())} caught, {sum(v == 'fled' for v in td['throws'].values())} fled")]
    for i, (k, v) in enumerate(rows):
        y = 100 + i * 28
        p.append(t(668, y, k, 9, MUTED) + t(976, y, v, 11, INK, anchor="end"))
    p.append(t(668, 222, "RECENT CATCHES", 9, MUTED))
    for i, c in enumerate(state["recent"][:5]):
        p.append(f'<rect x="{668 + i * 62}" y="232" width="54" height="54" rx="8" fill="{LCD}" stroke="#C9DDB4" stroke-width="2"/>'
                 + img(c["id"], 695 + i * 62, 282, .55, fit=(50, 48)))
    if not state["recent"]:
        p.append(t(668, 262, "none yet. be the first!", 12, MUTED, "sn"))
    p.append(t(668, 312, "new Pokémon every day at 00:00 IST", 11, MUTED, "sn"))
    css = (".appear{animation:appear .8s ease-out both}@keyframes appear{from{transform:translateX(120px);opacity:0}}"
           f".cv{{animation:cv {len(msg) * .05:.2f}s steps({len(msg)}) .8s forwards}}@keyframes cv{{to{{transform:translateX({len(msg) * 12}px)}}}}")
    return svg(W, H, "".join(p), css, f"A wild {td['name']} appeared! Visitors have caught {len(dex)} species.")


def button_svg():
    W, H = 640, 76
    p = [f'<rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="{(H - 6) / 2}" fill="{RED}" stroke="{LINE}" stroke-width="4"/>',
         f'<rect x="3" y="{H / 2}" width="{W - 6}" height="{H / 2 - 3}" rx="0" fill="#FFFFFF" opacity=".0"/>',
         '<g class="ball"><circle cx="46" cy="38" r="24" fill="#FFFFFF" stroke="#222" stroke-width="4"/>'
         '<path d="M22 38a24 24 0 0 1 48 0z" fill="#E3350D" stroke="#222" stroke-width="4"/>'
         '<circle cx="46" cy="38" r="7" fill="#FFFFFF" stroke="#222" stroke-width="4"/></g>',
         t(354, 46, "THROW A POKé BALL", 18, "#FFFFFF", anchor="middle")]
    css = ".ball{transform-box:fill-box;transform-origin:center;animation:wob 1.8s ease-in-out infinite}" \
          "@keyframes wob{0%,60%,100%{transform:rotate(0)}70%{transform:rotate(-18deg)}80%{transform:rotate(14deg)}90%{transform:rotate(-6deg)}}"
    return svg(W, H, "".join(p), css, "Throw a Poke Ball")


# ---------------------------------------------------------------- game state
def today_ist():
    return dt.datetime.now(IST).date().isoformat()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"date": None, "today": None, "dex": {}, "throws": 0, "trainers": [], "recent": []}


def roll_day(state):
    d = today_ist()
    if state.get("date") != d:
        h = int(hashlib.sha256(f"harsh-dex:{d}".encode()).hexdigest(), 16)
        pid, lv = 1 + h % MAX_DEX, 5 + (h >> 20) % 46
        name, rate = species(pid)
        state.update(date=d, today={"id": pid, "name": name, "level": lv, "capture_rate": rate, "throws": {}})
    return state


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- commands
def build():
    token = os.environ.get("GH_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Set GH_STATS_TOKEN to a classic PAT with repo + read:user.")
    me = gql(token, "{ viewer { login databaseId createdAt contributionsCollection { contributionCalendar {"
                    " totalContributions weeks { contributionDays { date contributionCount } } } } } }")["viewer"]
    repos, cursor = [], None
    while True:
        page = gql(token, """query($c:String){ viewer { repositories(first:25, after:$c, ownerAffiliations:OWNER, isFork:false){
            pageInfo{hasNextPage endCursor}
            nodes{ name isPrivate homepageUrl
              languages(first:10){edges{size node{name}}}
              defaultBranchRef{target{... on Commit{history{totalCount}}}}
              root: object(expression:"HEAD:"){... on Tree{entries{name}}}
              pkg: object(expression:"HEAD:package.json"){... on Blob{text}} } } } }""", {"c": cursor})["viewer"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    repos = [r for r in repos if r["name"].lower() != me["login"].lower()]

    # all-time contributions + streaks
    days, total = [], 0
    now = dt.datetime.now(dt.timezone.utc)
    for y in range(int(me["createdAt"][:4]), now.year + 1):
        cc = gql(token, """query($f:DateTime,$t:DateTime){ viewer { contributionsCollection(from:$f,to:$t){
            contributionCalendar{ totalContributions weeks{contributionDays{date contributionCount}} } } } }""",
                 {"f": f"{y}-01-01T00:00:00Z", "t": min(now, dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)).isoformat()}
                 )["viewer"]["contributionsCollection"]["contributionCalendar"]
        total += cc["totalContributions"]
        days += [d for w in cc["weeks"] for d in w["contributionDays"]]
    today = dt.datetime.now(IST).date().isoformat()
    seq = [d["contributionCount"] for d in sorted(days, key=lambda d: d["date"]) if d["date"] <= today]
    longest = run = 0
    for c in seq:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current, rev = 0, seq[::-1]
    if rev and rev[0] == 0:
        rev = rev[1:]
    for c in rev:
        if not c:
            break
        current += 1

    commits = {r["name"]: ((r["defaultBranchRef"] or {}).get("target") or {}).get("history", {}).get("totalCount", 0) for r in repos}
    stats = dict(contrib=total, commits=sum(commits.values()), longest=longest, current=current, repos=len(repos),
                 live=sum(1 for r in repos if r["homepageUrl"]), updated=dt.datetime.now(IST).strftime("%d %b %Y").upper())

    lang_bytes = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            if e["node"]["name"] not in {"Jupyter Notebook", "TeX", "PowerShell", "Shell", "Batchfile", "Dockerfile"}:
                lang_bytes[e["node"]["name"]] = lang_bytes.get(e["node"]["name"], 0) + e["size"]
    lt = sum(lang_bytes.values()) or 1
    langs = [(k, 100 * v / lt) for k, v in sorted(lang_bytes.items(), key=lambda kv: -kv[1])]

    # party levels = number of repos using each tech
    def uses(r, tech):
        names = {e["name"] for e in ((r.get("root") or {}).get("entries") or [])}
        try:
            pkg = json.loads(r["pkg"]["text"]) if r.get("pkg") else {}
        except ValueError:
            pkg = {}
        deps = set(pkg.get("dependencies", {})) | set(pkg.get("devDependencies", {}))
        langs_ = {e["node"]["name"] for e in r["languages"]["edges"]}
        return {
            "TypeScript": "TypeScript" in langs_,
            "Python": "Python" in langs_,
            "JavaScript": "JavaScript" in langs_,
            "Node.js": bool(pkg),
            "Next.js": "next" in deps,
            "React": "react" in deps,
            "PostgreSQL": bool(deps & {"pg", "postgres", "@supabase/supabase-js", "@prisma/client", "prisma", "typeorm"})
                          or "PLpgSQL" in langs_ or "supabase" in names,
            "Supabase": "@supabase/supabase-js" in deps or "supabase" in names,
            "Firebase": "firebase" in deps or "firebase-admin" in deps,
            "Docker": bool(names & {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}),
        }.get(tech, False)

    print("tech usage:", ", ".join(f"{k} {sum(uses(r, k) for r in repos)}" for k in
          ["TypeScript", "JavaScript", "Python", "Node.js", "Next.js", "React", "PostgreSQL", "Supabase", "Firebase", "Docker"]))
    members = []
    for pid, tech, role, typ in PARTY:
        members.append(dict(pid=pid, poke=species(pid)[0], tech=tech, role=role, type=typ,
                            lv=sum(uses(r, tech) for r in repos)))

    info = dict(PROFILE, repos=len(repos), started=dt.date.fromisoformat(me["createdAt"][:10]).strftime("%b %Y").upper())

    cal = me["contributionsCollection"]["contributionCalendar"]
    write("header.svg", header_svg(info))
    write("dialog.svg", dialog_svg(PROFILE["dialog"]))
    write("party.svg", party_svg(members))
    for i, e in enumerate(DEX, 1):
        write(f"dex-{i:03d}.svg", dex_svg(i, e, commits))
    write("research.svg", research_svg(RESEARCH))
    write("stats.svg", stats_svg(stats, langs))
    write("route.svg", route_svg(cal["weeks"], cal["totalContributions"]))
    write("button.svg", button_svg())
    state = roll_day(load_state())
    save_state(state)
    write("encounter.svg", encounter_svg(state))
    print(f"built: {stats['repos']} repos, {stats['contrib']} contributions, party "
          + ", ".join(f"{m['tech']} Lv.{m['lv']}" for m in members) + f", wild {state['today']['name']}")


def catch():
    token, repo = os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"]
    number, user = int(os.environ["ISSUE_NUMBER"]), os.environ["ISSUE_USER"]
    state = roll_day(load_state())
    td = state["today"]
    sprite_md = f'<img src="{sprite_url(td["id"])}" height="96" alt="{td["name"]}"/>'
    if user in td["throws"]:
        body = (f"{sprite_md}\n\n**You've already thrown a Poké Ball today, @{user}!**\n\n"
                f"The wild {td['name']} is still watching you. A new Pokémon appears at **00:00 IST**, come back then.")
    else:
        chance = .25 + .6 * td["capture_rate"] / 255
        caught = random.random() < chance
        td["throws"][user] = "caught" if caught else "fled"
        state["throws"] += 1
        if user not in state["trainers"]:
            state["trainers"].append(user)
        if caught:
            catchers = state["dex"].setdefault(str(td["id"]), [])
            new_species = not catchers
            catchers.append(user)
            state["recent"] = [{"id": td["id"], "name": td["name"], "user": user, "date": state["date"]}] + state["recent"][:19]
            body = (f"{sprite_md}\n\n### Gotcha! {td['name']} was caught!\n\n"
                    + (f"That's a **brand new species** for the Visitor Dex. " if new_species else "")
                    + f"Visitors have now caught **{len(state['dex'])} / {MAX_DEX}** species.\n\n"
                      f"Thanks for stopping by, @{user}. Come back tomorrow for a new Pokémon!")
        else:
            body = (f"{sprite_md}\n\n### Oh no! The wild {td['name']} broke free and fled!\n\n"
                    f"It had a {chance:.0%} catch rate, so better luck tomorrow, @{user}. "
                    f"A new Pokémon appears at **00:00 IST**.")
    save_state(state)
    write("encounter.svg", encounter_svg(state))
    rest(token, f"/repos/{repo}/issues/{number}/comments", {"body": body})
    rest(token, f"/repos/{repo}/issues/{number}", {"state": "closed", "state_reason": "completed"}, "PATCH")
    print(f"throw by {user}: {td['throws'].get(user)}")


if __name__ == "__main__":
    {"build": build, "catch": catch}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()

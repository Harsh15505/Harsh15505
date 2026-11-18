"""
Generates cute stats cards for the profile README, counting PRIVATE repos too.

Needs a token that can read your private repos:
  - in GitHub Actions: a classic PAT (scopes: repo, read:user) stored as the
    repository secret GH_STATS_TOKEN
  - locally: GITHUB_TOKEN=$(gh auth token) python scripts/gen_stats.py

Only totals are written to the SVGs. Private repo names never leave the script.
"""

import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets"
SKIP_LANGS = {"Jupyter Notebook", "TeX", "PowerShell", "Shell", "Batchfile", "Dockerfile"}

# pastel palette
BG, BORDER, INK, SOFT = "#FFF7FB", "#F9C6DA", "#5B4B8A", "#9A8CC0"
ACCENTS = ["#FF8FB1", "#B8A4FF", "#8FD3FF", "#A8E6CF", "#FFD59E", "#FFB5A7"]


def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch():
    viewer = gql("{ viewer { login createdAt } }")["viewer"]
    repos, cursor = [], None
    while True:
        page = gql(
            """query($c:String){ viewer { repositories(first:50, after:$c, ownerAffiliations:OWNER, isFork:false){
                 pageInfo{hasNextPage endCursor}
                 nodes{ isPrivate homepageUrl stargazerCount
                   languages(first:10){edges{size node{name color}}}
                   defaultBranchRef{target{... on Commit{history{totalCount}}}} } } } }""",
            {"c": cursor},
        )["viewer"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    days, total_contrib = [], 0
    start_year = int(viewer["createdAt"][:4])
    now = dt.datetime.now(dt.timezone.utc)
    for y in range(start_year, now.year + 1):
        cc = gql(
            """query($f:DateTime,$t:DateTime){ viewer { contributionsCollection(from:$f,to:$t){
                 contributionCalendar{ totalContributions weeks{contributionDays{date contributionCount}} } } } }""",
            {"f": f"{y}-01-01T00:00:00Z", "t": min(now, dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)).isoformat()},
        )["viewer"]["contributionsCollection"]["contributionCalendar"]
        total_contrib += cc["totalContributions"]
        days += [d for w in cc["weeks"] for d in w["contributionDays"]]
    return viewer, repos, days, total_contrib


def streaks(days):
    today = dt.date.today().isoformat()
    counts = [d["contributionCount"] for d in sorted(days, key=lambda d: d["date"]) if d["date"] <= today]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    rev = counts[::-1]
    if rev and rev[0] == 0:  # today not committed yet: don't break the streak
        rev = rev[1:]
    for c in rev:
        if not c:
            break
        current += 1
    return current, longest


def sparkle(x, y, s, color, delay):
    p = f"M{x},{y-s} Q{x},{y} {x+s},{y} Q{x},{y} {x},{y+s} Q{x},{y} {x-s},{y} Q{x},{y} {x},{y-s}Z"
    return f'<path class="tw" style="animation-delay:{delay}s" d="{p}" fill="{color}"/>'


def kitty(x, y):
    # tiny blinking cat that sits in the corner of the card
    return f'''<g transform="translate({x},{y})">
  <path d="M6,22 L10,4 L20,15 Q30,11 40,15 L50,4 L54,22 Q58,44 30,46 Q2,44 6,22Z" fill="#FFFFFF" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M12,10 L14,17 L18,14Z M48,10 L46,17 L42,14Z" fill="#FFC2D6"/>
  <g class="blink"><ellipse cx="21" cy="27" rx="2.6" ry="3.4" fill="{INK}"/><ellipse cx="39" cy="27" rx="2.6" ry="3.4" fill="{INK}"/></g>
  <ellipse cx="15" cy="34" rx="4" ry="2.4" fill="#FFB3CB" opacity=".8"/><ellipse cx="45" cy="34" rx="4" ry="2.4" fill="#FFB3CB" opacity=".8"/>
  <path d="M27,32 Q30,35 33,32" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>
</g>'''


STYLE = f"""<style>
  .t{{font:700 19px 'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:{INK}}}
  .l{{font:600 12.5px 'Segoe UI',Ubuntu,sans-serif;fill:{SOFT}}}
  .v{{font:800 22px 'Segoe UI',Ubuntu,sans-serif;fill:{INK}}}
  .s{{font:600 12px 'Segoe UI',Ubuntu,sans-serif;fill:{INK}}}
  .in{{opacity:0;animation:fade .6s ease forwards}}
  .tw{{transform-box:fill-box;transform-origin:center;animation:tw 2.4s ease-in-out infinite}}
  .blink{{transform-box:fill-box;transform-origin:center;animation:blink 4s infinite}}
  .grow{{transform-box:fill-box;transform-origin:left;animation:grow 1s ease forwards;transform:scaleX(0)}}
  @keyframes fade{{to{{opacity:1}}}}
  @keyframes tw{{0%,100%{{transform:scale(.6);opacity:.5}}50%{{transform:scale(1.1);opacity:1}}}}
  @keyframes blink{{0%,92%,100%{{transform:scaleY(1)}}95%{{transform:scaleY(.1)}}}}
  @keyframes grow{{to{{transform:scaleX(1)}}}}
</style>"""


def card(w, h, title, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
{STYLE}
<rect x="1.5" y="1.5" width="{w-3}" height="{h-3}" rx="20" fill="{BG}" stroke="{BORDER}" stroke-width="2.5" stroke-dasharray="7 5"/>
<text x="26" y="40" class="t">{title}</text>
{body}
</svg>'''


def stats_svg(repos, days, total_contrib):
    current, longest = streaks(days)
    commits = sum((r["defaultBranchRef"] or {}).get("target", {}).get("history", {}).get("totalCount", 0) for r in repos)
    live = sum(1 for r in repos if r["homepageUrl"])
    private = sum(1 for r in repos if r["isPrivate"])
    year = dt.date.today().year
    this_year = sum(d["contributionCount"] for d in days if d["date"].startswith(str(year)))
    items = [
        ("🌱", "contributions (all time)", f"{total_contrib:,}"),
        ("🍓", f"contributions in {year}", f"{this_year:,}"),
        ("🧁", "commits across my repos", f"{commits:,}"),
        ("🔥", "current streak", f"{current} days"),
        ("🏆", "longest streak", f"{longest} days"),
        ("📦", f"repos ({private} private)", f"{len(repos)}"),
        ("🚀", "apps deployed live", f"{live}"),
    ]
    body, x0, y0 = [], 26, 70
    for i, (emo, label, val) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = x0 + col * 205, y0 + row * 52
        body.append(
            f'<g class="in" style="animation-delay:{0.12*i:.2f}s"><text x="{x}" y="{y+18}" font-size="20">{emo}</text>'
            f'<text x="{x+32}" y="{y+14}" class="v">{val}</text><text x="{x+32}" y="{y+31}" class="l">{label}</text></g>'
        )
    body.append(kitty(355, 236))
    body.append(sparkle(300, 32, 7, ACCENTS[0], 0) + sparkle(326, 22, 5, ACCENTS[1], .8) + sparkle(400, 40, 6, ACCENTS[2], 1.4))
    return card(440, 300, "Harsh's coding garden", "\n".join(body))


def langs_svg(repos):
    c, colors = Counter(), {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in SKIP_LANGS:
                continue
            c[n] += e["size"]
            colors[n] = e["node"]["color"]
    total = sum(c.values()) or 1
    top = c.most_common(6)
    body, x, bar_w = [], 26, 388
    # stacked rounded bar
    body.append(f'<clipPath id="bar"><rect x="{x}" y="74" width="{bar_w}" height="14" rx="7"/></clipPath><g clip-path="url(#bar)" class="grow">')
    cx = x
    for i, (n, s) in enumerate(top):
        w = bar_w * s / sum(v for _, v in top)
        body.append(f'<rect x="{cx:.1f}" y="74" width="{w+0.5:.1f}" height="14" fill="{ACCENTS[i]}"/>')
        cx += w
    body.append("</g>")
    for i, (n, s) in enumerate(top):
        col, row = i % 2, i // 2
        px, py = x + col * 200, 136 + row * 44
        body.append(
            f'<g class="in" style="animation-delay:{0.15*i+.4:.2f}s"><circle cx="{px+7}" cy="{py-4}" r="7" fill="{ACCENTS[i]}"/>'
            f'<text x="{px+22}" y="{py}" class="s">{n}</text><text x="{px+170}" y="{py}" class="l" text-anchor="end">{100*s/total:.1f}%</text></g>'
        )
    body.append(sparkle(330, 30, 6, ACCENTS[3], .3) + sparkle(352, 20, 4, ACCENTS[4], 1.1))
    body.append('<text x="26" y="274" class="l">✿ includes private client repos · refreshed daily</text>')
    return card(440, 300, "Languages I speak", "\n".join(body))


def main():
    if not TOKEN:
        sys.exit("Set GITHUB_TOKEN (or GH_STATS_TOKEN) to a token that can read your private repos.")
    viewer, repos, days, total = fetch()
    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(stats_svg(repos, days, total), encoding="utf-8")
    (OUT / "languages.svg").write_text(langs_svg(repos), encoding="utf-8")
    print(f"ok: {viewer['login']} · {len(repos)} repos · {total} contributions")


if __name__ == "__main__":
    main()

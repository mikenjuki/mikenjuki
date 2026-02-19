"""
generate_langs.py
Fetches language stats from GitHub API and writes assets/langs.svg
Run via GitHub Actions with GITHUB_TOKEN set in environment.
"""

import os
import json
import math
import requests
from collections import defaultdict

USERNAME = "mikenjuki"
OUTPUT_PATH = "assets/langs.svg"

# Colours per language — extend as needed
LANG_COLORS = {
    "TypeScript":  "#3178c6",
    "JavaScript":  "#f1e05a",
    "Python":      "#3572A5",
    "Rust":        "#dea584",
    "Go":          "#00ADD8",
    "CSS":         "#563d7c",
    "HTML":        "#e34c26",
    "Shell":       "#89e051",
    "Dockerfile":  "#384d54",
    "MDX":         "#fcb32c",
}
DEFAULT_COLOR = "#8b949e"

def fetch_languages(token: str) -> dict[str, int]:
    headers = {"Authorization": f"Bearer {token}"}
    totals: dict[str, int] = defaultdict(int)

    page = 1
    while True:
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=10,
        )
        repos = resp.json()
        if not repos or not isinstance(repos, list):
            break

        for repo in repos:
            if repo.get("fork"):
                continue
            lang_url = repo.get("languages_url")
            if not lang_url:
                continue
            lr = requests.get(lang_url, headers=headers, timeout=10)
            for lang, bytes_ in lr.json().items():
                totals[lang] += bytes_

        if len(repos) < 100:
            break
        page += 1

    return dict(totals)


def top_n(langs: dict[str, int], n: int = 8) -> list[tuple[str, int]]:
    sorted_ = sorted(langs.items(), key=lambda x: x[1], reverse=True)
    top = sorted_[:n]
    total = sum(v for _, v in top)
    return top, total


def make_svg(top: list[tuple[str, int]], total: int) -> str:
    cx, cy, r_outer, r_inner = 110, 110, 90, 52
    gap_deg = 2.0

    slices = []
    start = -90.0
    for lang, bytes_ in top:
        pct = bytes_ / total
        sweep = pct * 360 - gap_deg
        slices.append((lang, pct, start, sweep))
        start += pct * 360

    def polar(cx, cy, r, deg):
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    def arc_path(cx, cy, ro, ri, start_deg, sweep_deg):
        x1o, y1o = polar(cx, cy, ro, start_deg)
        x2o, y2o = polar(cx, cy, ro, start_deg + sweep_deg)
        x1i, y1i = polar(cx, cy, ri, start_deg + sweep_deg)
        x2i, y2i = polar(cx, cy, ri, start_deg)
        large = 1 if sweep_deg > 180 else 0
        return (
            f"M {x1o:.3f} {y1o:.3f} "
            f"A {ro} {ro} 0 {large} 1 {x2o:.3f} {y2o:.3f} "
            f"L {x1i:.3f} {y1i:.3f} "
            f"A {ri} {ri} 0 {large} 0 {x2i:.3f} {y2i:.3f} Z"
        )

    # SVG dimensions
    width, height = 340, 220
    legend_x = 215

    paths_svg = []
    for lang, pct, start_deg, sweep_deg in slices:
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)
        d = arc_path(cx, cy, r_outer, r_inner, start_deg, sweep_deg)
        paths_svg.append(
            f'  <path d="{d}" fill="{color}">'
            f'<title>{lang} {pct*100:.1f}%</title></path>'
        )

    legend_items = []
    for i, (lang, pct, _, _) in enumerate(slices):
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)
        y = 30 + i * 22
        legend_items.append(
            f'  <rect x="{legend_x}" y="{y}" width="10" height="10" rx="2" fill="{color}"/>'
            f'  <text x="{legend_x + 16}" y="{y + 9}" '
            f'font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" fill="#c9d1d9">'
            f'{lang} <tspan fill="#8b949e">{pct*100:.1f}%</tspan></text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="12" fill="#0d1117"/>
  <text x="{cx}" y="16" text-anchor="middle"
    font-family="ui-monospace,SFMono-Regular,monospace" font-size="11"
    font-weight="600" fill="#8b949e" letter-spacing="1">TOP LANGUAGES</text>
{"".join(paths_svg)}
  <text x="{cx}" y="{cy + 5}" text-anchor="middle"
    font-family="ui-monospace,SFMono-Regular,monospace" font-size="11" fill="#8b949e">languages</text>
{"".join(legend_items)}
</svg>"""
    return svg


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set")

    print("Fetching language stats...")
    langs = fetch_languages(token)
    if not langs:
        raise SystemExit("No language data found")

    top, total = top_n(langs, n=8)
    print("Top languages:", [(l, f"{b/total*100:.1f}%") for l, b in top])

    svg = make_svg(top, total)
    os.makedirs("assets", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"Written → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

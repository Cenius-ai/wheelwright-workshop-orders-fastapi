"""Tier-C UI verification for the running app (no browser in this sandbox).

Checks every route for status, real text, leak strings, asset resolution and
computes the token contrast pairs.

Target the app with APP_BASE_URL (default http://127.0.0.1:$PORT, i.e. a local
dev server), so the same check works against a split deploy or a remote host:

    APP_BASE_URL=https://wheelwright.example.co.uk python3 scripts/ui_check.py
"""

from __future__ import annotations

import os
import re
import sys

import httpx

BASE = os.environ.get("APP_BASE_URL") or f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
LEAK = re.compile(r"\b(nan|NaN|None|null|undefined|Invalid Date|\[object Object\])\b|-\d+ days ago")
ROUTES = ["/", "/wheels", "/wheels/new", "/wheels/1", "/schedule", "/schedule?month=2026-12", "/clients", "/clients/1", "/login", "/register", "/nope-404"]

failures: list[str] = []


def text_of(html: str) -> str:
    body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()


def main() -> int:
    with httpx.Client(base_url=BASE, follow_redirects=True, timeout=20) as client:
        login_page = client.get("/login")
        assert login_page.status_code == 200
        client.post("/login", data={"email": "cenius@cenius.ai", "password": "cenius"})

        for route in ROUTES:
            response = client.get(route)
            body = response.text
            text = text_of(body)
            problems = []
            expected = [404] if route == "/nope-404" else []
            if expected:
                if response.status_code != 404:
                    problems.append(f"status {response.status_code} != 404")
            elif response.status_code >= 400:
                problems.append(f"status {response.status_code}")
            if not expected and len(text) < 400:
                problems.append(f"only {len(text)} chars of text")
            if route != "/login" and LEAK.search(text):
                problems.append(f"leak: {LEAK.search(text).group(0)!r}")
            if body.count("<h1") != 1:
                problems.append(f"h1 count {body.count('<h1')}")
            for ref in set(re.findall(r'(?:href|src)="(/static/[^"]+)"', body)):
                asset = client.get(ref)
                if asset.status_code != 200:
                    problems.append(f"asset {ref} -> {asset.status_code}")
            css = client.get("/static/css/app.css")
            if css.headers.get("content-type", "").split(";")[0] != "text/css":
                problems.append("css content-type " + css.headers.get("content-type", ""))
            if problems:
                failures.append(f"{route}: " + "; ".join(problems))
                print("FAIL", route, "; ".join(problems))
            else:
                print("ok  ", route, response.status_code, f"{len(text)} chars")

        # Security headers on an authenticated page
        page = client.get("/wheels")
        for header in ("content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy"):
            if header not in page.headers:
                failures.append(f"missing header {header}")
                print("FAIL missing header", header)

    # Token contrast pairs (relative luminance, WCAG 2.1)
    def lum(hex_colour: str) -> float:
        hex_colour = hex_colour.lstrip("#")
        channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def ratio(fg: str, bg: str) -> float:
        a, b = lum(fg), lum(bg)
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    pairs = [
        ("foreground on background", "#eef0f3", "#090d10", 4.5),
        ("foreground on card", "#eef0f3", "#14181c", 4.5),
        ("muted-foreground on card", "#9a9fa5", "#14181c", 4.5),
        ("muted-foreground on background", "#9a9fa5", "#090d10", 4.5),
        ("accent on background", "#3faff3", "#090d10", 4.5),
        ("accent on card", "#3faff3", "#14181c", 4.5),
        ("on-accent on accent", "#111111", "#3faff3", 4.5),
        ("on-destructive on destructive", "#ffffff", "#c9302d", 4.5),
        ("placeholder on background", "#767c83", "#090d10", 4.5),
        ("field error on card", "#ff9c99", "#14181c", 4.5),
        ("control border on background", "#5f6871", "#090d10", 3.0),
        ("control border on card", "#5f6871", "#14181c", 3.0),
        ("ring on background", "#3faff3", "#090d10", 3.0),
        ("status build on card", "#7cc4f5", "#14181c", 4.5),
        ("status tyre on card", "#e6b25c", "#14181c", 4.5),
        ("status complete on card", "#6ddba0", "#14181c", 4.5),
        ("status cancelled on card", "#b0b6bd", "#14181c", 4.5),
    ]
    for label, fg, bg, floor in pairs:
        value = ratio(fg, bg)
        status = "ok  " if value >= floor else "FAIL"
        if value < floor:
            failures.append(f"contrast {label}: {value:.2f} < {floor}")
        print(f"{status} contrast {label}: {value:.2f} (>= {floor})")

    print()
    print("FAILURES:", len(failures))
    for line in failures:
        print(" -", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

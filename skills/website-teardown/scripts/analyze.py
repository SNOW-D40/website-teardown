#!/usr/bin/env python3
"""
website-teardown — analyze publicly accessible web pages.

Compliance-first by design:
  * identifies itself honestly (no spoofed browser User-Agent)
  * reads and respects robots.txt by default
  * rate-limits requests (randomized delay)
  * extracts metadata only — never downloads or stores images, never
    redistributes page copy

Standard library only. Python 3.8+.
"""

import argparse
import json
import random
import re
import statistics
import sys
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

DEFAULT_UA = "website-teardown/0.1 (+https://github.com/SNOW-D40/website-teardown)"
MAX_HTML_BYTES = 2_000_000
MAX_CSS_BYTES = 400_000
MAX_CSS_FILES = 3
MAX_PAGES_DEFAULT = 20

PLATFORM_SIGNATURES = {
    "Shopify": ["cdn.shopify.com", "shopify.theme", "window.shopify", "/cdn/shop/"],
    "WooCommerce": ["woocommerce", "wp-content/plugins/woocommerce"],
    "WordPress": ["wp-content", "wp-includes"],
    "Magento": ["magento", "static/version", "mage/"],
    "BigCommerce": ["bigcommerce.com", "cdn11.bigcommerce.com"],
    "Squarespace": ["squarespace.com", "static1.squarespace.com"],
    "Wix": ["wix.com", "wixstatic.com"],
    "Shopware": ["shopware"],
}

APP_SIGNATURES = {
    "Klaviyo": ["klaviyo"],
    "Judge.me": ["judge.me", "judgeme"],
    "Yotpo": ["yotpo"],
    "Loox": ["loox"],
    "Stamped": ["stamped.io"],
    "Recharge": ["rechargepayments", "recharge"],
    "Gorgias": ["gorgias"],
    "Tidio": ["tidio"],
    "Mailchimp": ["mailchimp", "chimpstatic"],
    "Swiper": ["swiper"],
    "GSAP": ["gsap"],
    "Algolia": ["algolia"],
    "Hotjar": ["hotjar"],
    "Google Analytics": ["googletagmanager", "google-analytics", "gtag("],
    "Meta Pixel": ["connect.facebook.net", "fbq("],
}

HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
FONT_RE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.IGNORECASE)
PRICE_RE = re.compile(r"(?:[$€£¥￥]|USD|EUR|GBP)\s?(\d{1,5}(?:[.,]\d{1,2})?)")
CSS_URL_RE = re.compile(r"url\(([^)]*)\)")


class PageParser(HTMLParser):
    """Collects structural metadata. Text is kept only long enough to
    mine price ranges and is never written to the report."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = []
        self.h2 = []
        self.stylesheets = []
        self.inline_css = []
        self.script_srcs = []
        self.meta = {}
        self.img_count = 0
        self.text_chunks = []
        self._in_title = False
        self._in_style = False
        self._heading = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "style":
            self._in_style = True
        elif tag in ("h1", "h2"):
            self._heading = tag
        elif tag == "img":
            self.img_count += 1
        elif tag == "link":
            rel = a.get("rel", "").lower()
            href = a.get("href", "")
            if "stylesheet" in rel and href:
                self.stylesheets.append(href)
        elif tag == "script" and a.get("src"):
            self.script_srcs.append(a["src"])
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower().strip()
            if name and a.get("content"):
                self.meta[name] = a["content"]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "style":
            self._in_style = False
        elif tag in ("h1", "h2"):
            self._heading = None

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += data
        elif self._in_style:
            self.inline_css.append(data)
        elif self._heading == "h1":
            self.h1.append(text)
        elif self._heading == "h2":
            self.h2.append(text)
        else:
            self.text_chunks.append(text)


def _safe_stdio():
    """Windows consoles default to a legacy codepage (e.g. cp936) that cannot
    encode every character we print. Degrade instead of crashing."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def fetch(url, ua, timeout, max_bytes):
    req = Request(url, headers={"User-Agent": ua, "Accept": "text/html,text/css,*/*"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read(max_bytes)
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, "replace")


def robots_allows(base_url, ua, timeout):
    """Returns (allowed, reason). Missing robots.txt is treated as allow."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except HTTPError as exc:
        return True, f"robots.txt HTTP {exc.code} (treated as allow)"
    except (URLError, OSError) as exc:
        return True, f"robots.txt unreachable ({exc.__class__.__name__}, treated as allow)"
    allowed = rp.can_fetch(ua, base_url)
    if allowed:
        return True, "robots.txt allows"
    return False, "robots.txt disallows"


def normalize_hex(h):
    h = h.lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def is_neutral(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    spread = max(r, g, b) - min(r, g, b)
    return spread < 12  # greys, near-white, near-black


def top_colors(css_text, limit=5):
    counts = {}
    for m in HEX_RE.finditer(css_text):
        c = normalize_hex(m.group(0)[1:])
        if is_neutral(c):
            continue
        counts[c] = counts.get(c, 0) + 1
    return [c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]


def top_fonts(css_text, limit=3):
    counts = {}
    for m in FONT_RE.finditer(css_text):
        family = m.group(1).split(",")[0].strip().strip("\"'").strip()
        if not family or family.startswith("var(") or len(family) > 40:
            continue
        key = family.lower()
        counts[key] = counts.get(key, 0) + 1
    return [f for f, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]


def detect(signatures, haystack):
    hits = []
    for name, needles in signatures.items():
        if any(n.lower() in haystack for n in needles):
            hits.append(name)
    return hits


def price_range(text):
    values = []
    for m in PRICE_RE.finditer(text):
        raw = m.group(1).replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            continue
        if 1 <= v <= 10000:
            values.append(v)
    if not values:
        return None
    values.sort()
    return {
        "min": round(values[0], 2),
        "median": round(statistics.median(values), 2),
        "max": round(values[-1], 2),
        "samples": len(values),
    }


def analyze(url, ua, timeout, respect_robots):
    result = {"url": url, "ok": False, "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    if respect_robots:
        allowed, reason = robots_allows(url, ua, timeout)
        result["robots"] = reason
        if not allowed:
            result["error"] = "skipped: robots.txt disallows automated access"
            return result

    try:
        html = fetch(url, ua, timeout, MAX_HTML_BYTES)
    except HTTPError as exc:
        result["error"] = f"HTTP {exc.code}"
        return result
    except (URLError, OSError) as exc:
        result["error"] = f"{exc.__class__.__name__}: {exc}"
        return result

    parser = PageParser()
    try:
        parser.feed(html)
    except Exception as exc:  # malformed markup should not kill the run
        result["parse_warning"] = f"{exc.__class__.__name__}: {exc}"

    css_parts = list(parser.inline_css)
    for href in parser.stylesheets[:MAX_CSS_FILES]:
        try:
            css_parts.append(fetch(urljoin(url, href), ua, timeout, MAX_CSS_BYTES))
        except Exception:
            continue
    css_text = "\n".join(css_parts)

    haystack = html.lower()
    page_text = " ".join(parser.text_chunks)

    result.update(
        {
            "ok": True,
            "title": parser.title.strip()[:200],
            "description": (parser.meta.get("description") or parser.meta.get("og:description") or "")[:300],
            "h1_count": len(parser.h1),
            "h1": [h[:120] for h in parser.h1[:3]],
            "h2_count": len(parser.h2),
            "img_count": parser.img_count,
            "css_files": len(parser.stylesheets),
            "js_files": len(parser.script_srcs),
            "platform": detect(PLATFORM_SIGNATURES, haystack),
            "apps": detect(APP_SIGNATURES, haystack),
            "colors": top_colors(css_text),
            "fonts": top_fonts(css_text),
            "price_range": price_range(page_text),
            "has_og_tags": "og:title" in parser.meta,
            "has_structured_data": "application/ld+json" in haystack,
        }
    )
    return result


def to_markdown(results):
    lines = [
        "| Site | Platform | Colors | Fonts | Price band | Apps |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        if not r.get("ok"):
            lines.append(f"| {r['url']} | — | — | — | — | FAIL: {r.get('error', 'failed')} |")
            continue
        colors = " ".join(r["colors"][:3]) or "—"
        fonts = ", ".join(r["fonts"][:2]) or "—"
        pr = r.get("price_range")
        band = f"${pr['min']:g}–${pr['max']:g}" if pr else "—"
        apps = ", ".join(r["apps"][:4]) or "—"
        platform = ", ".join(r["platform"][:2]) or "—"
        lines.append(f"| {r['url']} | {platform} | {colors} | {fonts} | {band} | {apps} |")
    lines.append("")
    lines.append("> Metadata only. No page copy, images, or screenshots are collected or redistributed.")
    return "\n".join(lines)


def main(argv=None):
    _safe_stdio()
    ap = argparse.ArgumentParser(
        prog="website-teardown",
        description="Analyze publicly accessible pages and emit a comparison report.",
    )
    ap.add_argument("urls", nargs="+", help="page URLs to analyze (public pages only)")
    ap.add_argument("--json", metavar="FILE", help="write raw results as JSON")
    ap.add_argument("--md", metavar="FILE", help="write the markdown report to FILE")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                    help=f"hard cap on URLs per run (default {MAX_PAGES_DEFAULT})")
    ap.add_argument("--timeout", type=float, default=15.0, help="per-request timeout in seconds")
    ap.add_argument("--delay", type=float, default=2.0, help="base delay between requests (seconds)")
    ap.add_argument("--user-agent", default=DEFAULT_UA, help="User-Agent string (identify yourself)")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="DANGEROUS: ignore robots.txt. Do not use on third-party sites.")
    args = ap.parse_args(argv)

    urls = args.urls[: args.max_pages]
    if len(args.urls) > args.max_pages:
        print(f"[warn] {len(args.urls)} URLs given, capped at --max-pages {args.max_pages}", file=sys.stderr)

    results = []
    for i, url in enumerate(urls):
        if not urlparse(url).scheme:
            url = "https://" + url
        print(f"[{i + 1}/{len(urls)}] {url}", file=sys.stderr)
        results.append(analyze(url, args.user_agent, args.timeout, not args.ignore_robots))
        if i < len(urls) - 1:
            time.sleep(args.delay + random.uniform(0, 1.0))

    report = to_markdown(results)
    print(report)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        print(f"[ok] JSON written to {args.json}", file=sys.stderr)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
        print(f"[ok] Markdown written to {args.md}", file=sys.stderr)

    failed = sum(1 for r in results if not r.get("ok"))
    return 1 if failed == len(results) else 0


if __name__ == "__main__":
    sys.exit(main())

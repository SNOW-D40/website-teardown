# website-teardown

> Analyze publicly accessible web pages into a metadata comparison report —
> platform, palette, fonts, price band, installed apps. **Analysis, not copying.**

📖 中文使用说明书 → [`docs/使用说明书.md`](docs/使用说明书.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#)

```bash
python3 skills/website-teardown/scripts/analyze.py kettl.co ollieandjames.com
```

```
| Site                  | Platform | Colors                   | Fonts                    | Price band  | Apps                      |
| --------------------- | -------- | ------------------------ | ------------------------ | ----------- | ------------------------- |
| https://kettl.co      | Shopify  | #dd6444 #467c99 #38637a  | otto                     | $26–$150    | Klaviyo, Recharge         |
| https://www.allbirds… | Shopify  | #e0dacf #03143b #9c0f0f  | geograph, akkurat mono   | $5–$105     | Yotpo, Swiper, GA         |
```

Real run against six live storefronts: [`examples/sample-report.md`](examples/sample-report.md) ·
raw output: [`examples/sample-raw.json`](examples/sample-raw.json). Gymshark and Blue
Bottle appear with their refusal reason rather than being silently dropped — that's
the tool respecting `robots.txt`.

## Why

Building a storefront, writing a pitch, or benchmarking a category usually starts
with the same manual chore: open five sites, eyeball the fonts, guess the
platform, screenshot everything, paste it into a doc.

This does that chore in one command — and stops exactly where the useful part
ends. You get **measurable metadata**, not someone else's content.

## What it extracts

| Field | How |
| --- | --- |
| Platform | Signature detection from asset URLs + `generator` meta — 15 platforms: Shopify, WooCommerce, WordPress, PrestaShop, Magento, BigCommerce, Wix, Squarespace, Shopware, Shoplazza, Shopline, Ueeshop, XShoppy, SHOPPY, Youzan |
| Palette | Hex frequency across inline + up to 3 linked stylesheets, neutrals filtered out |
| Fonts | `font-family` frequency, ranked |
| Price band | Currency-prefixed numbers in visible text → min / median / max |
| Apps | Klaviyo, Judge.me, Yotpo, Recharge, Gorgias, Tidio, Algolia, GA, Meta Pixel, … |
| Structure | h1/h2 counts, image count, CSS/JS file counts, Open Graph tags, JSON-LD presence |

No dependencies. One file. Standard library only.

## Install as an agent skill

This repo ships the tool as an [Agent Skill](https://docs.claude.com/en/docs/claude-code/skills)
as well as a plain CLI — same code, two ways to consume it.

**Claude Code / compatible agents:**

```bash
git clone https://github.com/SNOW-D40/website-teardown.git
cp -r website-teardown/skills/website-teardown ~/.claude/skills/
```

On Windows:

```powershell
git clone https://github.com/SNOW-D40/website-teardown.git
Copy-Item -Recurse website-teardown\skills\website-teardown "$env:USERPROFILE\.claude\skills\"
```

**DeepSeek Harness / npm-based hosts:** the `skills/` folder is the contract —
point your profile at it, or vendor the directory.

**Just the CLI:** clone and run `analyze.py` directly. That's it.

## Usage

```bash
python3 skills/website-teardown/scripts/analyze.py URL [URL ...] [options]
```

Requires **Python 3.8+** and nothing else — no `pip install`. On Windows use
`python` (or `py -3`) in place of `python3`; the [Chinese manual](docs/使用说明书.md)
walks through the PowerShell paths.

| Option | Default | Description |
| --- | --- | --- |
| `--input FILE` | — | Read extra URLs from a file (one per line, `#` comments, BOM-safe) |
| `--md FILE` | — | Write the markdown report |
| `--json FILE` | — | Write raw structured results |
| `--max-pages N` | `20` | Hard cap on URLs per run |
| `--delay S` | `2.0` | Base delay between requests (+0–1s jitter) |
| `--timeout S` | `15` | Per-request timeout |
| `--user-agent S` | `website-teardown/0.1 (+repo)` | Identifies the tool honestly |
| `--ignore-robots` | off | **Only for sites you own.** |

Exit code is `1` only when *every* URL failed; partial success returns `0`.

## Compliance

This tool is built to sit on the safe side of the line:

- **Honest User-Agent.** No spoofed browser string. Sites can identify and block it.
- **robots.txt respected by default.** Disallowed paths are skipped and reported, not retried.
- **Rate limited.** Randomized 2–3s between requests; `--max-pages` caps the blast radius.
- **Metadata only.** No image downloads, no page copy storage, no screenshots
  redistributed. Visible text is used in memory to mine price ranges and then dropped.
- **No access-control circumvention.** Login walls, paywalls, captchas, and bot
  protection are out of scope — a blocked request is reported, never retried with
  a disguise.

You are responsible for complying with the target sites' terms of service and
applicable law in your jurisdiction. Analyze public pages, keep volumes small,
and keep source links in every report you share.

## Related

If you build Shopify stores for clients, the process around the build — intake
forms, the 40+ pre-launch checklist, handover documents — is packaged separately
as **[Shopify Agency Kit](https://gumroad.com/l/shopify-agency-kit)**.

This tool tells you what a competitor's site is made of. That kit is what you do
before and after.

## License

MIT — see [LICENSE](LICENSE). Provided "as is", without warranty of any kind.

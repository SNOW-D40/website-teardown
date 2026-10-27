---
name: website-teardown
description: "Analyze publicly accessible web pages and produce a metadata comparison report — platform, colour palette, fonts, price band, installed apps, content structure. Use when the user asks to compare competitor sites, audit a storefront, reverse-engineer a site's tech stack, or build a teardown / competitive-analysis report. Compliance-first: respects robots.txt by default, rate-limits every request, and never collects page copy, images, or screenshots."
allowed-tools: Bash
---

# website-teardown

Turns a list of public URLs into a comparison table of **measurable metadata** —
platform, palette, typography, price band, installed apps, page structure.

It deliberately does **not** extract page copy or download images. The report says
*what a site is made of*, not *what it says*. See `references/report-format.md`
for the output contract.

## When to use

- "Compare these 5 competitor stores" / "这几个站有什么不同"
- "What platform / theme / apps does this site use?"
- "What's their price positioning and visual style?"
- Pre-project research: what does the category look like before building a new store

## When not to use

- Anything behind a login, paywall, or captcha — **stop and tell the user**;
  bypassing access controls is out of scope and potentially illegal
- Copying a site's design, copy, or assets — this tool cannot and will not do that
- Bulk crawling (thousands of pages) — this is a small-batch analysis tool

## Run it

Replace `<skill-dir>` with the directory this SKILL.md lives in.

```bash
python3 <skill-dir>/scripts/analyze.py https://example.com --md report.md
```

Multiple sites, with both outputs:

```bash
python3 <skill-dir>/scripts/analyze.py \
  ollieandjames.com kettl.co bluebottlecoffee.com \
  --md report.md --json raw.json
```

Windows launcher:

```powershell
python "<skill-dir>\scripts\analyze.py" https://example.com --md report.md
```

### Useful flags

| Flag | Default | Purpose |
| --- | --- | --- |
| `--max-pages` | 20 | Hard cap per run |
| `--delay` | 2.0 | Base delay between requests (randomized +0–1s) |
| `--timeout` | 15 | Per-request timeout |
| `--user-agent` | `website-teardown/0.1 (+repo url)` | Identifies the tool honestly |
| `--ignore-robots` | off | **Don't.** Only for sites you own |

## What you get back

A markdown table plus (optionally) raw JSON:

| Site | Platform | Colors | Fonts | Price band | Apps |
| --- | --- | --- | --- | --- | --- |
| kettl.co | Shopify | #1A1A1A #F5F1EA | inter, playfair display | $18–$32 | Klaviyo, Judge.me |

## Rules to follow when presenting results

1. **Always keep the source URL visible** in the report — the reader must be able
   to go look at the original site. The report is a pointer, not a substitute.
2. **Never offer to clone, copy, or recreate** the analyzed design. If the user
   asks for that, refuse and explain the distinction between analysis and copying.
3. **Quote only what is necessary.** Short factual observations ("uses a
   two-column hero with a serif headline") are fine; reproducing marketing copy
   is not.
4. **Report failures honestly.** If a site blocks robots.txt or returns 403, say
   so — do not retry with a different user agent.
5. **State the date.** Metadata goes stale; every report carries the analysis
   timestamp.

## If a site fails

| Symptom | Meaning | Action |
| --- | --- | --- |
| `skipped: robots.txt disallows` | Site opts out | Report it, move on |
| `HTTP 403 / 429` | Bot protection / rate limit | Stop; do not retry or spoof |
| Timeout | Slow site or blocked region | Report it; suggest the user check manually |
| `parse_warning` | Malformed HTML | Results may be partial; still usable |

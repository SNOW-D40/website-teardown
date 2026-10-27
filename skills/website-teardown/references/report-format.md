# Report format contract

The report is a **pointer to sources**, not a substitute for them. Every row
must stay traceable to the page it came from.

## Required shape

```markdown
| Site | Platform | Colors | Fonts | Price band | Apps |
| --- | --- | --- | --- | --- | --- |
| https://kettl.co | Shopify | #1A1A1A #F5F1EA | inter, playfair | $18–$32 | Klaviyo, Yotpo |

> Metadata only. No page copy, images, or screenshots are collected or redistributed.
> Analyzed 2026-10-28T03:20:00+0800.
```

Rules:

1. **Full URL in the first column**, not a made-up short name — the reader must
   be able to click through.
2. **Failures stay in the table** with the reason (`robots.txt disallows`,
   `HTTP 403`). Silently dropping a row misrepresents the sample.
3. **The footer line is not optional.** It states what was *not* collected and
   when the snapshot was taken.
4. **No prose lifting.** Observations like "two-column hero with serif headline"
   are fine; copying headline text is not.

## JSON shape

```json
[
  {
    "url": "https://kettl.co",
    "ok": true,
    "analyzed_at": "2026-10-28T03:20:00+0800",
    "robots": "robots.txt allows",
    "title": "Kettl Tea",
    "platform": ["Shopify"],
    "colors": ["#1a1a1a", "#f5f1ea"],
    "fonts": ["inter", "playfair display"],
    "price_range": { "min": 18.0, "median": 24.0, "max": 32.0, "samples": 14 },
    "apps": ["Klaviyo", "Yotpo"],
    "h1_count": 1,
    "h2_count": 6,
    "img_count": 24
  }
]
```

## When presenting to a user

Lead with the **comparison insight** ("all five sit on Shopify; three use a
serif headline; the price band splits into two clusters"), then the table.
The table is evidence, not the answer.

Never follow the table with "now let's rebuild their homepage".

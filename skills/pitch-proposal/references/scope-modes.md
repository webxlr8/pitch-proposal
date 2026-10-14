# Presets and scope

| Preset | When | Pages |
|---|---|---|
| `build` | New website or platform, from a brief, profile or reference site | cover-concept, understanding, features-pair, features-shop-give, feature-grid, homepage-concept, sitemap, scope-modules, delivery, why-us |
| `refresh` | The client's existing site: clone it, fix the layout, make it look better | cover-screenshot, site-structure, site-review, scope-steps |
| `plan` | Company profile → page-by-page website plan | cover-concept, understanding, sitemap, page-plan, homepage-concept, feature-grid, delivery, why-us |
| `--pages a,b,c` | Anything else | any templates in any order (duplicate a template by listing it twice) |

## Strict scope
When the user limits the scope ("just mention X, nothing else"):
- Use only the pages that describe X (usually `refresh`).
- The scope page lists only X. No SEO, hosting, maintenance, add-ons, timelines or prices.
- Remove "why us" proof unless asked.

## Reference site ("make something like <url>")
- Crawl it, list every function, then write them as functions of the CLIENT'S future site.
- `proposal.json → "ban": ["<reference name>", "<reference domain>", "<founder/person names>", ...]` so the build fails if any slip in.
- Visuals: concept screens + stock photos, never the reference site's screenshots.

## Profile / PDF brief (new site for a known company)
- Read the whole document. Group their services into 4–8 service pages.
- Recommend the minimum page count and explain it (main pages + service pages, × languages).
- Concept screens use the client's real colours (`--c-*` variables) and logo.

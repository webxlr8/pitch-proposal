---
name: pitch-proposal
description: Create a branded, A4 website proposal PDF that a client can understand at a glance. Works from a client brief or company profile (PDF), a client's existing website to fix or clone, or a reference website ("build us something like this"). Reads the sender's branding and services from their own website, maps the target site's pages and functions, writes scope, sitemap, modules, a homepage concept with mockups, delivery phases and "why us", fills images from free stock libraries, and checks the PDF before it is sent. No prices unless asked. Use when the user asks to create, write or design a website proposal, scope document, website plan, redesign or clone proposal, or "a proposal for a site like <url>".
---

# pitch-proposal

- **This skill** is generic: page templates, analysis scripts, checks.
- **The sender** comes from a company profile: `./pitch-profile/`, `$PITCH_PROFILE` or `--profile` (same format as the pitch-audit skill). Create one per company with `scripts/profile_from_site.py <url> --out profiles/<name>`.
- **Scripts** live in `scripts/` under this skill folder. Run them from the folder where clients are kept.
- **Output** goes to `clients/<slug>/`: `proposal.html` (edit here), `<name>.pdf`, `previews/`, `images/`, `notes.md`.
- **Page types and image slots:** `references/page-types.md`. **Writing:** `references/copy-voice.md`. **Presets and strict scope:** `references/scope-modes.md`. **Images:** `references/images.md`.

## Rules
1. **One sender brand.** Logo, colours, fonts, contact and proof come from the profile. If the user names a different sender ("use our partner company's branding"), build or pick that company's profile first.
2. **Client brand:** use it when known (their logo and colours in concept screens). When it is not known, keep `[Client Brand Name]` and the neutral "YOUR BRAND" concept, and say so.
3. **Reference sites are research only.** For "build something like <url>", describe its functions in general words. Never put its name, logo, screenshots, people or wording in the proposal. Add its names to `proposal.json → ban`.
4. **No prices** unless the user asks. `build.py` fails on amounts and pricing words in the copy. Timelines only if the user gave them or the profile states them; otherwise "confirmed after discovery".
5. **Do only what was asked.** If the brief is narrow ("clone it, fix the layout, make it look better"), use the `refresh` preset and write only that scope. No extra services, SEO, hosting or add-ons.
6. **Every claim is sourced.** Sender numbers and client names only from `proof.yaml`. Client facts only from their profile, site or the user. Problems only if you saw them in a screenshot. Unsure → put it in `notes.md` and tell the user.
7. **Concept screens are labelled as concepts.** Stock photos never pose as the client's own staff, premises or products.
8. **Ship only what passed `build.py`,** after you have looked at every preview page yourself.

## Workflow
1. **Sender profile.** Find it (`pitch-profile/`, `profiles/<name>/`). Missing → `python3 scripts/profile_from_site.py <sender-url> --out profiles/<name> [--theme dark]`, then review `report.md`, logos in `brand/`, and fill `proof.yaml` with approved claims only.
2. **Understand the input** (write findings to `clients/<slug>/notes.md`):
   - Client PDF/brief: read every page. Note services, audience, regions, tone, brand colours.
   - Website (client's or reference): `python3 scripts/crawl_site.py <url> --out clients/<slug>/site` → read `site.md`, open the example pages it lists to confirm each function. Screenshots: `python3 scripts/screenshots.py shoot <url> clients/<slug>/site/home.png` (and `--mobile`).
3. **Pick a preset** (`references/scope-modes.md`): `build` (new platform), `refresh` (clone + fix + improve), `plan` (page-by-page site plan from a profile), or a custom `--pages` list.
4. **Scaffold:** `python3 scripts/new_proposal.py <slug> --client "<Client>" --preset <preset> [--profile <dir>] [--theme dark|light] [--client-domain <domain>]`.
5. **Images** (`references/images.md`): real screenshot crops for problems (`screenshots.py crop`); free stock for concepts (`stock_photos.py get <unsplash-url> --out clients/<slug>/images --name <slot>`). Replace every placeholder.
6. **Write the copy** in `proposal.html`, page by page, following `references/copy-voice.md`. Delete template sample text, unused pages and unused widgets. Fill `proposal.json` (`ban`, `allow`, `output`).
7. **Build:** `python3 scripts/build.py clients/<slug>`. Fix every ERROR. Then open every `previews/page-XX.png`: clipped or overlapping text, a word alone on a line, empty bottom areas (warned), photos that fight the text. Rebuild until clean.
8. **Deliver:** send the PDF (SendUserFile). In a few lines tell the user: pages and what each covers, the scope, every assumption and placeholder to check (from `notes.md`), and image credits.

## Never
- Invent metrics, client names, testimonials, prices, guarantees or dates.
- Show a reference site's branding, or present stock photos as the client's own.
- Log in, submit forms, bypass bot protection or crawl aggressively.
- Publish, email or upload the proposal anywhere without the user's go-ahead.

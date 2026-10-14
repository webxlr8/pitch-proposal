# Page types

Each file in `templates/pages/` is one A4 page (`<section class="page">`). `new_proposal.py` joins them
and fills `{{TOKENS}}` from the profile. Edit copy directly in `proposal.html` afterwards.

| Page | Use it for | Image slots |
|---|---|---|
| `cover-concept` | New build. Photo cover + desktop and phone concept of the client's new site + 5 module tags | hero, img-1, img-2, img-3 |
| `cover-screenshot` | Refresh / fix. The client's current site in a browser frame | current-site |
| `understanding` | Who the site serves (4 audiences), how people engage (5 steps), 3 goals | img-4 … img-7 |
| `features-pair` | Two functions, each with a concept screen (catalogue + schedule, booking form) | img-8, img-9, img-1 … img-3 |
| `features-shop-give` | Online shop and donations with concept screens | img-10, img-11, img-12, img-1 … img-3, img-8 |
| `feature-grid` | Six more functions as photo cards + "every function at a glance" pills | img-13 … img-18 |
| `homepage-concept` | Full concept homepage with 7 numbered notes | hero, img-1 … img-3, img-19, img-20, img-12 |
| `sitemap` | Proposed menu tree (`--n` = number of items) + six "built better" tiles | — |
| `page-plan` | Goal + numbered sections for each page (one row per page, ~7 per A4) | — |
| `site-structure` | How the CURRENT site is built: menu tree, homepage sections, 3 facts | — |
| `site-review` | Six problems on the current site, each with a real screenshot crop | shot-1 … shot-6 |
| `scope-steps` | Strict scope in 3 numbered blocks + closing contact band | — |
| `scope-modules` | Six modules + admin dashboard concept | — |
| `delivery` | Six phases with "you receive", what we need / what you get | — |
| `why-us` | Proof stats, how we work, clients (all from proof.yaml), next steps, contact band | closing |

## Building blocks (in `templates/base.css` and `templates/ui.css`)
- Layout: `.cols-2/3/4/5`, `.mt-4/6/8`, `.card`, `.tile`, `.stat`, `.pcard` (photo card), `.ev` (evidence card), `.steps` (set `--n`), `.tree` (set `--n`), `.phases`, `.scope/.sc`, `.feat` / `.feat.rev`, `.stage`, `.hp` + `.ann`, `.end` (closing band).
- Text: `.eyebrow`, `h2` with `<em>` highlight, `.lead`, `.k` (small caps label), `.dot` list, `.pill`, `.note`.
- Concept UI (`.ui`): `.nav`, `.hero` (+ `.next` card), `.band`, `.sec` + `.cards`, `.testi`, `.cta`, `.foot`, `.panel` with `.filters/.trow` (schedule), `.tabs/.fld/.two/.slots` (booking form), `.prod/.minis` (product), `.seg/.line/.total` (donation), `.dash` (admin). Phone: `.phone > .scr.ui` with `.pn/.pvh/.ls`.
- Client palette for concept screens: override `--c-bg --c-primary --c-deep --c-accent --c-head` in the `<style>` block of `proposal.html`.

## Fitting content to A4
- `build.py` fails if a page overflows (page count ≠ number of sections). Shorten copy or split the page.
- It warns when more than 22% of a page body is empty at the bottom. Enlarge images (`height`), padding, or add one useful block. Do not pad with filler text.

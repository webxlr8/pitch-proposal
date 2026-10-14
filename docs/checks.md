# Checks in build.py

| Level | Check | Fix |
|---|---|---|
| Error | PDF page count ≠ number of `<section class="page">` | Content overflowed: shorten copy or split the page |
| Error | `{{TOKEN}}` left in the HTML | Fill it or remove the block |
| Error | Missing image file | Add the image or fix the path |
| Error | Placeholder image still used | Replace it (stock photo or screenshot crop) |
| Error | Amounts or pricing words in the copy while `no_prices` is true | Remove, or add a phrase to `proposal.json → allow`. Concept screens are skipped |
| Error | A word from `proposal.json → ban` appears in the PDF | Remove it (reference-site names, other brands) |
| Warning | Template sample copy left in | Rewrite it for the client |
| Warning | `[Bracket]` placeholders in the copy | Fine when intentional, e.g. `[Client Brand Name]` |
| Warning | More than 22% of a page body empty at the bottom | Enlarge blocks or add one useful element |

After a clean build, look at every `previews/page-XX.png`: clipped text, overlaps, a single word on a line, photos that fight the text.

# Images

Order of preference:
1. **Client's own** logo and photos (from their site or PDF) when the proposal is for them.
2. **Real screenshots** of the current site as evidence (`screenshots.py shoot` then `crop`). Crop, never edit.
3. **Free stock photos** for concepts and moods: Unsplash or Pexels (`stock_photos.py`). Both licences allow free commercial use.
4. Nothing else. No AI-generated "photos" of the client's business, staff or premises.

## Stock photos
- With `UNSPLASH_ACCESS_KEY` or `PEXELS_API_KEY`: `stock_photos.py search "<query>" --out clients/<slug>/images/_candidates`, look at `sheet.png`, then `get`.
- Without a key: open `https://unsplash.com/s/photos/<query>?license=free` (browser or web search), pick photos, then `stock_photos.py get https://unsplash.com/photos/<id> --out clients/<slug>/images --name <slot>`.
- Unsplash+ photos are paid and refused.
- Credits are saved in `images/credits.json`. Add "Photography: Unsplash" (or Pexels) to the closing note.

## Choosing
- Match the client's world: people like their customers, their region, their activity.
- One mood across the document; avoid mixing studio shots with phone snaps.
- Text over photos: the templates add a dark gradient. Check contrast in the previews.
- Large, calm images for covers and closing bands; detailed ones for small cards.

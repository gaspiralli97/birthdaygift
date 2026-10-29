# Reference

Working material, kept so the design decisions behind the service can be traced.
None of it is imported by the application.

| File | What it is |
|---|---|
| `original-card.html` | The hand-written card this whole service grew out of — one page, for one person. Its night-sky layout, candle grid, WAV melody and starfield are what the card page reproduces. |
| `colorways.html` | The same card in the three colourways, used to pick the palette. Colours are sampled from the Baginy storefront: near-black, burgundy, champagne. |
| `prototype.html` | A throwaway prototype of the whole flow — form, live preview, four languages, a template-based letter engine. |

## Why the prototype's letter engine is not in the application

It was a genuine attempt to make a template read like a person wrote it: beats
instead of slots, the sender's own words placed first so no colon introduces
them, four paragraphs of deliberately uneven length, and facts about the age
computed rather than recalled.

It got close enough to prove the point and not close enough to use. A template
can place a detail next to a sentence; it cannot read the detail and build a
joke on top of it, which is exactly what made the original card land. The
application therefore writes the letter with a model, and keeps the prototype
here as the record of what was tried.

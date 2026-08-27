---
name: j33-blog-promo-kit
description: Use when the user has a blog article or draft and needs promotional assets for it — generating Instagram, X, and LinkedIn images plus the J33.AI website banner and thumbnail, and/or writing the social posts to go with them. Trigger on "promo images for this post", "social kit", "banner and thumbnail", "post this article", "images for the blog", "make the LinkedIn post for this", or any mention of publishing/promoting a J33.AI article. Also use when asked to restyle or regenerate an existing article's images.
---

# J33.AI Blog Promo Kit

Turn one blog article into five images at exact platform sizes plus the post copy for
each channel.

Two rules keep the output from looking machine-made:

1. Every glyph is set by a text engine (Chromium or Pillow), never by an image model.
2. The artwork is the article's own content: a diagram of its architecture, its code, or
   a real photograph.

## Deliverables

| Channel           | File              | Pixels    | Ratio | Notes                                |
| ----------------- | ----------------- | --------- | ----- | ------------------------------------ |
| Instagram         | `instagram.png`   | 1080×1350 | 4:5   | Must survive a 1:1 centre crop in-grid |
| X                 | `x.png`           | 1600×900  | 16:9  | Also the `twitter:image`             |
| LinkedIn          | `linkedin.png`    | 1200×1200 | 1:1   | Native image post                    |
| Website banner    | `<slug>.png`      | 1600×873  | ~1.83 | Displayed at 7:3, centre-cropped     |
| Website thumbnail | `<slug>-card.png` | 1659×948  | ~7:4  | Article card in listings             |

The website filenames match what j33.ai expects (`heroImage: images/<slug>.webp`,
`cardImage: images/<slug>-card.webp`). `kit.py --webp` writes the `.webp` files.

The banner is displayed at 7:3, so about 94px is cropped from the top and bottom of the
1600×873 file. Keep everything that matters inside the middle band. `verify.py` checks it.

## Workflow

### 1. Read the article

The whole thing. You need:

- The one idea a reader takes away. This is the headline.
- A concrete artefact: an architecture, a sequence, a snippet of real code, a number. This
  is the artwork.
- A specific result, constraint or story for the hook in the social copy.
- The slug, from the filename or the article metadata.

If the article is a `.docx`, extract it first (`extract_docx_text.py`, `dump_docx.py` in
this repo).

### 2. Choose a surface

| Surface | Use when | Looks like |
| ------- | -------- | ---------- |
| `paper` | The article explains a mechanism you can draw | Cream `#F6F0E2`, navy display type, outlined diagram, cyan values |
| `navy`  | Security, infrastructure, architecture, anything with a threat model | `#0A0D33` → `#01102D`, white type, cyan accent |
| `photo` | You have a real photograph and the topic is physical | Photo under a navy scrim, white and cyan type |

Prefer `paper` when there is a mechanism to draw. Use `navy` when there is not. Use
`photo` only with a real photograph; a generated stock plate is the look this skill
exists to avoid.

### 3. Write the spec

One JSON file drives all five renders. `references/layouts.md` has every field and the
art modes.

```json
{
  "slug": "why-chatgpt-should-never-touch-your-database",
  "eyebrow": "PART 1 OF 3",
  "headline": "ChatGPT Should Never Touch Your Database",
  "accent": "Never",
  "subhead": "A prompt is a suggestion, not a security control",
  "kicker": "MCP · ENTRA ID · POSTGRES",
  "surface": "navy",
  "display": "inter",
  "art": "diagram",
  "art_svg": "<svg …>"
}
```

Headline: under 8 words, and a claim rather than a topic. "ChatGPT Should Never Touch
Your Database" works; "Understanding Enterprise AI Integration" does not.

`accent` is the word or phrase that turns cyan: the word carrying the argument, one per
image.

### 4. Render

```bash
python scripts/kit.py --spec spec.json --out out/ --webp
```

Uses Chromium when Playwright is installed, Pillow otherwise. `--engine pil` forces
Pillow. `--webp` also writes `.webp` for the two website files.

### 5. Verify

```bash
python scripts/verify.py out/
```

Checks the crop safe zones, contrast (3:1 for display type, 4.5:1 for smaller text),
exact dimensions and webp weight, and writes `_crop-<name>.png` previews of the banner's
7:3 display and the Instagram grid. Fix what it reports and re-render.

Then look at the PNGs with the Read tool. The script cannot see a bad line break or a
diagram colliding with the logo.

### 6. Write the copy

Follow `references/social-copy.md`: per-platform limits, structure, and the tells of
machine writing. Write `copy.md` into the output folder in the J33.AI "we" voice the
articles use.

## Anti-slop rules

Never in an image:

- Glowing brains, neural-network orbs, circuit boards, humanoid robots
- Holographic UI, lens flares, particle swarms, binary rain, hexagon grids
- Handshakes, up-and-to-the-right arrows, "digital transformation" swooshes
- Text from an image model, in any quantity
- More than one accent colour, or any colour outside `references/brand.md`
- Faces or logos you do not have rights to

Always:

- A diagram of the actual system, with the article's own labels
- Real code from the article, in a monospace face
- A real photograph of something specific, if you have one
- Empty space; the strongest j33.ai cards are close to half empty
- The J33.AI lockup, placed as `references/brand.md` says

Typography: two sizes doing the work. The headline must survive a phone-sized thumbnail,
roughly 90–130px on a 1600px canvas. If it has to shrink below ~70px to fit, cut words.

## Files

- `references/brand.md`: J33.AI tokens from the live site CSS, logo rules
- `references/image-specs.md`: canvases, safe zones, crop maths, export settings
- `references/layouts.md`: spec schema, art modes, worked examples
- `references/social-copy.md`: per-platform limits, hashtags, prose checklist
- `scripts/kit.py`: spec in, five images out
- `scripts/render.py`: Chromium renderer
- `scripts/compose.py`: Pillow renderer; `scripts/svgpil.py` rasterises `art: diagram`
  for it
- `scripts/verify.py`: dimension, crop, contrast and weight checks
- `tests/test_kit.py`: `python tests/test_kit.py`, Pillow and stdlib only. Run it after
  changing anything under `scripts/`
- `assets/templates/poster.html`: the layout both renderers follow
- `assets/fonts/`: Inter (variable) and Anton, bundled
- `assets/examples/`: `navy-diagram.json` and `paper-code.json`, both rendered and
  checked. Copy one rather than starting blank

## Without Chromium

Fonts are bundled and nothing touches the network. Without Chromium (ChatGPT's sandbox,
most CI) `kit.py` uses Pillow. Two differences: the navy gradient is vertical rather than
angled, and `art: diagram` renders the SVG subset listed in `references/layouts.md`.
Anything outside it is named in the warnings; author to the subset, or render that canvas
through Chromium.

---
name: j33-blog-promo-kit
description: Use when the user has a blog article or draft and needs promotional assets for it — generating Instagram, X, and LinkedIn images plus the J33.AI website banner and thumbnail, and/or writing the social posts to go with them. Trigger on "promo images for this post", "social kit", "banner and thumbnail", "post this article", "images for the blog", "make the LinkedIn post for this", or any mention of publishing/promoting a J33.AI article. Also use when asked to restyle or regenerate an existing article's images.
---

# J33.AI Blog Promo Kit

Turn one blog article into a complete, on-brand publishing kit: five images at exact
platform dimensions, plus the post copy for each channel.

The whole point of this skill is that the output must not look AI-generated. Two rules
carry most of that weight:

1. **Every visible glyph is rendered by a real text engine** — a browser or Pillow —
   never by an image model. Image models produce warped letterforms and invented words,
   which is the single loudest "this was AI'd" signal.
2. **The artwork comes from the article's actual content** — a real diagram of the real
   architecture, real code from the real repo, or a real photograph. Not a glowing brain,
   not a circuit board, not a humanoid robot.

## Deliverables

Every run produces exactly these five images plus `copy.md`:

| Channel           | File                    | Pixels     | Ratio | Notes                                    |
| ----------------- | ----------------------- | ---------- | ----- | ---------------------------------------- |
| Instagram         | `instagram.png`         | 1080×1350  | 4:5   | Must survive a 1:1 centre crop in-grid   |
| X                 | `x.png`                 | 1600×900   | 16:9  | Also serves as the `twitter:image`       |
| LinkedIn          | `linkedin.png`          | 1200×1200  | 1:1   | Native image post                        |
| Website banner    | `<slug>.png`            | 1600×873   | ~1.83 | **Rendered at 7:3 — centre-cropped**     |
| Website thumbnail | `<slug>-card.png`       | 1659×948   | ~7:4  | Article card in listings                 |

The two website filenames match what j33.ai already expects: `heroImage: images/<slug>.webp`
and `cardImage: images/<slug>-card.webp`. Convert to `.webp` at the end (the script does
this) so they drop straight onto the CDN.

The banner crop is the trap worth remembering. The file is 1600×873 but the site displays
it at 7:3, so roughly 94px is shaved off the top and 94px off the bottom. Anything that
matters has to live inside the middle band. `verify.py` checks this for you.

## Workflow

### 1. Read the article properly

Read the whole thing, not the first two paragraphs. You are looking for four things:

- **The one idea.** What does a reader actually take away? This becomes the headline.
- **A concrete artefact.** An architecture, a sequence, a comparison table, a snippet of
  real code, a number. This becomes the artwork and it is what stops the image looking generic.
- **The proof.** A specific result, constraint, or war story you can use as the hook in
  the social copy.
- **The slug**, from the filename or the existing article metadata.

If the article is a `.docx`, extract it first — there are already helper scripts in this
repo (`extract_docx_text.py`, `dump_docx.py`).

### 2. Choose a surface

Three, matching what j33.ai already ships. Pick on content, not on mood.

| Surface | Use when | Looks like |
| ------- | -------- | ---------- |
| `paper` | The article explains a mechanism and you can draw it | Warm cream `#F6F0E2`, heavy navy display type, hand-drawn-feel diagram, blue data values |
| `navy`  | Security, infrastructure, architecture, anything with a threat model | `#0A0D33` → `#01102D`, white type with cyan accent words |
| `photo` | You have a genuinely good photograph and the topic is human or physical | Photo under a navy scrim, white + cyan headline |

Default to `paper` when the article has a mechanism worth drawing — it is the most
distinctive of the three and the least like everyone else's tech blog. Use `navy` when
there is nothing to draw. Only use `photo` if you actually have a real photograph; a
generated "professional office" stock plate is exactly the slop we are avoiding.

### 3. Write the spec

One JSON file drives all five renders. See `references/layouts.md` for every field and
the art modes.

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

Headline discipline: **under 8 words**, and it must say something. "ChatGPT Should Never
Touch Your Database" works. "Understanding Enterprise AI Integration" says nothing and
will read as filler. Prefer the claim over the topic.

`accent` is the word or phrase that turns cyan. Choose the word carrying the argument —
`Never`, `SQL Injection`, `By Hand`. One accent per image; two is noise.

### 4. Render

```bash
python scripts/kit.py --spec spec.json --out out/ --slug <slug>
```

It renders through Chromium when Playwright is available and falls back to Pillow when it
isn't, so the same spec works in Claude Code and in ChatGPT's sandbox. Add `--engine pil`
to force the fallback, `--webp` to also emit `.webp` for the two website files.

### 5. Verify before showing the user

```bash
python scripts/verify.py out/
```

This checks the banner's crop safe-zone, flags text contrast below 4.5:1, confirms exact
pixel dimensions, and renders a 1:1 centre-crop preview of the Instagram image so you can
see what the profile grid will show. Fix anything it reports, then re-render.

Then actually look at the PNGs with the Read tool. The script cannot tell you that a
headline broke across a line badly or that the diagram collides with the logo. You can.

### 6. Write the copy

Read `references/social-copy.md` and follow it — it has the per-platform limits, the
structure that works for technical content, and the list of tells that make writing read
as machine-generated. Write `copy.md` into the output folder.

Voice is **J33.AI "we"**, matching the articles' own prose ("at J33.AI we built the
integration the other way around"). Not "I", not a faceless brand voice.

## Anti-slop rules

These are not stylistic preferences. Each one corresponds to something that makes a
reader's eye flag an image as machine-made.

**Never put in an image**

- Glowing blue brains, neural-network orbs, circuit-board patterns, humanoid robots
- Floating holographic UI, lens flares, particle swarms, binary rain, hexagon grids
- Handshakes, arrows going up-and-to-the-right, generic "digital transformation" swooshes
- Text generated by an image model, in any quantity, for any reason
- More than one accent colour, or any colour outside `references/brand.md`
- Faces or logos you do not have the rights to

**Do put in an image**

- A diagram of the actual system the article describes, drawn to the article's own labels
- Real code, copied from the article, in a real monospace face
- A real photograph, if you have one, of something physically specific
- Generous empty space — the two strongest j33.ai cards are close to half empty
- The J33.AI lockup, always, in the position `references/brand.md` specifies

**Typography**

Two type sizes doing all the work beats five doing a little each. Set the headline large
enough that it survives a phone-sized thumbnail — for a 1600px-wide canvas that means
roughly 90–130px. If the headline needs to shrink below ~70px to fit, the headline is
too long; cut words instead of type size.

## Reference files

Read these as you need them rather than up front:

- `references/brand.md` — the exact J33.AI tokens, pulled from the live site CSS, plus the logo lockup rules
- `references/image-specs.md` — every canvas, safe zone, crop maths, and export setting
- `references/layouts.md` — the full spec schema, all art modes, and worked examples
- `references/social-copy.md` — per-platform limits, hashtags, and the anti-slop checklist for prose

## Scripts

- `scripts/kit.py` — the orchestrator; spec in, five images out
- `scripts/render.py` — Chromium renderer, exact pixel output
- `scripts/compose.py` — Pillow renderer, no browser needed
- `scripts/verify.py` — dimension, crop, and contrast checks
- `assets/templates/poster.html` — the layout engine both renderers share conceptually
- `assets/fonts/` — Inter (variable) and Anton, bundled so nothing needs the network
- `assets/examples/` — two working specs, both rendered and checked:
  `navy-diagram.json` (navy surface, SVG architecture diagram) and
  `paper-code.json` (cream paper, Anton display, real code, art dropped on the
  portrait canvases via `overrides`). Copy one and edit it rather than starting blank.

## Running outside Claude Code

The skill is self-contained: fonts are bundled and nothing fetches from the network.
In an environment without Chromium — ChatGPT's sandbox, most CI — `kit.py` detects
that and uses the Pillow renderer automatically. Two things behave differently there
and the script tells you when they bite:

- the navy gradient is vertical rather than angled, which is not visually significant
- `art: diagram` needs `cairosvg`; without it the artwork is **dropped and reported**,
  not silently replaced. Either `pip install cairosvg` or switch that canvas to
  `art: code` / `art: none`.

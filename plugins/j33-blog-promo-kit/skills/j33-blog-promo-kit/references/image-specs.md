# Canvas specifications

Five canvases. The dimensions are fixed; two of them match files j33.ai already serves.
`scripts/profiles.py` is the source of truth for these numbers.

## The table

| Key         | Output            | Pixels    | Ratio  | Layout  | Safe inset (px)        |
| ----------- | ----------------- | --------- | ------ | ------- | ---------------------- |
| `banner`    | `<slug>.png`      | 1600×873  | 1.833  | `wide`  | 96 sides, **110 t/b**  |
| `card`      | `<slug>-card.png` | 1659×948  | 1.750  | `split` | 100 all round          |
| `instagram` | `instagram.png`   | 1080×1350 | 0.800  | `stack` | 72 sides, **207 t/b**  |
| `x`         | `x.png`           | 1600×900  | 1.778  | `split` | 96 all round           |
| `linkedin`  | `linkedin.png`    | 1200×1200 | 1.000  | `stack` | 88 all round           |

The two bold insets are crop safe zones, explained below.

## The banner crop

j33.ai displays the hero at 7:3 but the file is 1600×873 (1.833:1). With
`object-fit: cover`, the browser fills the width and crops the overflow height:

```
displayed height at 7:3   = 1600 × 3/7   = 685.7px
file height               = 873px
total cropped             = 873 − 685.7   = 187.3px
cropped per edge (centre) = 93.7px
```

The visible band is y ∈ [94, 779]. The 110px inset leaves ~16px of slack. Put nothing
load-bearing outside that band: no headline, logo or diagram label. Above and below is
background only.

`verify.py` writes `_crop-banner.png`, the cropped result, so you can look rather than
assume.

## The Instagram grid crop

A 4:5 post shows in full in the feed, but the profile grid shows a 1:1 centre crop. From
1080×1350 that removes 135px from the top and 135px from the bottom:

```
visible in grid = y ∈ [135, 1215]
```

The 207px inset is more generous than the 135px minimum because a headline sitting on the
crop line looks like a mistake even when it fits. Keep the headline and logo inside the
inset; background can run to the edge.

## Layout modes

`wide` (banner): text left, artwork right, with the middle breathing. Vertically centred
within the crop-safe band, not within the file.

`split` (card, X): text left, artwork right, one gutter between. The layout both shipped
j33.ai cards use.

`stack` (Instagram, LinkedIn): logo top, headline, artwork below, kicker at the base.
Artwork is optional here; on a 1:1 or 4:5 canvas a strong headline with air often beats a
cramped diagram.

Column shares and gutters are `text_frac()` and `type_scale()` in `profiles.py`.

When artwork would have to shrink past legibility, drop it. An empty half is a design
choice; an illegible diagram is a defect.

## The photo scrim

When `surface: photo`, the photograph alone will not hold white text. In order:

1. The photograph, `object-fit: cover`, centred on its subject.
2. A scrim in `#02080F`, whose direction depends on the layout.
3. A flat `#0A0D33` overlay at 18% across the whole frame, to pull the photo toward brand.

The scrim has to be opaque wherever type lands, and type lands in different places per
layout:

| Layout | Canvases | Scrim |
| ------ | -------- | ----- |
| `wide`, `split` | banner, card, X | Horizontal: 94% at the left edge → 80% at 38% across → clear at 68%. The text keeps to the left half; the photograph gets the right half. |
| `stack` | Instagram, LinkedIn | Vertical: 90% at the top → 62% at the bottom. The headline runs the full width here, so a horizontal clear would drop the end of every line onto bare photo. |

`verify.py` measures contrast under the glyphs rather than trusting the recipe: 3:1 for
display type, 4.5:1 for smaller text. On a photo surface it downgrades the crop-strip
check to a note, because edge energy cannot tell a photograph's texture from type.

## Export settings

- PNG, 8-bit RGB, no alpha. Alpha in an OG image renders black on some clients.
- sRGB. Convert a Display P3 photograph first, or the cyan shifts.
- Website files also as `.webp`, quality 82. The shipped j33.ai cards weigh about 160KB
  at 1659×948 and the banner about 310KB at 1600×873; the budgets `verify.py` enforces
  (`webp_kb` in `profiles.CANVASES`) are 200KB and 340KB.
- Never upscale a source photograph past 1.0×. If it is too small, use a different surface.

## The manifest

`kit.py` writes `_kit.json` beside the images: for each file, its canvas, surface, layout,
insets, and the box the glyphs occupy. `verify.py` reads it. Without it the verifier
guesses the canvas from the filename and the surface from the image, and says so.

## Rendering fidelity

Both renderers work at 2× and downsample with LANCZOS (Chromium via
`deviceScaleFactor: 2`). Rendering 1:1 makes the type look thin and slightly ragged.

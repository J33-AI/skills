# Canvas specifications

Five canvases. The dimensions are fixed; do not "round" them, because two of them are
matched to files j33.ai already serves.

## The table

| Key         | Output            | Pixels    | Ratio  | Layout  | Safe inset (px)        |
| ----------- | ----------------- | --------- | ------ | ------- | ---------------------- |
| `banner`    | `<slug>.png`      | 1600×873  | 1.833  | `wide`  | 96 sides, **110 t/b**  |
| `card`      | `<slug>-card.png` | 1659×948  | 1.750  | `split` | 100 all round          |
| `instagram` | `instagram.png`   | 1080×1350 | 0.800  | `stack` | 72 sides, **207 t/b**  |
| `x`         | `x.png`           | 1600×900  | 1.778  | `split` | 96 all round           |
| `linkedin`  | `linkedin.png`    | 1200×1200 | 1.000  | `stack` | 88 all round           |

The two bold insets are not padding preferences. They are crop survival zones, explained
below.

## The banner crop — the one that catches people

j33.ai displays the hero at **7:3** but the file is **1600×873** (1.833:1). With
`object-fit: cover`, the browser scales to fill the width and crops the overflow height:

```
displayed height at 7:3   = 1600 × 3/7   = 685.7px
file height               = 873px
total cropped             = 873 − 685.7   = 187.3px
cropped per edge (centre) = 93.7px
```

So the visible band is **y ∈ [94, 779]**. Design to a 110px inset and you have ~16px of
slack. Put nothing load-bearing — no headline, no logo, no diagram label — outside that
band. The area above and below should be background continuation only.

`verify.py --crop` renders the cropped result so you can confirm rather than assume.

## The Instagram grid crop

A 4:5 post is displayed in full in the feed, but the **profile grid shows a 1:1 centre
crop**. From 1080×1350 that removes 135px from the top and 135px from the bottom.

```
visible in grid = y ∈ [135, 1215]
```

The 207px safe inset is deliberately more generous than the 135px minimum, because a
headline sitting exactly on the crop line looks like a mistake even when it technically
fits. Keep the headline and logo inside the inset; decorative background can run to the edge.

## Layout modes

**`wide`** — banner. Text occupies the left ~46%, artwork the right ~48%, with the middle
breathing. Vertically centred within the crop-safe band, not within the file.

**`split`** — card and X. Text left ~52%, artwork right ~44%, one gutter of ~5% between.
This is the layout both shipped j33.ai cards use.

**`stack`** — Instagram and LinkedIn. Logo top, headline in the upper-middle, artwork
below, kicker at the base. Artwork is optional here; on a 1:1 or 4:5 canvas a strong
headline with a lot of air often outperforms a cramped diagram.

When artwork would need to shrink past legibility to fit, drop it. An empty right half is
a design choice; an illegible diagram is a defect.

## The photo scrim

When `surface: photo`, the photograph alone will not hold white text. Apply, in order:

1. The photograph, `object-fit: cover`, centred on its subject.
2. A horizontal gradient, `#02080F` at 92% on the text side → transparent at 62% across.
3. A flat `#0A0D33` overlay at 18% across the whole frame, to pull the photo toward brand.

Check the result with `verify.py`, which measures actual contrast under the headline
rather than trusting the recipe.

## Export settings

- PNG, 8-bit RGB, no alpha for the final files. Alpha in an OG image renders black on
  some clients.
- sRGB. If the source photograph is Display P3, convert it — otherwise the cyan shifts.
- Website files additionally to `.webp`, quality 82. The shipped j33.ai cards land around
  160KB at 1659×948 and the banner around 310KB at 1600×873; treat those as the budget.
- Never upscale a source photograph past 1.0×. If it is too small, use a different surface.

## Rendering fidelity

Chromium path renders at `deviceScaleFactor: 2` onto a half-size viewport, then downsamples
— this is what gives clean type edges. The Pillow path supersamples 2× and resizes with
`LANCZOS` for the same reason. Do not render 1:1; the type will look thin and slightly
ragged, which reads as cheap.

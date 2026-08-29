# Spec schema and art modes

One JSON file drives all five renders. Write it, render, look, adjust.

## Full schema

```jsonc
{
  // ── identity ────────────────────────────────────────────────────────────
  "slug":     "why-chatgpt-should-never-touch-your-database",  // required

  // ── text ────────────────────────────────────────────────────────────────
  "eyebrow":  "PART 1 OF 3",                     // optional, small caps above headline
  "headline": "ChatGPT Should Never Touch Your Database",   // required, <8 words
  "accent":   "Never",                           // optional substring of headline → cyan
  "subhead":  "A prompt is a suggestion, not a security control",  // optional, one line
  "kicker":   "MCP · ENTRA ID · POSTGRES",       // optional, dotted meta line

  // ── look ────────────────────────────────────────────────────────────────
  "surface":  "dark",        // paper | dark | photo (default dark)
  "theme":    "crimson",     // see references/brand.md (default signal)
  "accent_hex": "#7C2A92",   // optional one-off, overrides the theme's accent
  "display":  "inter",       // inter | anton   (anton is caps-only)
  "photo":    "path/to.jpg", // required when surface = photo

  // ── artwork ─────────────────────────────────────────────────────────────
  "art":      "diagram",     // none | diagram | code | photo
  "art_svg":  "<svg viewBox='0 0 600 420'>…</svg>",   // when art = diagram
  "art_img":  "path/to.jpg", // when art = photo (a picture *beside* the text,
                             //   as opposed to `photo` which goes behind it)
  "fit_viewbox": true,       // default; false keeps the viewBox you authored
  "art_code": {                                        // when art = code
    "lang":  "python",
    "lines": ["app.add_middleware(", "    CORSMiddleware,", "    allow_origins=[\"*\"],", ")"],
    "highlight": [2]        // 0-based line indices to tint cyan
  },

  // ── per-canvas overrides (optional) ─────────────────────────────────────
  "overrides": {
    "instagram": { "art": "none", "headline": "ChatGPT Should Never\nTouch Your Database" }
  }
}
```

Only `slug` and `headline` are required. `surface: navy` still works and means `dark`.

`overrides` exists because a headline that reads well across a 1600px banner often needs
a manual line break on a 1080px portrait canvas, and because artwork that works in
`split` is often better dropped in `stack`. Override rather than compromising the wide
canvases.

## Art modes

### `none`

Type and air. The right half (or lower half) stays empty except for the surface
treatment. Right for argumentative articles, an opinion piece, a postmortem, a "why you
shouldn't", where there is no honest diagram to draw. It is a first choice, not a
fallback.

### `diagram`

Real SVG describing the article's actual system.

- `viewBox` of `0 0 600 420` for `split`/`wide`, `0 0 600 480` for `stack`. The renderer
  scales it; author in those coordinates.
- Strokes: `#INK`, which the renderer swaps for `#0A0D33` on `paper` and `#FFFFFF` on
  `dark`/`photo`. Width `2.5`–`3`.
- Node fills: none, or the surface colour. Outlined boxes, not filled blocks.
- Numeric values, labels that carry the payload, and the single most important arrow:
  `#ACCENT`, which the renderer swaps for the theme's accent on the plate in use.
- Write the tokens, not hex. A drawing with hex in it only works on one theme, and the
  same SVG has to render on five canvases across both plates. An unrecognised colour
  draws nothing and is named in the warnings.
- Corner radius `10` on node rectangles.
- Labels in Inter 600 at `18`–`22` units. Monospace for anything that is literally code.
- Dashed strokes (`stroke-dasharray="6 6"`) for the "not yet computed" or "blocked" parts.

Copy the labels verbatim from the article. If the article says "Custom MCP server", the
box says "Custom MCP server", not "AI Gateway".

**What the renderers accept.** Chromium renders whatever SVG you write. The Pillow path
goes through `scripts/svgpil.py`, which implements this much:

| Supported | Notes |
| --------- | ----- |
| `svg`, `g`, `a`, `switch` | Containers; `transform` with translate/scale/rotate/matrix/skew |
| `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon` | `rx`/`ry` rounding on rects |
| `path` | `M L H V C S Q T A Z`, absolute and relative |
| `text`, `tspan` | `text-anchor`, `font-size`/`weight`/`family`; set in the bundled Inter, or a monospace face when the family says so |
| `defs`/`marker` | Drawn as an arrowhead oriented along the connector; enough for `marker-end`, not general marker support |
| Presentation attributes | `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, `fill-opacity`, `stroke-opacity`, `opacity`, `currentColor`, and the same properties via `style="…"` |

Gradients, filters, clip paths, patterns, masks and `use` are not supported: they are
skipped and named in the warnings. Stay inside the table and both engines agree.

By default the renderer refits the viewBox to what you drew, because hand-authored SVG
usually carries slack that would shrink the drawing. Set `"fit_viewbox": false` if your
viewBox is deliberate.

Worked example, the boundary from the ChatGPT/Postgres article:

```svg
<svg viewBox="0 0 600 420" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="#INK" stroke-width="2.5">
    <rect x="150" y="10"  width="300" height="64" rx="10"/>
    <rect x="150" y="118" width="300" height="64" rx="10"/>
    <rect x="150" y="226" width="300" height="64" rx="10" stroke="#ACCENT"/>
    <rect x="150" y="334" width="300" height="64" rx="10"/>
  </g>
  <g stroke="#INK" stroke-width="2.5" marker-end="url(#a)">
    <path d="M300 74 v44"/><path d="M300 182 v44"/><path d="M300 290 v44"/>
  </g>
  <g font-family="Inter" font-weight="600" font-size="20" fill="#INK" text-anchor="middle">
    <text x="300" y="49">ChatGPT</text>
    <text x="300" y="157">Microsoft Entra ID</text>
    <text x="300" y="265" fill="#ACCENT">Custom MCP server</text>
    <text x="300" y="373">PostgreSQL</text>
  </g>
</svg>
```

It is the article's own four-layer stack, the boundary component is the accented one
because that is the article's argument, and nothing in it is decorative.

### `code`

Real code from the article in a monospace face, on an inset panel.

- 4–10 lines. More than that reads as texture.
- Copy it from the article verbatim, including the bug if the point is the bug.
- `highlight` tints the lines carrying the point, usually the vulnerable line or the fix.
- No line numbers unless the prose refers to them. No fake IDE chrome, no traffic-light
  dots.

A technical reader should recognise something true at a glance. An invented snippet reads
as fake.

### `photo`

A photograph in the artwork column, beside the text. Distinct from `surface: photo`, which
puts a photograph behind everything.

- `art_img` is the path. Relative paths are read from the working directory first, then
  from the spec's own folder, so a spec can live next to its images.
- It is fitted inside the artwork box without cropping.
- A real photograph of something specific.

## Worked example: the `photo` surface

`surface: photo` needs a real photograph, so there is no runnable example in
`assets/examples/`. The shape is:

```json
{
  "slug": "the-server-room-nobody-owns",
  "eyebrow": "FIELD NOTES",
  "headline": "The Server Room Nobody Owns",
  "accent": "Nobody Owns",
  "subhead": "Every audit found it. No budget line ever did.",
  "kicker": "INFRA · OWNERSHIP · RISK",
  "surface": "photo",
  "theme": "slate",
  "art": "none",
  "photo": "shots/rack-corner.jpg"
}
```

- `art: none` is almost always right here. On `wide`/`split` the scrim clears to the
  right so the photograph can be seen; a diagram there fights the picture for the same
  half of the canvas.
- Brightness matters more than composition. The scrim holds white type over a bright
  photograph, but a blown-out sky in the text half will still fail. If `verify.py` flags
  contrast, crop to a darker part of the frame or use `dark`. Do not thin the scrim.

## Choosing per canvas

| Canvas      | Default art | Why |
| ----------- | ----------- | --- |
| `banner`    | as spec     | Widest canvas, most room for a diagram |
| `card`      | as spec     | The shipped j33.ai cards all carry artwork |
| `x`         | as spec     | Seen small in-timeline; simplify if the diagram has >6 nodes |
| `linkedin`  | often `none`| Square crops diagrams awkwardly; headline-led usually wins |
| `instagram` | often `none`| Portrait plus the 1:1 grid crop leaves little room |

Set these through `overrides`. The renderer does not drop artwork on its own.

## Headline fitting

The renderer shrinks the headline within a range per canvas. If it bottoms out at the
minimum it prints a warning. Treat that as "cut words", not "lower the minimum": the
minimums are where the type stops surviving a phone-sized thumbnail.

Manual line breaks with `\n` beat automatic wrapping whenever the natural break is not
where the wrap lands. Break on the syntactic seam:

```
ChatGPT Should Never
Touch Your Database          ✓ breaks between subject and predicate

ChatGPT Should Never Touch
Your Database                ✗ splits the verb phrase
```

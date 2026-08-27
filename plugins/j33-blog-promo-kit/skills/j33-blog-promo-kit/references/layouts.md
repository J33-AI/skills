# Spec schema and art modes

One JSON file drives all five renders. Write it, render, look at the output, adjust.

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
  "surface":  "navy",        // paper | navy | photo
  "display":  "inter",       // inter | anton   (anton is caps-only)
  "photo":    "path/to.jpg", // required when surface = photo

  // ── artwork ─────────────────────────────────────────────────────────────
  "art":      "diagram",     // none | diagram | code
  "art_svg":  "<svg viewBox='0 0 600 420'>…</svg>",   // when art = diagram
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

Only `slug`, `headline`, and `surface` are required. Everything else has a sane default.

`overrides` exists because a headline that reads well across a 1600px banner often needs a
manual line break on a 1080px portrait canvas, and because artwork that works in `split`
frequently should just be dropped in `stack`. Override rather than compromising the wide
canvases.

## Art modes

### `none`

Type and air. The right half (or lower half) stays empty except for the surface treatment.

Use it when the article is argumentative rather than mechanical — an opinion piece, a
postmortem, a "why you shouldn't" — where there is no honest diagram to draw. This is a
legitimate first choice, not a fallback. Restraint reads as confidence.

### `diagram`

You author real SVG describing the article's actual system. This is the highest-value mode
and the main thing separating these cards from generic tech-blog art.

Rules that keep it on-brand:

- `viewBox` of `0 0 600 420` for `split`/`wide`, `0 0 600 480` for `stack`. The renderer
  scales it; author in those coordinates.
- Strokes: `#0A0D33` on `paper`, `#FFFFFF` on `navy`/`photo`. Width `2.5`–`3`.
- Node fills: none, or the surface colour. Outlined boxes, not filled blocks.
- Numeric values, labels that carry the payload, and the single most important arrow:
  `#0099CC`.
- Corner radius `10` on node rectangles.
- Labels in Inter 600 at `18`–`22` units. Monospace for anything that is literally code.
- Dashed strokes (`stroke-dasharray="6 6"`) for the "not yet computed" or "blocked" parts.

Copy the labels verbatim from the article. If the article says "Custom MCP server", the box
says "Custom MCP server", not "AI Gateway". Invented labels are how a diagram starts looking
like decoration.

Worked example — the boundary from the ChatGPT/Postgres article:

```svg
<svg viewBox="0 0 600 420" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="#FFFFFF" stroke-width="2.5">
    <rect x="150" y="10"  width="300" height="64" rx="10"/>
    <rect x="150" y="118" width="300" height="64" rx="10"/>
    <rect x="150" y="226" width="300" height="64" rx="10" stroke="#0099CC"/>
    <rect x="150" y="334" width="300" height="64" rx="10"/>
  </g>
  <g stroke="#FFFFFF" stroke-width="2.5" marker-end="url(#a)">
    <path d="M300 74 v44"/><path d="M300 182 v44"/><path d="M300 290 v44"/>
  </g>
  <g font-family="Inter" font-weight="600" font-size="20" fill="#FFFFFF" text-anchor="middle">
    <text x="300" y="49">ChatGPT</text>
    <text x="300" y="157">Microsoft Entra ID</text>
    <text x="300" y="265" fill="#0099CC">Custom MCP server</text>
    <text x="300" y="373">PostgreSQL</text>
  </g>
</svg>
```

Note what makes it work: it is the article's own four-layer stack, the boundary component
is the accented one because that is the article's argument, and there is nothing decorative
anywhere in it.

### `code`

Real code from the article in a real monospace face, on a subtly inset panel.

- 4–10 lines. More than that and it becomes texture rather than content.
- Copy it from the article verbatim, including the bug if the point is the bug.
- `highlight` tints the lines carrying the point — usually the vulnerable line or the fix.
- No line numbers unless the prose refers to them. No fake IDE chrome, no traffic-light dots.

The point of `code` is that a technical reader recognises something true at a glance. A
plausible-looking but invented snippet does the opposite.

## Choosing per canvas

| Canvas      | Default art | Why |
| ----------- | ----------- | --- |
| `banner`    | as spec     | Widest canvas, most room for a diagram |
| `card`      | as spec     | The shipped j33.ai cards all carry artwork |
| `x`         | as spec     | Seen small in-timeline; simplify if the diagram has >6 nodes |
| `linkedin`  | often `none`| Square crops diagrams awkwardly; headline-led usually wins |
| `instagram` | often `none`| Portrait plus the 1:1 grid crop leaves little room |

Set these through `overrides`. The renderer does not guess for you, deliberately — a
silently dropped diagram is worse than one you decided to drop.

## Headline fitting

The renderer auto-fits the headline within a range per canvas, shrinking to fit. If it
bottoms out at the minimum it prints a warning. **Treat that warning as "cut words", not
as "lower the minimum".** The minimums are set where the type stops surviving a phone-sized
thumbnail.

Manual line breaks with `\n` in the headline beat automatic wrapping whenever the natural
break is not where the wrap lands. Break on the syntactic seam:

```
ChatGPT Should Never
Touch Your Database          ✓ breaks between subject and predicate

ChatGPT Should Never Touch
Your Database                ✗ splits the verb phrase
```

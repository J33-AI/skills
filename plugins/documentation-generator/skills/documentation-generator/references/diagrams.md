# Drawing figures

`scripts/diagram.py` draws at 3× and downsamples with Lanczos, so figures stay
sharp when Word scales them to page width. Canvas width 940–1180 logical px.

Never embed a screenshot. A drawn figure can be corrected; a screenshot rots the
day the UI changes and nobody can fix it.

## Palette — semantic, not decorative

| Pair | Meaning |
|---|---|
| `GREEN_F/S` | exists, works, allowed, the happy path |
| `BLUE_F/S` | new, informational, user-facing |
| `AMBER_F/S` | waiting, caution, configuration |
| `RED_F/S` | terminal, refused, forbidden, a gap |
| `PURPLE_F/S` | internal, staff-only, deferred |
| `TEAL_F/S` | cross-cutting explanation |
| `GREY_F/S`, `SLATE_F/S` | neutral, system, closed |

`_F` is the fill, `_S` the stroke. Use them as a pair. A reader who has seen
three of your figures already knows what amber means — do not spend that.

## Primitives

```python
c = Canvas(1140, 620)
c.title(24, 14, "A title that states the point")
c.caption(24, 44, "A subtitle that adds something the title could not")

c.box(x, y, w, h, "label", sub="smaller second line",
      fill=GREEN_F, stroke=GREEN_S, font=c.f.bold, radius=8)

c.arrow([(x1, y1), (x2, y2)], fill=GREEN_S, width=2,
        label="what happens", label_at=(x, y))

c.text(x, y, "free text", c.f.small, MUTED, anchor="ma")   # ma = centred
c.line([(x1, y1), (x2, y2)], fill=FAINT, width=2, dashed=True)
c.diamond(cx, cy, w, h, "decision?")

c.save(p("01_name.png"))
```

Fonts on `c.f`: `title`, `bold`, `body`, `small_bold`, `small`, `tiny`, `mono`.

**`|` inside a box label is a hard line break.** That is the only markup the
drawing layer understands — `**bold**` renders as literal asterisks. Use
CAPITALS for emphasis inside a figure.

## Sequence diagrams

```python
s = Sequence(1140, [("C", "Client"), ("API", "Endpoint"), ("DB", "Database")],
             step=44)
s.msg("C", "API", "POST /resource")
s.msg("API", "C", "201 { id }", style="reply")      # dashed, green
s.note("API", "Something worth saying", span=("C", "DB"))
s.sep("TRANSACTION BEGINS")                          # a labelled divider
s.render(p("03_sequence.png"))
```

`.sep()` is what makes a sequence diagram worth drawing. Marking where a
transaction opens and closes shows the reader something they cannot get from
reading the code linearly.

## Recurring layouts

| Layout | When |
|---|---|
| **Card list** | Name · condition · consequence, in three columns. The workhorse — most figures are this. |
| **Layered stack** | Request path. One box per layer, each naming its directory. |
| **Sequence** | Anything with ordering or a transaction boundary. |
| **State machine** | Stages and transitions. Lifecycle bands across the top, elbow arrows between boxes. |
| **Comparison** | Two panels — red "what would be wrong", green "what the code does". Use when a decision could plausibly have gone the other way. |
| **ER diagram** | Tables as boxes with a coloured header and one line per column. |
| **Wireframe** | A screen. Browser chrome, then boxes as fields and buttons. |

## The `entity()` pattern for ER diagrams

Not in `diagram.py` — it is ten lines you write per document, because every
schema wants slightly different columns:

```python
ROW_H, HEAD_H = 15.5, 26

def entity(c, x, y, w, name, cols, fill, stroke):
    h = HEAD_H + len(cols) * ROW_H + 6
    c.box(x, y, w, h, "", fill=WHITE, stroke=stroke, radius=6, width=2)
    c.d.rounded_rectangle(c._s(x, y, x + w, y + HEAD_H + 6), radius=18,
                          fill=fill, outline=stroke, width=6)
    c.text(x + 10, y + 6, name, c.f.small_bold, INK)
    cy = y + HEAD_H + 10
    for col, tag in cols:                      # tag: "pk" | "fk" | "" | "muted"
        c.text(x + 10, cy, col, c.f.tiny, INK if tag != "muted" else MUTED)
        if tag in ("pk", "fk"):
            c.text(x + w - 10, cy, tag.upper(), c.f.tiny, stroke, anchor="ra")
        cy += ROW_H
    return (x, y, w, h)
```

Then draw foreign keys as elbow arrows between box edges. Helpers `left()`,
`right()`, `top()`, `bottom()` in the render template give you the anchor points.

## Arrow routing

- **Elbows, not diagonals.** A diagonal across a busy figure is unreadable at
  print size.
- **Reserve a lane and stay in it.** Long return arrows go around the outside,
  never through a box.
- **If two labels collide, move one** to a distinct x. Do not shrink the font —
  the next reader will not be able to read it either.
- Where a transition applies from many states, **annotate the target box**
  rather than drawing six arrows into it.

## Verify every figure

Pillow does not reflow text. Overlapping labels, clipped boxes, text running
past a panel edge and missing-glyph tofu are all invisible until somebody looks
at the PNG.

Read every figure you generate before putting it in a document. This catches
something roughly one time in three, and it is the difference between a document
that looks considered and one that looks generated.

Common failures:

| Symptom | Cause |
|---|---|
| Black boxes or blank squares | An emoji or symbol the font lacks — use words |
| Text past the panel edge | Box too narrow for the string; widen or split with `\|` |
| Two labels on top of each other | Both defaulted to the segment midpoint — set `label_at` |
| Literal `**` in the image | Markdown in a diagram; use CAPITALS |
| Content clipped at the bottom | Canvas height too small — it does not auto-grow |

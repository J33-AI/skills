# House style

The look and the voice. Both matter — a beautiful document that hedges is
useless, and a sharp document that looks like a wiki page does not get read.

## Page and type

| Property | Value |
|---|---|
| Page | A4, 210 × 297 mm |
| Margins | 20 mm sides and top, 18 mm bottom |
| Content width | **6.55 in** — every table width must sum to this |
| Body | Segoe UI 10 pt, 1.18 line spacing |
| Headings | H1 19 pt ink · H2 14 pt blue · H3 11.5 pt ink, bold, keep-with-next |
| Mono | Consolas — code blocks 8.5 pt, inline one point below surroundings |

All of this is already set by `Doc()`. Do not restyle.

## Document skeleton

1. **Cover** — `d.cover(programme, title, subtitle, tagline, meta_rows)`
2. **Orientation callout** — "the short version", 3–5 sentences
3. **Contents** — `d.contents()`
4. **Numbered sections** — `d.h1("1.  Title", page_break=True)`
5. **Open questions**
6. **Sources**
7. **Footer** — `d.footer_text(...)`

Section numbers use two spaces after the dot: `"1.  What this does"`. It reads
better at 19 pt and it is what every existing document does.

## Callouts

| Kind | Use for |
|---|---|
| `note` | Something the reader needs but would not think to ask |
| `reuse` | Existing code that already does the job — **cite a file path** |
| `build` | What genuinely has to be written |
| `warn` | A trap, a conflict, a constraint — **name the consequence** |
| `ui` | Verbatim UI copy, quoted as the user sees it |

Two rules carry most of the weight:

- **A `warn` must name a consequence.** "This is important" is not a warning.
  "The constraint fires on the first autosave and makes the form unusable" is.
  If you cannot say what goes wrong, it is a `note`.
- **A `reuse` must cite a file.** `services/pricing.py`, not "the pricing layer".
  An uncheckable claim is worse than none, because it will be believed.

Two callouts in a row is a smell. Three is prose that should have been a table.
Never open a section with one — set the scene in a sentence, then interrupt.

## Inline markup

```
**bold**     emphasis, and the first phrase of a callout line
`code`       identifiers, paths, columns, endpoints — mono and purple
_italic_     quoted requirement text, quoted UI strings
- item       inside a callout, becomes a bullet
```

## Tables

Widths must sum to ≈ 6.55 in. Standard shapes:

| Purpose | Columns | Widths |
|---|---|---|
| Column spec | Column · Type · Null · Notes | `[1.5, 1.45, 0.5, 3.1]` |
| Endpoint list | Endpoint · Purpose · State · Notes | `[1.15, 2.45, 0.85, 2.1]` |
| Decisions | # · Decision · Recommendation | `[0.3, 2.6, 3.65]` |
| Comparison | Do · Do not | `[3.2, 3.35]` |
| Three-column | Thing · Where · Why | `[2.1, 2.2, 2.25]` |

`font_size=8.5` for reference tables, `9` for short ones, `9.5` on the cover.
The first column is the key. If the last column does not earn its place, the
table should have been a bullet list.

## Code blocks

Shaded, no syntax colouring, under ~22 lines. Longer belongs in a figure or
should be trimmed to the interesting part. Show request and response together.

## Figures

Captions are numbered automatically and **assert something** — "Two panes: pick
a day on the left, a time on the right" — rather than restating the title.

## Voice

A careful colleague explaining a decision to another engineer. Not a vendor,
not a textbook.

**Do:**

- State the decision, then the reason.
- Name consequences concretely — "two writers, one row, and the later one wins
  silently".
- Say what is missing or wrong in the same voice as what works.
- Point at a file for every claim about the code.
- Where the code contradicts a comment, a README or itself, **say so** and say
  which one you believed. That is a finding, and it is often the most valuable
  sentence in the document.

**Do not:**

- Hedge. Decide, or say plainly that it is open.
- Use: simply, just, obviously, seamless, robust, leverage, utilise,
  best-in-class, cutting-edge.
- Pad a table row to fill a column.
- Narrate code line by line — explain shape, boundaries and failure modes.
- Claim the code does something you have not read.

## Numbers and references

- Section cross-references as `§n` — `§9`, `see §4.2`.
- File paths as written on disk, with a line number where it helps:
  `app/models/user.py:23`.
- Numbers under ten in words in prose; digits in tables.
- British spelling — organisation, behaviour, recognised.

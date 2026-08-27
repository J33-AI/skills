# J33.AI brand reference

Fixed values come from the live site CSS (`https://j33.ai/assets/root-*.css`). If the
site is restyled, re-pull that file and update this one.

## Three tiers of colour

| Tier   | What                                                          | Rule                                         |
| ------ | ------------------------------------------------------------- | -------------------------------------------- |
| Locked | The `J33.AI` lockup                                           | Never themed. `.AI` is always `#0099CC`      |
| Family | The plate behind everything                                   | The theme's, inside the brand's tonal range  |
| Free   | Accent word, eyebrow, diagram highlights, code highlight       | The theme's                                  |

Every article picks a theme. The theme colours the plate and the accent so one article
does not look like the last one. The lockup does not move.

## Fixed tokens

```css
--color-primary:      #0099CC;  /* brand cyan: the ".AI" of the lockup */
--color-primary-dark: #007AA3;  /* the same cyan for cream plates */
--color-navy:         #0A0D33;  /* type on light plates */
--color-secondary:    #1E3A8A;  /* diagram fills and chart series, never headline words */
--color-body:         #7A7A7A;  /* body text on light */
--color-body-light:   #94A3B8;  /* body text on dark, before the theme swings its hue */
--color-bg:           #FFFFFF;
--color-bg-alt:       #F5F5F5;
--photo-dark:         #02080F;  /* the near-black behind photographic cards */
```

## Themes

`profiles.THEMES` is the source of truth. Each theme carries a deep plate as (gradient
start, end), a paper plate, and two accents: a bright one for dark plates and a deeper
twin for cream, because a bright accent washes out on paper.

| Theme     | Accent (dark) | Accent (paper) | Deep plate          | Paper     | For                                        |
| --------- | ------------- | -------------- | ------------------- | --------- | ------------------------------------------ |
| `signal`  | `#0099CC`     | `#007AA3`      | `#0A0D33`→`#01102D` | `#F6F0E2` | Default. AI integration, MCP, platform     |
| `crimson` | `#E23744`     | `#B4232F`      | `#1B0710`→`#12040A` | `#F7EDEA` | Security, breaches, threat models          |
| `ember`   | `#F26A1B`     | `#B84C0C`      | `#1C0E06`→`#120802` | `#F8EFE4` | Incidents, outages, postmortems            |
| `gold`    | `#D9A21B`     | `#8A6410`      | `#1A1305`→`#110C02` | `#F7F1DE` | Cost, billing, spend, waste                |
| `citron`  | `#A9C41F`     | `#6B7D0F`      | `#131805`→`#0C1002` | `#F3F3E2` | Data, analytics, benchmarks                |
| `moss`    | `#3FA34D`     | `#2A7A36`      | `#08170D`→`#041008` | `#ECF3E9` | Reliability, savings realised, results     |
| `violet`  | `#8B5CF6`     | `#6234D4`      | `#130A2E`→`#0C0620` | `#F0EDF8` | Models, evals, research                    |
| `plum`    | `#A63FBF`     | `#7C2A92`      | `#170A1C`→`#0E0512` | `#F4EBF6` | Strategy, opinion, positioning             |
| `magenta` | `#D6389B`     | `#A81F73`      | `#1B0716`→`#12040E` | `#F8EBF3` | Launches, releases, announcements          |
| `slate`   | `#8E97A3`     | `#5C6570`      | `#0E1218`→`#070A0E` | `#EFF1F4` | Compliance, governance, procurement        |
| `mono`    | none          | none           | `#0B0B0D`→`#050506` | `#F4F2EE` | Manifestos, pure-argument pieces           |

`mono` has no accent: the ink does that job, and the lockup's cyan is the only colour on
the image.

Two rules hold the family together. `verify.py` and `load_spec` enforce both.

- Every deep plate sits in the same lightness band, so a themed background reads as J33
  in another key rather than another brand.
- An accent sits at least 60 degrees of hue from `#0099CC`, or is desaturated enough to
  read as grey. Closer than that and the `.AI` looks like a failed colour match rather
  than the mark. `slate` and `mono` take the grey exemption.

Secondary type on a dark plate (subhead, kicker) keeps `#94A3B8`'s lightness and
saturation but swings to the theme's hue, so a warm theme does not carry a cool grey.
`signal` leaves it exactly `#94A3B8`.

### One-off accents

`"accent_hex": "#7C2A92"` in the spec overrides the theme's accent on every plate. It is
checked against the hue rule and rejected if it sits too near the lockup. Use a theme
unless the article genuinely needs a colour none of them carry.

### Using them

- On `paper`: headline `#0A0D33`, accent the theme's paper accent, kicker `#0A0D33`,
  rules `#0A0D33` at 100%.
- On `dark`: headline `#FFFFFF`, accent the theme's dark accent, subhead the swung grey,
  hairlines `#FFFFFF` at 22%.
- On `photo`: headline `#FFFFFF`, accent the theme's dark accent, and a scrim tinted with
  the theme's plate so contrast holds; see `image-specs.md`.

One accent per image, plus the lockup. `#1E3A8A` is for diagram fills and chart series,
never for headline words; it is too close to the navy to read as an accent.

## Typography

The site is Inter throughout:

```css
--font-sans: "Inter", system-ui, sans-serif;
```

Bundled in `assets/fonts/`, both under the SIL Open Font License 1.1 (`OFL-Inter.txt`,
`OFL-Anton.txt`), so the skill works with no network access:

- Inter (variable, axes `opsz` 14–32 and `wght` 100–900): the brand face. `wght` 800–900
  for display, 600–700 for kickers, 400–500 for subheads.
- Anton (static): the heavy condensed display face on the editorial cards ("ATTENTION,
  WORKED OUT BY HAND"). Caps only, headline only.

Monospace for code artwork: `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`,
matching the site's code blocks.

### The site's type scale

```css
--text-h1: 50px;  --leading-h1: 1.08;
--text-h2: 42px;  --leading-h2: 1.14;
--text-h3: 28px;  --leading-h3: 1;
--text-body: 17px; --leading-body: 1.5;
--text-label: 12px;
```

Web sizes; posters are 2–3× larger. Keep the leading ratios, especially 1.08 on a tight
headline.

## The logo lockup

Wordmark, always live text:

```
J33.AI
└┬─┘└┬┘
 │   └── ".AI"  →  #0099CC on every theme
 └────── "J33"  →  #0A0D33 on light plates, #FFFFFF on dark
```

Inter, weight 800, letter-spacing `-0.02em`. The dot belongs to the cyan run: `J33` +
`.AI`.

Placement, matching the shipped cards:

- `paper`: bottom-left, below the kicker.
- `dark` and `photo`: top-left, above the headline.

Size about 3.5% of canvas width (56px on a 1600px canvas), with at least one logo-height
of clear space on every side. Never rotate it, never put it on a busy part of a
photograph, never recolour either run — not to match the theme, not to match each other.

## Radii, shadows, spacing

```css
--radius-sm:   8px;
--radius:      12px;
--radius-lg:   15px;
--radius-pill: 38px;
--shadow-soft: rgba(0,0,0,.15) 0 40px 80px 0;
--shadow-card: rgba(0,0,0,.08) 0 20px 40px 0;
```

Scale radii with the canvas. Diagram nodes on the editorial cards use roughly
`--radius-sm` scaled up: soft, not pill-shaped.

## Voice

From the articles: direct, first-person plural, states a position and then justifies it.
"a prompt is a suggestion, not a security control" is the register. Not breathless, not
hedged, no exclamation marks.

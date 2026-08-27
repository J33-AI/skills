# J33.AI brand reference

Values are from the live site CSS (`https://j33.ai/assets/root-*.css`). If the site is
restyled, re-pull that file and update this one.

## Colour tokens

```css
--color-primary:    #0099CC;  /* cyan: the accent, and the ".AI" in the logo */
--color-secondary:  #1E3A8A;  /* deep indigo: secondary fills, chart series */
--color-navy:       #0A0D33;  /* the core brand dark; headings on light surfaces */
--color-navy-light: #01102D;  /* slightly cooler and darker; gradient end */
--color-heading:    #0A0D33;
--color-body:       #7A7A7A;  /* body text on light */
--color-body-light: #94A3B8;  /* body text on dark */
--color-bg:         #FFFFFF;
--color-bg-alt:     #F5F5F5;
--color-input:      #FAFAFA;
```

Two values sampled from the shipped article cards, not in the CSS but part of the look:

```css
--paper:      #F6F0E2;  /* the warm cream of the editorial cards */
--photo-dark: #02080F;  /* the near-black the photographic cards sit on */
```

The hover colour derived from primary:

```css
--color-primary-dark: #007AA3;
```

### Using them

- On `paper`: headline `#0A0D33`, accent `#0099CC`, kicker `#0A0D33`, rules `#0A0D33` at 100%.
- On `navy`: headline `#FFFFFF`, accent `#0099CC`, subhead `#94A3B8`, hairlines `#FFFFFF` at 22%.
- On `photo`: headline `#FFFFFF`, accent `#0099CC`, and a navy scrim over the photo so
  contrast holds; see `image-specs.md`.

One accent colour per image. `#1E3A8A` is for diagram fills and chart series, not for
headline words; it is too close to the navy to read as an accent.

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
 │   └── ".AI"  →  #0099CC
 └────── "J33"  →  #0A0D33 on light surfaces, #FFFFFF on dark
```

Inter, weight 800, letter-spacing `-0.02em`. The dot belongs to the cyan run: `J33` +
`.AI`.

Placement, matching the shipped cards:

- `paper`: bottom-left, below the kicker.
- `navy` and `photo`: top-left, above the headline.

Size about 3.5% of canvas width (56px on a 1600px canvas), with at least one logo-height
of clear space on every side. Never rotate it, never put it on a busy part of a
photograph, never recolour the two runs to match each other.

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

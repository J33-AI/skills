# J33.AI brand and art direction

## Brand priority

1. Use `#0099CC` for the `.AI` portion of the J33.AI wordmark. Do not substitute purple or violet for `.AI`.
2. Render `J33` in white or another neutral colour chosen for clear contrast with the image background.
3. A user-supplied official logo is authoritative for shape and proportions; preserve the `.AI` blue without recoloring it.
4. If current J33.AI brand assets are already available in the workspace, reuse them.
5. Otherwise use the renderer defaults: Inter for all text, warm white or charcoal chosen from the background, `.AI` blue `#0099CC`. No accent colour, rule or badge. Do not fabricate a symbol or logo mark.

When a transparent J33.AI logo is supplied, pass it to the renderer with `--logo`. Do not redraw it. Keep clear space around it and do not place it inside a pill, badge or fake app chrome.

## Typography and contrast

- Render typography after the final crop, directly at the target output size. Never place text inside generated source artwork.
- Keep article titles and category labels neutral. The renderer measures the background under the text block and under the wordmark separately and picks warm white over dark areas or charcoal over light areas for each.
- A colon in the title splits it into a headline and a smaller deck line. Keep the deck to a few words.
- Require strong contrast and inspect the text at 100% size and at mobile-thumbnail size.
- Keep `J33` in the chosen neutral text colour unless the official supplied logo specifies otherwise. Keep `.AI` fixed at `#0099CC`.
- Use `--text-color` or `--j33-color` only to override a wrong automatic choice. The scrim behind the text is soft, local and tinted from the plate; it is only as strong as the 6:1 contrast target needs.

## Concept selection

Choose one visual thesis tied to the article's mechanism. Good concepts expose a relationship: separation, routing, trust, flow, comparison, compression, handoff or constraint. Use the article's own concrete nouns when possible.

Prefer, in this order:

1. a believable editorial photograph or macro still life with controlled composition;
2. a tactile, product-photography-style arrangement of real materials;
3. a clean, precise diagram or geometric editorial illustration when the subject is abstract.

Avoid the default “technology poster” vocabulary: blue neon, glowing brains, robot heads, floating dashboards, random network nodes, anonymous hooded attackers and rows of meaningless code.

## Source-art prompt requirements

Prompts for source artwork must state all of the following:

- editorial campaign image for a professional technology consultancy;
- the article-specific subject and one clear visual relationship;
- believable materials, lighting, scale and camera behavior;
- uncluttered composition with generous negative space for later typography;
- a centered or safely crop-able focal subject that works in 4:5, 4:3 and 16:9;
- no words, letters, numerals, logos, watermarks, interface labels or fake code;
- no glossy sci-fi treatment, neon glow, excessive depth-of-field blur or generic AI iconography.

Generate source art only. Add typography and branding later with the renderer.

## Human-design test

Before accepting the campaign, ask:

- Could this image only belong to this article, or could it promote any AI post?
- Is there one dominant idea, or a collage of decorations?
- Are materials, shadows, reflections and scale believable?
- Is the composition confident when viewed small?
- Would removing half the elements make it stronger?

If the answer exposes generic or synthetic choices, revise the concept and rerender.

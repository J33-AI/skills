---
name: j33-blog-promo-kit-v2
description: "Turn a supplied J33.AI blog article or article draft into a coordinated promotion kit: Instagram, LinkedIn, X, website banner and website thumbnail images, plus platform-ready post copy. Use for J33.AI article promotion; not for writing or editing the article itself."
---

# J33 Blog Promo Kit v2

Create a coherent campaign from the article's actual argument, not merely its title. The result must feel commissioned by a human editor: restrained, specific, readable and consistent across all five surfaces.

## Inputs

Require the article title and body. Use a supplied article URL, logo, visual reference, brand palette or exact dimensions when available. If only title and body are supplied, proceed with the defaults in [references/deliverables.md](references/deliverables.md); do not block on optional inputs.

Read the full article before designing or drafting. Identify:

- the single strongest reader takeaway;
- the concrete subject or mechanism that can anchor the visual;
- the intended technical depth and audience;
- claims that must not be exaggerated.

## Produce the kit

1. Read [references/brand-and-art-direction.md](references/brand-and-art-direction.md) before creating imagery.
2. Form one campaign concept. Reuse it across every surface; do not create five unrelated designs.
3. Create artwork without lettering, logos, fake UI, code or interface labels. Prefer one high-resolution master with a centered subject and generous negative space. Create a separate vertical source only if the 4:5 crop materially weakens the composition.
4. Render titles and branding with `scripts/render_campaign.py`; use `--display-title` or `--short-title` when a faithful shorter version improves legibility. A colon in the title splits it into a headline and a smaller deck line. The renderer places the text block top-left, picks warm white or charcoal from the background under it, and adds a soft local scrim only where contrast falls short; pass `--text-anchor bottom` when the plate's negative space is at the bottom. Never ask an image model to spell the title or recreate the J33.AI logo. Use an attached transparent PNG logo when provided. Otherwise use the renderer's restrained text wordmark fallback.
5. Inspect every rendered image at full size and as a thumbnail. Revise the art, crop or `--text-anchor` if a subject is clipped, the text block sits on the subject, text is too small, contrast is weak (the renderer warns below 6:1), or any generated detail looks synthetic.
6. Read [references/copy-guide.md](references/copy-guide.md), draft three platform-specific posts, and save them to `post-copy.md`. If a publish URL was provided, include it in all three posts; otherwise use `[ARTICLE URL]` without inventing a link.
7. Run `scripts/check_copy.py post-copy.json` on a machine-readable copy of the final text. Fix any limit failure before delivery.
8. Verify the output set against [references/deliverables.md](references/deliverables.md). Deliver all five images and the copy together. Do not claim publishing or scheduling unless the user explicitly requested and authorized it.

## Quality bar

- Render every title, category label and wordmark directly at the final canvas size so the text is crisp. Never resize, blur or recompress a completed text layer.
- Keep article titles and category labels neutral. The renderer picks warm white on dark backgrounds and charcoal on light backgrounds and reports the contrast ratio per image; override with `--text-color` only when the automatic choice is wrong. Do not use decorative coloured title text or accent bars.
- Render only `.AI` in the official blue `#0099CC`. Render `J33` in white or another neutral colour that suits the background and maintains strong contrast.
- Keep image text to the article title or a faithful shortened title, an optional category, and J33.AI.
- Preserve technical accuracy. A short image title may simplify wording, but must not change the article's claim.
- Avoid generic AI imagery, glossy neon dashboards, humanoid robots, floating holograms, random circuits, excessive gradients, lens flares, fake code, cluttered icon collages and decorative padlocks.
- Prefer editorial photography, tangible objects, restrained geometric systems, documentary detail, material texture, natural light and article-specific visual metaphors.
- Do not use engagement bait, inflated claims, rhetorical filler, emoji chains, forced questions or phrases such as “game-changer,” “unlock,” “dive into,” “in today's fast-paced world,” or “the future is here.”
- If a first render looks templated or synthetic, change the underlying concept rather than adding more decoration.

## Output organization

Use a clean folder named from the article slug. Include only final deliverables plus `post-copy.md`; keep source artwork and temporary inspection files outside the final folder.

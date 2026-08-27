# J33-AI Skills

Shared Claude Code skills for the J33-AI team, packaged as an installable plugin marketplace.

## Prerequisites

1. **Claude Code** installed and signed in (`npm install -g @anthropic-ai/claude-code` or the desktop app).
2. **git** available on PATH (the marketplace is fetched via git clone; repo is public, no auth needed).
3. **Node.js ≥ 18 with `npx`** — the koboyo plugin bundles a Playwright browser-automation MCP server started via `npx @playwright/mcp`. First start downloads the package (and a browser on first `browser_*` use).
4. **Python 3.10+ with Pillow** (`pip install pillow`) — the j33-blog-promo-kit plugin renders images. Optional extras for it: **Playwright + Chromium** (`pip install playwright && playwright install chromium`) for the high-fidelity renderer, and **cairosvg** (`pip install cairosvg`) if you want SVG diagrams on the no-browser fallback path. Without Playwright it falls back to Pillow automatically.
5. *(Optional, better)* **Claude in Chrome extension** — if you have it, agents drive your real Chrome instead of the bundled Playwright browser. Install the extension in Chrome, then grant koboyo.com site permission in its settings. The koboyo skill's workflow was verified against this path.

## Install

In any Claude Code session:

```
/plugin marketplace add J33-AI/skills
/plugin install koboyo@j33-skills
/plugin install j33-blog-promo-kit@j33-skills
```

Then restart the session (or `/plugin` → verify enabled). Check it worked:

- `/plugin` shows `koboyo` installed and enabled.
- The skill appears in the available-skills list (ask Claude: "do you have a koboyo skill?").
- `/mcp` lists `koboyo-browser` (the bundled Playwright MCP) as connected or available.

On first use of the bundled MCP, Claude Code shows the standard "MCP server detected" permission prompt — approve it.

## Update

```
/plugin marketplace update j33-skills
```

## Skills

| Skill | What it does |
|---|---|
| **koboyo** | Diagram-as-code on [koboyo.com](https://koboyo.com): the full verified DSL (nodes, edges, groups, icons, 20 diagram families incl. sequence blocks, ERD crow's-foot, orgchart) plus the battle-tested browser rendering workflow — clean-canvas recipe, generate→export→download-PNG pipeline, layout model. Everything verified by live rendering; includes the traps (flowchart family is single-lane, Cmd+A misses off-viewport shapes, export needs two round-trips) so agents don't rediscover them. |

| **j33-blog-promo-kit** | Turns a blog article into a full publishing kit: five images at exact platform dimensions (Instagram 1080×1350, X 1600×900, LinkedIn 1200×1200, j33.ai banner 1600×873 and card 1659×948) plus the post copy for each channel. Brand tokens are pulled from the live j33.ai CSS. Every glyph is rendered by a real text engine (Chromium or Pillow), never an image model, so no warped letterforms — artwork is an SVG diagram of the article's own architecture or real code from the piece. Ships a verifier that checks the banner's 7:3 display crop, Instagram's 1:1 grid crop, contrast and file weight. |

**No browser? Still useful.** The DSL sections work standalone — Claude writes the diagram code, you paste it into koboyo.com's `</>` panel yourself (Cmd+Enter to generate). Browser automation (bundled Playwright MCP or Claude in Chrome) is only needed for fully hands-off render + PNG export.

## Contributing

One directory per plugin under `plugins/`, with `.claude-plugin/plugin.json` (manifest only — nothing else inside `.claude-plugin/`) and `skills/<name>/SKILL.md` at plugin root (agentskills spec: `name` + `description` frontmatter, description starts with "Use when..."). MCP servers go in `.mcp.json` at plugin root. Add an entry to `.claude-plugin/marketplace.json`. Skills must be tested before publishing — baseline an agent without the skill, verify compliance with it.

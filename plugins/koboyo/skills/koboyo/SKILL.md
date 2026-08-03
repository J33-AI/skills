---
name: koboyo
description: Use when creating, editing, or rendering diagrams on koboyo.com (Koboyo infinite canvas) — architecture diagrams, sequence diagrams, ERD, flowcharts — or when the user mentions Koboyo, its diagram-as-code panel, or asks to draw on koboyo.com.
---

# Koboyo Diagram-as-Code

## Overview

Koboyo (https://koboyo.com) is a free infinite-canvas whiteboard with its own diagram-as-code DSL. **It is NOT Mermaid, D2, or JSON — do not guess by analogy.** No API or MCP exists; interact via browser automation only. Docs: koboyo.com/docs (+ /docs/syntax, /docs/reference, /docs/attributes). All syntax below was verified by live rendering (2026-08-03).

## Critical anti-patterns (baseline agents invent these — all WRONG)

| Wrong (D2/Mermaid habit) | Right (Koboyo) |
|---|---|
| `node: "Label" { icon: x }` blocks | `Label [x]` — flat line, positional attrs |
| `color: "#4A90D9"` hex | Palette words only: `blue green red orange violet teal pink yellow gray` |
| `edge { style: dashed }` | `A --> B` (double dash = dashed) |
| `diagram "X" { ... }` wrapper | No wrapper. `title: X` line draws a labeled frame |

## Syntax

```
// comment                          ← // whole-line or trailing
title: My diagram                   ← optional, draws labeled frame
direction: right                    ← right (default) | down | left | up
icons: inside                       ← inside (default) | badge
colorMode: pastel                   ← pastel (default) | bold | outline

Name [attrs]                        ← node; attrs positional, comma-sep
api = FastAPI auth-api [attrs]      ← explicit id for long labels
A -> B: label                       ← solid arrow, label after colon to EOL
A --> B: label                      ← dashed arrow
A <-> B                             ← bidirectional
A -> B -> C                         ← chains; nodes auto-declare from edges
"A -> B" [note]                     ← quote names only if they contain -> : = , [ ] { } //
```

**Positional attrs** (vocabulary decides meaning, no keys needed):
- **icon**: `aws/lambda`, `aws/api-gateway`, `gcp/...`, `azure/...`, `tech/nginx`, `tech/fastapi`, `tech/postgres`, `tech/redis`, or bare `server browser database user lock`. Unknown icon → silent fallback to shape, never errors.
- **color**: `blue green red orange violet teal pink yellow gray` (hex/CSS map to nearest)
- **shape**: `rectangle ellipse diamond cylinder queue actor` + 40 more; aliases `box decision db database`
- **fill**: `pastel` (default) | `bold` | `outline`; plus `shadow` flag
- **frame**: `browser phone tablet window`
- Explicit keys when needed: `icon: color: shape: label: link: head:`

**Groups / layered layout** (verified live; the way to get professional aligned diagrams):
```
group Edge [teal] {
  Caddy [server, teal]
  nginx [tech/nginx, green]
}
```
- `group Name [attrs] { members }` renders a labeled tinted container; members separated by newlines or commas; groups nest; layout auto-contracts containers so nothing overlaps. Group attrs: color, icon, `frame` (browser/phone/tablet/window = device chrome).
- Alternative: node joins group via its own attrs — `nginx [tech/nginx, group: Edge]`.
- Layout is compiler-owned: no coordinates; declaration order drives placement; direction + groups are the layout levers. Manual drag on canvas afterwards works and code round-trips.
- Layered pattern for architecture diagrams: one group per tier (Client / Edge / App / Data) + `direction: right` → horizontal main flow with vertically stacked columns per tier.

**Family headers** (first meaningful line; omitted = architecture, flows right):
`sequence | erd | class | flowchart | statemachine | bpmn | orgchart | wireframe | mindmap | gantt | gitgraph | sankey | timeline | journey | cycle | funnel | pyramid | venn | matrix | chart <bar|line|pie|area|scatter|donut|radar|quadrant>`

- **sequence** (verified live): blocks are BRACE-delimited, condition is bare text after keyword, NO colon:
  ```
  opt document scan {
    fe -> api: POST /scan-document
  }
  alt paid service {
    ...
  } else free service {
    ...
  }
  ```
  Also `loop cond { }`, `par label { } and label { }`, `break cond { }`; blocks nest. `activate X`/`deactivate X`; `note over X: text`, `note over X, Y:`, `note left of X:`, `note right of X:`. Lifelines declare like nodes (`api = Auth API [tech/fastapi]`) BUT icon attrs on lifelines are silently ignored — headers render as plain auto-colored boxes. Caveat: `else` renders as a separate ADJACENT frame, not a compartment — either/or reads poorly; two `opt` blocks + a note often communicate better.
- **erd** (verified live): entities MUST be declared before relations (relations naming undeclared tables are dropped with a diagnostic). Field blocks supported:
  ```
  users [blue] {
    id uuid pk
    email string
    authority_id uuid fk
  }
  users ||--o{ applications: submits
  ```
  Field = `name type key` (type/key optional; key = `pk`|`fk`; quote names with spaces). Crow's-foot one glyph per end, Mermaid-orientation — **brace opens toward the entity it touches**: `||` one, `|o`/`o|` zero-or-one, `}|`/`|{` one-or-many, `}o`/`o{` zero-or-many; joined by `--` (identifying, solid) or `..` (non-identifying, dashed). So `a ||--o{ b` is right, `a ||--}o b` is wrong-facing. Coarse forms also work: `1:1`, `1:N`, `N:1`, `N:M`, `->`.
- **class**: `--|>` inherit, `..|>` realize, `*--` compose, `o--` aggregate, `..>` depend, `--` assoc; visibility `+ - # ~`
- **flowchart** (verified live, both axes): layout is a SINGLE-LANE chain — `direction` only picks the axis (17 nodes → 840×6562 portrait or 8192×341 landscape strip; export clamps at 8192px). Decision branches never fan out 2D; alternates render as long bypass arcs. **For any flowchart with branches, use the architecture family instead**: no header, one `group` per stage, `[diamond]` nodes for decisions, edge labels for yes/no — architecture layout is genuinely 2D. Layout model: `direction` sets the MAIN axis; branches fan out perpendicular. Use `direction: down` for flowcharts (groups stack as bands, branches go sideways, ~1:5 portrait — normal flowchart shape); `direction: right` gets crushed against the 8192px export clamp (15-17:1 strips). Inter-group whitespace is not DSL-tunable; to compact further, merge adjacent stage groups or split the journey at a natural seam. **statemachine**: defaults right
- **orgchart** (verified live): same `id = Label [color]` + `->` grammar; header switches layout engine. Proper top-down tree — ranks on rows, siblings side by side, parents centred over children, arrowless elbow connectors (`->` = "reports to", not flow). Colors apply per node. Naturally page-friendly landscape (13-node/5-level tree → 2.53:1). **For tree-shaped content, strictly better than the architecture-family workaround.** No `direction` needed. Quirk: subtree width = widest descendant rank; leaf siblings of deep subtrees leave empty space, no rebalancing.
- **sequence tip**: to attach a note to a specific `alt`/`opt` branch, write it as a dashed message (`api --> worker: queued for review`) — `note over` inside a block escapes and renders as a free-floating sticky outside the frame
- Mermaid and eraser.io code imports directly

## Verified example (rendered correctly first try)

```
title: LexPortal dev stack

Browser [browser]
Caddy [server, teal]
nginx [tech/nginx, green]
api = FastAPI auth-api [tech/fastapi, green]
PostgreSQL [tech/postgres, blue]
Redis [tech/redis, red]
Regula [server, orange]

Browser -> Caddy: https
Caddy -> nginx: proxy
nginx -> api: /api
api -> PostgreSQL: sql
api -> Redis: sessions
api --> Regula: scan document
```

## Browser workflow

1. Navigate to https://koboyo.com — full editor works anonymously, no login (login = Google/GitHub/email, only for saving/AI/slides).
2. Open code panel: `</>` icon top right, or "Edit as code" link on a diagram frame.
3. Paste code → "Update diagram" button or Cmd+Enter. **Generating REPLACES the currently attached diagram**; code persists in panel for tweaking. To create a NEW frame instead: dismiss the `Editing "<name>". Generating replaces it.` banner via its "x" — the button label flips to "Generate diagram" (that label is the reliable signal the next generate creates a new frame).
4. Compiler is forgiving: malformed lines are skipped with diagnostics, not fatal. Status line reports e.g. "Updated 7 shapes · 6 arrows" / "Added 8 tables · 8 relations".
5. **One diagram per canvas.** Export PNG/SVG (hamburger menu, top left) always renders the ENTIRE canvas — selection and viewport are ignored. Anonymous Koboyo has NO "New canvas" (verified: hamburger = Open/Import/Save/Export/View only; one localStorage-backed canvas). Clean-canvas recipe (verified):
   1. Dismiss the code panel's `Editing "<name>"` banner (x) — button flips to "Generate diagram".
   2. Click an EMPTY canvas spot (mandatory — else Cmd+A selects code text, not shapes).
   3. **Cmd+1 (zoom to fit) BEFORE Cmd+A** — Cmd+A only selects shapes inside the viewport; wide diagrams leave off-screen orphans that silently contaminate the next export. Then Cmd+A, Delete, and screenshot to confirm empty.
   4. Paste new code, Generate. Always verify exports by READING the PNG, not trusting the canvas view.
   Before clearing, back up any diagram you didn't author: `get_page_text` on the canvas tab dumps the full code-panel source + all frame labels verbatim — regenerating from that source reproduces the diagram identically.
6. **Export needs two round-trips** (browser automation): click "Export", CONFIRM submenu painted (screenshot), then click "PNG image" in a separate tool call. Both clicks in one batch fail silently — no file, no error. Verify by listing ~/Downloads. Exports download as `canvas.png`, browser appends `(N)`.
7. Shortcuts: Cmd+1 = zoom to fit; Cmd+Z = undo. Code editor has NO auto-pairing/auto-indent — braces and quotes type in verbatim (paste-by-typing is safe). Diagrams round-trip: clicking a frame label reloads its current code into the panel.

## Full pipeline: generate → export → download PNG (battle-tested, 12+ renders)

Per diagram, in order:

1. **Clean canvas**: dismiss `Editing "<name>"` banner (x) → click empty canvas spot → Cmd+1 → Cmd+A → Delete → screenshot to confirm empty. (Cmd+1 first is non-negotiable: Cmd+A only selects in-viewport shapes; off-screen orphans silently contaminate the export.)
2. **Generate**: type/paste the DSL into the `</>` panel → button must read "Generate diagram" (not "Update diagram") → Cmd+Enter.
3. **Verify compile**: dismiss any autocomplete dropdown first (click elsewhere in panel — it covers the status line), then read the status line (`Added N shapes · M arrows` / `N tables · M relations` / `N lifelines · M messages`) and compare against the source's node/edge count. Check for skipped-line diagnostics.
4. **Frame it**: Cmd+1 (zoom to fit) — cosmetic only; export ignores viewport, but the confirm screenshot needs it.
5. **Export (two separate tool calls, never one batch)**: click hamburger → Export, screenshot to CONFIRM the submenu painted; THEN click "PNG image" in a new call. Single-batch double-clicks fail silently — submenu never paints, no file, no error.
6. **Confirm download**: `ls -t ~/Downloads/canvas*.png | head -1` — file appears as `canvas.png` or `canvas (N).png`. Chrome reuses freed names: if you moved the previous export away, the next one may reuse its number, so always take newest-by-mtime, never guess the name.
7. **Move immediately** to its final path: `mv "$(ls -t ~/Downloads/canvas*.png | head -1)" target/dir/my-diagram.png` — doing this per-diagram keeps names unambiguous.
8. **Verify by reading the PNG file** (not the canvas view): correct diagram, no orphan shapes, dimensions/aspect sane. This step has caught real contamination.

Incidents to expect: extension can drop connection mid-batch ("Browser extension is not connected") — the actions may have EXECUTED anyway; screenshot canvas state before re-running or you get duplicate renders. A frozen tab recovers by reload; Koboyo's localStorage keeps the diagram, but an old frame may resurrect from a stale snapshot — check for orphans after reload.
6. In Claude Code main session: always drive the browser via the Agent tool (user preference), never direct chrome MCP tools.

## Common mistakes

- Guessing D2/Mermaid syntax — see anti-pattern table above.
- Hex colors: accepted but mapped to nearest of the 9 palette words; just use the words.
- Forgetting `-->` for dashed/async edges.
- Expecting an API: there is none; PNG/SVG export or browser automation only.

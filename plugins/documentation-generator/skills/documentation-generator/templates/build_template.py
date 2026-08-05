"""TEMPLATE — copy to build_<name>.py and fill in.

    python render_<name>.py     # figures first
    python build_<name>.py      # then the document

Produces <name>.docx and <name>.md side by side. The Word file is for people;
the Markdown mirror is for git diffs and code review.

Remember to update the table of contents afterwards — it is a Word field and
stays empty until Word evaluates it. See SKILL.md, "Build and verify".
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from docxkit import BLUE, Doc, INK, MUTED          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DIA = os.path.join(HERE, "diagrams")
OUT = os.path.join(HERE, "output", "TITLE_HERE.docx")

# Standard column widths — each set sums to ≈ 6.55 in, the A4 content width.
COLS_SPEC = [1.5, 1.45, 0.5, 3.1]      # Column · Type · Null · Notes
COLS_EP = [1.15, 2.45, 0.85, 2.1]      # Endpoint · Purpose · State · Notes
COLS_DEC = [0.3, 2.6, 3.65]            # # · Decision · Recommendation
COLS_TWO = [3.2, 3.35]                 # Do · Do not
COLS_THREE = [2.1, 2.2, 2.25]          # Thing · Where · Why


def fig(name: str) -> str:
    return os.path.join(DIA, name)


d = Doc()

# ── Cover ──────────────────────────────────────────────────────────────────
d.cover(
    programme="PROJECT NAME  ·  TECHNICAL DOCUMENTATION",
    title="Component or System Name",
    subtitle="",                      # optional second line
    tagline="Architecture Overview",  # the document type
    meta_rows=[
        ["**Document ID**", "PRJ-ARCH-001"],
        ["**Version**", "1.0"],
        ["**Scope**", "What this document covers, in one sentence."],
        ["**Sources**", "Read from `path/to/module/` at commit `abc1234`."],
        ["**Audience**", "Who should read this and what they will do with it."],
    ],
)

# ── Orientation ────────────────────────────────────────────────────────────
d.callout("note", [
    "**The short version.** Three to five sentences: what this system does, and "
    "the one or two things a reader will be surprised by.",
    "",
    "If something is missing, inconsistent or riskier than it looks, name it "
    "here rather than burying it in a later section.",
], title="ORIENTATION")

# ── Contents ───────────────────────────────────────────────────────────────
d.contents()

# ── Body ───────────────────────────────────────────────────────────────────
d.h1("1.  What this system does", page_break=True)
d.p("Two or three paragraphs. Purpose first, then shape.")

d.figure(fig("01_cards.png"), "A caption that asserts something.")

d.h2("1.1  A sub-section")
d.bullet("A bullet, when order does not matter.")
d.numbered("A numbered step, when it does.")

d.table(
    ["Component", "Responsibility", "Source"],
    [
        ["`module.name`", "What it does", "`path/to/file.py`"],
    ],
    COLS_THREE, font_size=8.5,
)

d.code(
    "GET /api/v1/resource/{id}\n"
    "→ 200  { \"id\": \"…\" }\n"
    "→ 404  NOT_FOUND"
)

d.callout("warn", [
    "A trap, and **what happens if it is missed**. A warning without a "
    "consequence is a note.",
])

# ── Closing sections ───────────────────────────────────────────────────────
d.h1("n.  Open questions", page_break=True)
d.table(
    ["#", "Question", "Recommendation"],
    [
        ["1", "Something the code does not settle",
         "What you would do, and why — never a bare question."],
    ],
    COLS_DEC, font_size=8.5,
)

d.h1("n+1.  Sources")
d.p("Every claim in this document can be checked against the files below.")
d.table(
    ["Claim area", "File"],
    [
        ["Data model", "`app/models/`"],
        ["Endpoints", "`app/api/`"],
    ],
    [2.6, 3.95], font_size=8.5,
)

d.footer_text("PRJ-ARCH-001  ·  Component Name  ·  Architecture Overview  ·  v1.0")

print("wrote", d.save(OUT))

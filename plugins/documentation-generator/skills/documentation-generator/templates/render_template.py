"""TEMPLATE — copy to render_<name>.py and fill in.

One function per figure. Each returns the path it wrote, so the __main__ loop
prints a checkable list. Run this before the build script.

    python render_<name>.py

Diagrams draw at 3× and downsample, so they stay sharp when Word scales them to
page width. Canvas width 940–1180 logical px; height is whatever the content
needs.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from diagram import (                                    # noqa: E402
    AMBER_F, AMBER_S, BLUE_F, BLUE_S, Canvas, FAINT, GREEN_F, GREEN_S, GREY_F,
    GREY_S, INK, MUTED, PURPLE_F, PURPLE_S, RED_F, RED_S, SLATE_F, SLATE_S,
    Sequence, WHITE,
)

TEAL_F, TEAL_S = "#dcf0f2", "#2f7f88"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")
os.makedirs(OUT, exist_ok=True)


def p(name: str) -> str:
    return os.path.join(OUT, name)


# ── box edge helpers, for arrow endpoints ──────────────────────────────────
def right(b):  return (b[0] + b[2], b[1] + b[3] / 2)
def left(b):   return (b[0], b[1] + b[3] / 2)
def top(b):    return (b[0] + b[2] / 2, b[1])
def bottom(b): return (b[0] + b[2] / 2, b[1] + b[3])


# ═══════════════════════════════════════════════════════════════════════════
# Card list — the workhorse. Name · condition · consequence.
# ═══════════════════════════════════════════════════════════════════════════
def d1_cards():
    rows = [
        ("First thing", "when it applies",
         "What it means, in a sentence that survives being read alone.",
         GREEN_F, GREEN_S),
        ("Second thing", "when it applies", "…", AMBER_F, AMBER_S),
    ]
    c = Canvas(1140, 84 + len(rows) * 82 + 60)
    c.title(24, 14, "A title that states the point")
    c.caption(24, 44, "A subtitle that adds something the title could not.")

    y = 84
    for name, when, what, f, st in rows:
        c.box(24, y, 240, 74, name, sub=when, fill=f, stroke=st,
              font=c.f.small_bold, radius=7)
        c.box(276, y, 840, 74, what, fill=WHITE, stroke="#dde3ea",
              font=c.f.small, radius=7)
        y += 82
    return c.save(p("01_cards.png"))


# ═══════════════════════════════════════════════════════════════════════════
# Layered architecture
# ═══════════════════════════════════════════════════════════════════════════
def d2_layers():
    c = Canvas(1140, 560)
    c.title(24, 14, "Request path — one layer at a time")
    c.caption(24, 44, "Each layer names the directory it lives in.")

    layers = [
        ("HTTP  ·  routes", "app/api/", BLUE_F, BLUE_S),
        ("Validation  ·  schemas", "app/schemas/", GREEN_F, GREEN_S),
        ("Domain  ·  services", "app/services/", PURPLE_F, PURPLE_S),
        ("Persistence  ·  models", "app/models/", AMBER_F, AMBER_S),
        ("Database", "PostgreSQL", SLATE_F, SLATE_S),
    ]
    y = 90
    for name, where, f, st in layers:
        c.box(200, y, 740, 62, name, sub=where, fill=f, stroke=st,
              font=c.f.bold, radius=8)
        if y > 90:
            c.arrow([(570, y - 28), (570, y - 4)], fill=FAINT, width=3)
        y += 90
    return c.save(p("02_layers.png"))


# ═══════════════════════════════════════════════════════════════════════════
# Sequence — for anything with ordering or a transaction boundary
# ═══════════════════════════════════════════════════════════════════════════
def d3_sequence():
    s = Sequence(1140, [
        ("C", "Client"),
        ("API", "Endpoint"),
        ("SVC", "Service"),
        ("DB", "Database"),
    ], step=44)

    s.msg("C", "API", "POST /resource")
    s.msg("API", "SVC", "validate and dispatch")
    s.note("SVC", "Anything worth saying about what happens here.",
           span=("API", "DB"))
    s.sep("TRANSACTION BEGINS")
    s.msg("SVC", "DB", "INSERT …")
    s.sep("COMMIT")
    s.msg("API", "C", "201 { id }", style="reply")
    return s.render(p("03_sequence.png"))


# ═══════════════════════════════════════════════════════════════════════════
# Entity relationships — see scripts/diagram.py and the roles/DB renderers
# in the reference documents for the `entity()` helper pattern.
# ═══════════════════════════════════════════════════════════════════════════
def d4_comparison():
    c = Canvas(1140, 420)
    c.title(24, 14, "What is right, and what would be wrong")
    c.caption(24, 44, "Use this when a decision could plausibly have gone the "
                      "other way.")

    c.box(24, 84, 540, 220, "", fill=RED_F, stroke=RED_S, radius=9)
    c.text(48, 96, "WHAT WOULD BE WRONG", c.f.small_bold, RED_S)
    for i, line in enumerate(["Point one.", "Point two.", "The consequence."]):
        c.text(48, 128 + i * 26, line, c.f.small, INK)

    c.box(600, 84, 516, 220, "", fill=GREEN_F, stroke=GREEN_S, radius=9)
    c.text(624, 96, "WHAT THE CODE DOES", c.f.small_bold, GREEN_S)
    for i, line in enumerate(["Point one.", "Point two.", "Why it is better."]):
        c.text(624, 128 + i * 26, line, c.f.small, INK)

    c.box(24, 326, 1092, 74,
          "A closing note explaining the trade that was made, and what it costs.",
          fill=TEAL_F, stroke=TEAL_S, font=c.f.small, radius=9)
    return c.save(p("04_comparison.png"))


if __name__ == "__main__":
    for fn in (d1_cards, d2_layers, d3_sequence, d4_comparison):
        print("wrote", fn())

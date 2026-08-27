"""Canvas profiles, type scales, and spec loading.

Shared by both renderers so the Chromium and Pillow paths agree on geometry.
Numbers here are the source of truth for references/image-specs.md.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_ROOT / "assets" / "fonts"
TEMPLATE = SKILL_ROOT / "assets" / "templates" / "poster.html"

# ── palette (references/brand.md) ────────────────────────────────────────────
PRIMARY = "#0099CC"
SECONDARY = "#1E3A8A"
NAVY = "#0A0D33"
NAVY_LIGHT = "#01102D"
BODY_LIGHT = "#94A3B8"
PAPER = "#F6F0E2"
PHOTO_DARK = "#02080F"

# ── canvases ─────────────────────────────────────────────────────────────────
# crop_ratio is the aspect the *display surface* imposes on the file. Where it
# differs from the file's own aspect, content gets centre-cropped and the safe
# inset has to absorb it. banner is the one that bites: a 1600x873 file shown
# at 7:3 loses ~94px top and bottom.
CANVASES = {
    "banner": dict(
        out="{slug}.png", w=1600, h=873, layout="wide",
        inset_x=96, inset_y=110, crop_ratio=7 / 3, website=True,
    ),
    "card": dict(
        out="{slug}-card.png", w=1659, h=948, layout="split",
        inset_x=100, inset_y=100, crop_ratio=None, website=True,
    ),
    "instagram": dict(
        out="instagram.png", w=1080, h=1350, layout="stack",
        inset_x=72, inset_y=207, crop_ratio=1.0, website=False,
    ),
    "x": dict(
        out="x.png", w=1600, h=900, layout="split",
        inset_x=96, inset_y=96, crop_ratio=None, website=False,
    ),
    "linkedin": dict(
        out="linkedin.png", w=1200, h=1200, layout="stack",
        inset_x=88, inset_y=88, crop_ratio=None, website=False,
    ),
}

ORDER = ["banner", "card", "instagram", "x", "linkedin"]


def type_scale(w: int, layout: str) -> dict:
    """Type sizes as a fraction of canvas width.

    Portrait and square canvases get proportionally larger type: they are seen
    smaller in-feed, and they have vertical room the wide canvases do not.
    """
    if layout == "stack":
        f = dict(headline_max=.093, headline_min=.058, eyebrow=.0155,
                 subhead=.0260, kicker=.0175, logo=.0400, code=.0175, gutter=.035)
    else:
        f = dict(headline_max=.073, headline_min=.044, eyebrow=.0135,
                 subhead=.0225, kicker=.0155, logo=.0340, code=.0155, gutter=.045)
    scale = {k: round(w * v, 2) for k, v in f.items()}
    scale["u"] = round(w / 100, 3)
    return scale


def crop_box(name: str) -> tuple[int, int, int, int] | None:
    """The region of the file that actually survives to the viewer, or None.

    Returns (left, top, right, bottom) in file pixels.
    """
    c = CANVASES[name]
    ratio = c.get("crop_ratio")
    if not ratio:
        return None
    w, h = c["w"], c["h"]
    if abs(w / h - ratio) < 1e-6:
        return None
    if w / h > ratio:                      # too wide -> sides trimmed
        vw = int(round(h * ratio))
        x = (w - vw) // 2
        return (x, 0, x + vw, h)
    vh = int(round(w / ratio))             # too tall -> top/bottom trimmed
    y = (h - vh) // 2
    return (0, y, w, y + vh)


DEFAULTS = dict(
    eyebrow="", headline="", accent="", subhead="", kicker="",
    surface="navy", display="inter", art="none",
    art_svg="", art_code=None, photo="", art_img="",
)


def load_spec(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    if not spec.get("headline"):
        raise ValueError("spec is missing required field: headline")
    if not spec.get("slug"):
        raise ValueError("spec is missing required field: slug")
    if spec.get("surface") not in (None, "paper", "navy", "photo"):
        raise ValueError(f"unknown surface: {spec.get('surface')!r}")
    return spec


def resolve(spec: dict, canvas: str) -> dict:
    """Merge defaults, the spec, and any per-canvas override into one payload."""
    if canvas not in CANVASES:
        raise KeyError(f"unknown canvas {canvas!r}; expected one of {list(CANVASES)}")
    c = CANVASES[canvas]
    p = copy.deepcopy(DEFAULTS)
    p.update({k: v for k, v in spec.items() if k != "overrides"})
    p.update(spec.get("overrides", {}).get(canvas, {}))

    ts = type_scale(c["w"], c["layout"])

    # With no artwork a stack canvas is mostly empty, and a headline sized for
    # a shared canvas reads as timid. Let it grow into the space it now owns.
    has_art = (
        (p["art"] == "diagram" and p["art_svg"])
        or (p["art"] == "code" and p["art_code"])
        or (p["art"] == "photo" and p["art_img"])
    )
    if not has_art:
        p["art"] = "none"
        if c["layout"] == "stack":
            ts["headline_max"] = round(ts["headline_max"] * 1.28, 2)
            ts["headline_min"] = round(ts["headline_min"] * 1.15, 2)

    p.update(
        canvas=canvas, w=c["w"], h=c["h"], layout=c["layout"],
        inset_x=c["inset_x"], inset_y=c["inset_y"],
        fs_headline_max=ts["headline_max"], fs_headline_min=ts["headline_min"],
        fs_eyebrow=ts["eyebrow"], fs_subhead=ts["subhead"],
        fs_kicker=ts["kicker"], fs_logo=ts["logo"], fs_code=ts["code"],
        gutter=ts["gutter"], u=ts["u"],
        out_name=c["out"].format(slug=spec.get("slug", "poster")),
    )
    if p["surface"] == "photo" and not p.get("photo"):
        raise ValueError("surface 'photo' requires a 'photo' path in the spec")
    return p

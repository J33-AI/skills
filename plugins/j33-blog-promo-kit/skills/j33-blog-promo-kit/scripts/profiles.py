"""Canvas profiles, type scales, surface colours, fonts, and spec loading.

Shared by both renderers so the Chromium and Pillow paths agree. The numbers
here are the source of truth for references/image-specs.md.
"""

from __future__ import annotations

import colorsys
import copy
import functools
import json
import re
from pathlib import Path

from PIL import ImageColor, ImageFont

SKILL_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_ROOT / "assets" / "fonts"
TEMPLATE = SKILL_ROOT / "assets" / "templates" / "poster.html"

# Inter and Anton are bundled. A monospace face is not (no OFL mono is small
# enough to be worth it), so use one the host has. Windows, Linux, macOS.
MONO_CANDIDATES = (
    "consola.ttf", "cour.ttf",                                   # Windows
    "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf",           # Linux
    "NotoSansMono-Regular.ttf", "FreeMono.ttf",
    "Menlo.ttc", "Courier New.ttf",                               # macOS
)

# ── brand palette (references/brand.md) ──────────────────────────────────────
# No theme touches these. BRAND_CYAN is the ".AI" run of the lockup; NAVY is
# the type colour on light plates, white on dark ones.
BRAND_CYAN = "#0099CC"
BRAND_CYAN_DARK = "#007AA3"   # the site's --color-primary-dark, for cream plates
NAVY = "#0A0D33"
BODY_LIGHT = "#94A3B8"
PHOTO_DARK = "#02080F"

# How far an accent has to sit from the lockup's cyan, in degrees of hue. Any
# closer and the ".AI" reads as a failed colour match. Near-greys are exempt.
MIN_HUE_GAP = 60.0
NEUTRAL_SATURATION = 0.20

# ── themes ───────────────────────────────────────────────────────────────────
# A theme colours everything except the lockup. `dark` is the deep plate as
# (gradient start, end), `light` is the paper plate, `accent` is (on dark, on
# paper): a bright accent washes out on cream, so each theme carries a deeper
# twin for it. `mono` has no accent and takes the surface's type colour.
THEMES = {
    "signal":  dict(dark=("#0A0D33", "#01102D"), light="#F6F0E2",
                    accent=(BRAND_CYAN, BRAND_CYAN_DARK)),
    "crimson": dict(dark=("#1B0710", "#12040A"), light="#F7EDEA",
                    accent=("#E23744", "#B4232F")),
    "ember":   dict(dark=("#1C0E06", "#120802"), light="#F8EFE4",
                    accent=("#F26A1B", "#B84C0C")),
    "gold":    dict(dark=("#1A1305", "#110C02"), light="#F7F1DE",
                    accent=("#D9A21B", "#8A6410")),
    "citron":  dict(dark=("#131805", "#0C1002"), light="#F3F3E2",
                    accent=("#A9C41F", "#6B7D0F")),
    "moss":    dict(dark=("#08170D", "#041008"), light="#ECF3E9",
                    accent=("#3FA34D", "#2A7A36")),
    "violet":  dict(dark=("#130A2E", "#0C0620"), light="#F0EDF8",
                    accent=("#8B5CF6", "#6234D4")),
    "plum":    dict(dark=("#170A1C", "#0E0512"), light="#F4EBF6",
                    accent=("#A63FBF", "#7C2A92")),
    "magenta": dict(dark=("#1B0716", "#12040E"), light="#F8EBF3",
                    accent=("#D6389B", "#A81F73")),
    "slate":   dict(dark=("#0E1218", "#070A0E"), light="#EFF1F4",
                    accent=("#8E97A3", "#5C6570")),
    "mono":    dict(dark=("#0B0B0D", "#050506"), light="#F4F2EE",
                    accent=None),
}
DEFAULT_THEME = "signal"

# ── surfaces ─────────────────────────────────────────────────────────────────
# Type colours per surface. Both renderers draw from this table (the template
# gets it as CSS variables) and verify.py reads `fg` for its contrast check.
# Translucent colours are (r, g, b, a) with a in 0-255. `logo_top` puts the
# wordmark above the headline on dark surfaces, below it on paper.
# `code_label` stands in for the template's `opacity: .55` on the language tag.
# `light_plate` picks which of the theme's two accents this surface takes.
_DARK_TYPE = dict(
    fg="#FFFFFF", subhead=BODY_LIGHT, kicker=BODY_LIGHT,
    rule=(255, 255, 255, 56), logo_top=True, light_plate=False,
    code_fg="#E6EDF6", code_panel=(255, 255, 255, 12), code_edge=(255, 255, 255, 31),
    code_label=(150, 160, 180),
)
SURFACES = {
    "paper": dict(
        fg=NAVY, subhead="#4A4A55", kicker=NAVY,
        rule=(10, 13, 51, 255), logo_top=False, light_plate=True,
        code_fg=NAVY, code_panel=(10, 13, 51, 11), code_edge=(10, 13, 51, 36),
        code_label=(120, 122, 140),
    ),
    "dark": _DARK_TYPE,
    "photo": _DARK_TYPE,
}

# `navy` was the name before themes made the plate any colour.
SURFACE_ALIASES = {"navy": "dark"}


def surface_name(value: str | None) -> str:
    """The canonical surface name, or the value unchanged if unknown."""
    if not value:
        return "dark"
    return SURFACE_ALIASES.get(value, value)


def _hsv(hex_colour: str) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(*(c / 255 for c in ImageColor.getrgb(hex_colour)[:3]))


def retint(base: str, accent: str) -> str:
    """`base` at its own lightness and saturation, swung to the theme's hue.

    The swing is measured from the house accent, so `signal` returns `base`
    untouched and a warm theme warms it by however far its accent moved. Grey
    accents leave it alone.
    """
    accent_h, accent_s, _ = _hsv(accent)
    if accent_s < NEUTRAL_SATURATION:
        return base
    base_h, base_s, base_v = _hsv(base)
    swing = accent_h - _hsv(BRAND_CYAN)[0]
    r, g, b = colorsys.hsv_to_rgb((base_h + swing) % 1.0, base_s, base_v)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


# ── canvases ─────────────────────────────────────────────────────────────────
# crop_ratio is the aspect the display surface imposes on the file. Where it
# differs from the file's own aspect the content is centre-cropped and the
# inset has to absorb it: a 1600x873 banner shown at 7:3 loses ~94px top and
# bottom. webp_kb is the .webp weight budget; only the website files have one.
CANVASES = {
    "banner": dict(
        out="{slug}.png", w=1600, h=873, layout="wide",
        inset_x=96, inset_y=110, crop_ratio=7 / 3, webp_kb=340,
    ),
    "card": dict(
        out="{slug}-card.png", w=1659, h=948, layout="split",
        inset_x=100, inset_y=100, crop_ratio=None, webp_kb=200,
    ),
    "instagram": dict(
        out="instagram.png", w=1080, h=1350, layout="stack",
        inset_x=72, inset_y=207, crop_ratio=1.0, webp_kb=None,
    ),
    "x": dict(
        out="x.png", w=1600, h=900, layout="split",
        inset_x=96, inset_y=96, crop_ratio=None, webp_kb=None,
    ),
    "linkedin": dict(
        out="linkedin.png", w=1200, h=1200, layout="stack",
        inset_x=88, inset_y=88, crop_ratio=None, webp_kb=None,
    ),
}

ORDER = list(CANVASES)   # render order is table order

# In `stack` the artwork sits below the text and takes this share of the
# frame's height.
STACK_ART_FRAC = 0.36


def type_scale(w: int, layout: str) -> dict:
    """Type sizes as a fraction of canvas width, keyed as the payload wants.

    Portrait and square canvases get larger type: they are seen smaller
    in-feed and have vertical room the wide canvases do not.
    """
    if layout == "stack":
        f = dict(fs_headline_max=.093, fs_headline_min=.058, fs_eyebrow=.0155,
                 fs_subhead=.0260, fs_kicker=.0175, fs_logo=.0400, fs_code=.0175,
                 gutter=.035)
    else:
        f = dict(fs_headline_max=.073, fs_headline_min=.044, fs_eyebrow=.0135,
                 fs_subhead=.0225, fs_kicker=.0155, fs_logo=.0340, fs_code=.0155,
                 gutter=.045)
    scale = {k: round(w * v, 2) for k, v in f.items()}
    scale["u"] = round(w / 100, 3)
    return scale


def text_frac(layout: str, has_art: bool) -> float:
    """Share of the frame's width the text column takes.

    The Pillow composer, the template's flex-basis and verify.py all read it.
    """
    if layout == "stack":
        return 1.0          # text runs the full width; artwork sits below it
    if not has_art:
        return 0.78
    return 0.46 if layout == "wide" else 0.52


def crop_box(name: str) -> tuple[int, int, int, int] | None:
    """The region of the file the viewer actually sees, or None.

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


# ── fonts ────────────────────────────────────────────────────────────────────

_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}


@functools.cache
def mono_font_path() -> str | None:
    """The first face in MONO_CANDIDATES the host has, or None."""
    for name in MONO_CANDIDATES:
        try:
            ImageFont.truetype(name, 12)
        except OSError:
            continue
        return name
    return None


def font(size: float, weight: int = 400, opsz: float = 14.0,
         family: str = "inter") -> ImageFont.FreeTypeFont:
    """A cached face at `size` px. `family` is inter, anton or mono.

    Inter is the variable build, so weight and optical size are real axes.
    `mono` falls back to Inter when the host has no monospace face; check
    mono_font_path() to warn about that.
    """
    px = max(1, int(round(size)))
    key = (px, weight, opsz, family)
    if key not in _FONT_CACHE:
        if family == "anton":
            face = ImageFont.truetype(str(FONT_DIR / "Anton-Regular.ttf"), px)
        elif family == "mono" and mono_font_path():
            face = ImageFont.truetype(mono_font_path(), px)
        else:
            face = ImageFont.truetype(str(FONT_DIR / "Inter.ttf"), px)
            face.set_variation_by_axes([opsz, float(weight)])
        _FONT_CACHE[key] = face
    return _FONT_CACHE[key]


# ── diagram colours ──────────────────────────────────────────────────────────
# Diagram SVG names colours with tokens, not hex, so one drawing works on every
# theme and on both plates.
_SVG_TOKEN = re.compile(r"#(ACCENT|INK)\b", re.IGNORECASE)


def paint_svg(svg: str, accent: str, ink: str) -> str:
    """Swap the #ACCENT and #INK tokens for this render's colours."""
    return _SVG_TOKEN.sub(
        lambda m: accent if m.group(1).upper() == "ACCENT" else ink, svg)


# ── specs ────────────────────────────────────────────────────────────────────

DEFAULTS = dict(
    eyebrow="", headline="", accent="", subhead="", kicker="",
    surface="dark", theme=DEFAULT_THEME, accent_hex="",
    display="inter", art="none",
    art_svg="", art_code=None, photo="", art_img="", fit_viewbox=True,
)

def clashes_with_lockup(hex_colour: str) -> bool:
    """True when an accent sits too near BRAND_CYAN to be told apart from it."""
    if hex_colour.upper() in (BRAND_CYAN, BRAND_CYAN_DARK):
        return False       # the mark's own colour, deliberately
    hue, saturation, _ = _hsv(hex_colour)
    if saturation < NEUTRAL_SATURATION:
        return False
    gap = abs(hue - _hsv(BRAND_CYAN)[0]) * 360
    return min(gap, 360 - gap) < MIN_HUE_GAP


def load_spec(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    if not spec.get("headline"):
        raise ValueError("spec is missing required field: headline")
    if not spec.get("slug"):
        raise ValueError("spec is missing required field: slug")
    if surface_name(spec.get("surface")) not in SURFACES:
        raise ValueError(f"unknown surface: {spec.get('surface')!r}")
    if spec.get("theme") not in (None, *THEMES):
        raise ValueError(f"unknown theme: {spec.get('theme')!r}; "
                         f"expected one of {', '.join(THEMES)}")
    if spec.get("art") not in (None, "none", "diagram", "code", "photo"):
        raise ValueError(f"unknown art mode: {spec.get('art')!r}")
    if spec.get("accent_hex"):
        try:
            ImageColor.getrgb(spec["accent_hex"])
        except ValueError:
            raise ValueError(f"accent_hex is not a colour: {spec['accent_hex']!r}")
        if clashes_with_lockup(spec["accent_hex"]):
            raise ValueError(
                f"accent_hex {spec['accent_hex']} sits within {MIN_HUE_GAP:.0f} "
                f"degrees of the lockup's {BRAND_CYAN}, so the '.AI' would read "
                f"as a failed colour match. Pick a further hue, or theme "
                f"'signal' to use the brand cyan itself.")
    # Image paths resolve relative to the spec file as well as the cwd.
    spec["_base"] = str(Path(path).resolve().parent)
    return spec


def _resolve_image(value: str, base: str | None, field: str) -> str:
    """Absolute path to an image the spec points at, or a clear error."""
    p = Path(value).expanduser()
    if not p.is_absolute():
        for root in (Path.cwd(), Path(base) if base else None):
            if root and (root / p).exists():
                p = root / p
                break
    p = p.resolve()
    if not p.is_file():
        raise ValueError(
            f"{field} points at {value!r}, which is not a file. Paths are read "
            f"relative to the working directory, then to the spec's own folder.")
    return str(p)


def resolve(spec: dict, canvas: str) -> dict:
    """Merge defaults, the spec, and any per-canvas override into one payload."""
    if canvas not in CANVASES:
        raise KeyError(f"unknown canvas {canvas!r}; expected one of {list(CANVASES)}")
    c = CANVASES[canvas]
    p = copy.deepcopy(DEFAULTS)
    # `_`-prefixed keys are loader bookkeeping, not payload; render.py
    # serialises this dict to JSON for the browser.
    p.update({k: v for k, v in spec.items()
              if k != "overrides" and not k.startswith("_")})
    p.update(spec.get("overrides", {}).get(canvas, {}))

    ts = type_scale(c["w"], c["layout"])

    # No artwork on a stack canvas: let the headline use the room.
    has_art = (
        (p["art"] == "diagram" and p["art_svg"])
        or (p["art"] == "code" and p["art_code"])
        or (p["art"] == "photo" and p["art_img"])
    )
    if not has_art:
        p["art"] = "none"
        if c["layout"] == "stack":
            ts["fs_headline_max"] = round(ts["fs_headline_max"] * 1.28, 2)
            ts["fs_headline_min"] = round(ts["fs_headline_min"] * 1.15, 2)

    p["surface"] = surface_name(p["surface"])
    s = SURFACES[p["surface"]]
    theme = THEMES[p["theme"]]

    # Paper takes the deeper of the theme's two accents.
    if p["accent_hex"]:
        accent = p["accent_hex"]
    elif theme["accent"]:
        accent = theme["accent"][1 if s["light_plate"] else 0]
    else:
        accent = s["fg"]            # `mono`: the ink does the accent's job

    # Secondary type follows the theme's hue on a dark plate, so a warm theme
    # does not carry a cool grey subhead.
    c_subhead, c_kicker = s["subhead"], s["kicker"]
    if not s["light_plate"]:
        c_subhead = retint(c_subhead, accent)
        c_kicker = retint(c_kicker, accent)

    p.update(
        canvas=canvas, w=c["w"], h=c["h"], layout=c["layout"],
        inset_x=c["inset_x"], inset_y=c["inset_y"],
        text_frac=text_frac(c["layout"], has_art),
        stack_art_frac=STACK_ART_FRAC,
        out_name=c["out"].format(slug=spec["slug"]),
        c_fg=s["fg"], c_subhead=c_subhead, c_kicker=c_kicker, c_rule=s["rule"],
        logo_top=s["logo_top"], c_code_fg=s["code_fg"], c_code_panel=s["code_panel"],
        c_code_edge=s["code_edge"], c_code_label=s["code_label"],
        c_accent=accent, c_logo_j33=s["fg"], c_logo_ai=BRAND_CYAN,
        c_paper=theme["light"],
        c_dark_from=theme["dark"][0], c_dark_to=theme["dark"][1],
        c_glow=(*ImageColor.getrgb(accent)[:3], 40),
        c_photo_tint=(*ImageColor.getrgb(theme["dark"][0])[:3], 46),
    )
    if p["art"] == "diagram" and p["art_svg"]:
        p["art_svg"] = paint_svg(p["art_svg"], accent, s["fg"])
    p.update(ts)
    if p["surface"] == "photo" and not p.get("photo"):
        raise ValueError("surface 'photo' requires a 'photo' path in the spec")
    # A bad image path fails here, not as a blank hole in the render.
    base = spec.get("_base")
    if p.get("photo"):
        p["photo"] = _resolve_image(p["photo"], base, "photo")
    if p["art"] == "photo":
        p["art_img"] = _resolve_image(p["art_img"], base, "art_img")
    return p

"""Rasterise the skill's SVG subset with Pillow, no native libraries.

cairosvg is not used: it needs a libcairo that has no Windows wheel, and it
cannot see assets/fonts/, so labels would come out in a substituted face.

Covered, as documented in references/layouts.md:

    svg · g · defs/marker · rect · circle · ellipse · line
    polyline · polygon · path · text/tspan

with `transform`, `stroke-dasharray`, presentation attributes (inherited and
via `style="..."`), and `marker-start`/`marker-end` arrowheads. Labels are set
in the bundled Inter. Anything else is skipped and named in the warnings.

Geometry is collected in user units and fitted to the target box at the end,
which is what lets the viewBox be tightened to the drawn bounds, as the
template does with getBBox().
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageColor, ImageDraw

import profiles

SS = 2  # supersample factor, as in compose.py

# ── small parsers ────────────────────────────────────────────────────────────

_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_FUNC = re.compile(r"([A-Za-z]+)\s*\(([^)]*)\)")
_URL = re.compile(r"url\(\s*#([^)\s]+)\s*\)")

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

INHERITED = (
    "fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-opacity",
    "fill-opacity", "opacity", "font-family", "font-size", "font-weight",
    "font-style", "text-anchor", "marker-start", "marker-end", "color",
)

DRAWABLE = {"rect", "circle", "ellipse", "line", "polyline", "polygon",
            "path", "text"}
CONTAINER = {"svg", "g", "a", "switch"}
IGNORED = {"defs", "marker", "title", "desc", "metadata", "style", "tspan"}


def _nums(s: str) -> list[float]:
    return [float(x) for x in _NUM.findall(s or "")]


def _f(v, default: float = 0.0) -> float:
    """A length in px; other units are outside the subset."""
    if v is None:
        return default
    m = _NUM.match(str(v).strip())
    return float(m.group()) if m else default


def _color(v, current: str | None = None):
    """-> (r, g, b) or None for `none`/unparseable."""
    if v is None:
        return None
    v = str(v).strip()
    if not v or v in ("none", "transparent"):
        return None
    if v == "currentColor":
        return _color(current) if current else None
    # Pillow parses #rgb, #rrggbb, rgb(), rgba() and the CSS colour names.
    try:
        return ImageColor.getrgb(v)[:3]
    except ValueError:
        return None


# ── affine transforms ────────────────────────────────────────────────────────
# SVG's (a b c d e f):  x' = a*x + c*y + e   y' = b*x + d*y + f

def _mul(p, c):
    """Compose so that a point is transformed by `c` first, then `p`."""
    a1, b1, c1, d1, e1, f1 = p
    a2, b2, c2, d2, e2, f2 = c
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def _apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _scale_of(m) -> float:
    """Uniform scale a matrix implies — used for stroke and font size."""
    a, b, c, d = m[:4]
    return math.sqrt(abs(a * d - b * c)) or 1.0


def _transform(s: str):
    m = IDENT
    for name, arg in _FUNC.findall(s or ""):
        v = _nums(arg)
        name = name.lower()
        if name == "translate" and v:
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale" and v:
            sx = v[0]
            t = (sx, 0, 0, v[1] if len(v) > 1 else sx, 0, 0)
        elif name == "rotate" and v:
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) >= 3:
                t = _mul((1, 0, 0, 1, v[1], v[2]),
                         _mul(t, (1, 0, 0, 1, -v[1], -v[2])))
        elif name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "skewx" and v:
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewy" and v:
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = _mul(m, t)
    return m


# ── path data ────────────────────────────────────────────────────────────────

_TOK = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|"
                  r"([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)")

CURVE_STEPS = 18


def _cubic(p0, p1, p2, p3, n=CURVE_STEPS):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((
            u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
        ))
    return out


def _quad(p0, p1, p2, n=CURVE_STEPS):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def _arc(p0, rx, ry, rot, large, sweep, p1, n=CURVE_STEPS * 2):
    """Endpoint-parameterised elliptical arc, flattened. Per SVG F.6.5."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(rot)
    cs, sn = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2.0, (p0[1] - p1[1]) / 2.0
    x1, y1 = cs * dx + sn * dy, -sn * dx + cs * dy

    lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
    if lam > 1:
        k = math.sqrt(lam)
        rx, ry = rx * k, ry * k

    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1 / ry, -co * ry * x1 / rx
    cx = cs * cxp - sn * cyp + (p0[0] + p1[0]) / 2.0
    cy = sn * cxp + cs * cyp + (p0[1] + p1[1]) / 2.0

    def ang(ux, uy, vx, vy):
        d = math.hypot(ux, uy) * math.hypot(vx, vy)
        if d == 0:
            return 0.0
        c = max(-1.0, min(1.0, (ux * vx + uy * vy) / d))
        a = math.acos(c)
        return -a if ux * vy - uy * vx < 0 else a

    t1 = ang(1, 0, (x1 - cxp) / rx, (y1 - cyp) / ry)
    dt = ang((x1 - cxp) / rx, (y1 - cyp) / ry, (-x1 - cxp) / rx, (-y1 - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi

    out = []
    for i in range(1, n + 1):
        t = t1 + dt * i / n
        px, py = rx * math.cos(t), ry * math.sin(t)
        out.append((cs * px - sn * py + cx, sn * px + cs * py + cy))
    return out


def _subpaths(d: str):
    """Path data -> [(points, closed)], curves flattened to polylines."""
    toks = [(c, n) for c, n in _TOK.findall(d or "")]
    i, n_tok = 0, len(toks)
    subs, cur = [], []
    start = (0.0, 0.0)
    pos = (0.0, 0.0)
    cmd = None
    prev_c2 = None   # for S
    prev_q1 = None   # for T

    def take(k):
        nonlocal i
        vals = []
        while len(vals) < k and i < n_tok and toks[i][0] == "":
            vals.append(float(toks[i][1]))
            i += 1
        return vals if len(vals) == k else None

    def flush(closed=False):
        nonlocal cur
        if len(cur) > 1:
            subs.append((cur, closed))
        cur = []

    while i < n_tok:
        if toks[i][0]:
            cmd = toks[i][0]
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append(start)
                flush(True)
                pos = start
                continue
        if cmd is None:
            i += 1
            continue

        rel = cmd.islower()
        c = cmd.upper()

        if c == "M":
            v = take(2)
            if v is None:
                break
            flush()
            pos = (pos[0] + v[0], pos[1] + v[1]) if rel else (v[0], v[1])
            start = pos
            cur = [pos]
            cmd = "l" if rel else "L"      # implicit lineto for extra pairs
            prev_c2 = prev_q1 = None
            continue

        if not cur:
            cur = [pos]

        if c == "L":
            v = take(2)
            if v is None:
                break
            pos = (pos[0] + v[0], pos[1] + v[1]) if rel else (v[0], v[1])
            cur.append(pos)
            prev_c2 = prev_q1 = None
        elif c == "H":
            v = take(1)
            if v is None:
                break
            pos = (pos[0] + v[0], pos[1]) if rel else (v[0], pos[1])
            cur.append(pos)
            prev_c2 = prev_q1 = None
        elif c == "V":
            v = take(1)
            if v is None:
                break
            pos = (pos[0], pos[1] + v[0]) if rel else (pos[0], v[0])
            cur.append(pos)
            prev_c2 = prev_q1 = None
        elif c in ("C", "S"):
            v = take(4 if c == "S" else 6)
            if v is None:
                break
            if rel:
                v = [v[k] + (pos[0] if k % 2 == 0 else pos[1]) for k in range(len(v))]
            if c == "S":
                p1 = (2 * pos[0] - prev_c2[0], 2 * pos[1] - prev_c2[1]) if prev_c2 else pos
                p2, p3 = (v[0], v[1]), (v[2], v[3])
            else:
                p1, p2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            cur.extend(_cubic(pos, p1, p2, p3))
            prev_c2, prev_q1, pos = p2, None, p3
        elif c in ("Q", "T"):
            v = take(2 if c == "T" else 4)
            if v is None:
                break
            if rel:
                v = [v[k] + (pos[0] if k % 2 == 0 else pos[1]) for k in range(len(v))]
            if c == "T":
                p1 = (2 * pos[0] - prev_q1[0], 2 * pos[1] - prev_q1[1]) if prev_q1 else pos
                p2 = (v[0], v[1])
            else:
                p1, p2 = (v[0], v[1]), (v[2], v[3])
            cur.extend(_quad(pos, p1, p2))
            prev_q1, prev_c2, pos = p1, None, p2
        elif c == "A":
            v = take(7)
            if v is None:
                break
            end = (pos[0] + v[5], pos[1] + v[6]) if rel else (v[5], v[6])
            cur.extend(_arc(pos, v[0], v[1], v[2], int(v[3]) != 0, int(v[4]) != 0, end))
            prev_c2 = prev_q1 = None
            pos = end
        else:
            i += 1

    flush()
    return subs


# ── shapes -> polylines ──────────────────────────────────────────────────────

def _ellipse_pts(cx, cy, rx, ry, n=64):
    return [(cx + rx * math.cos(2 * math.pi * k / n),
             cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)] + [(cx + rx, cy)]


def _rrect_pts(x, y, w, h, rx, ry, n=10):
    if rx <= 0 and ry <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    rx = min(rx or ry, w / 2.0)
    ry = min(ry or rx, h / 2.0)
    pts = []
    # (centre, start angle) for each corner, clockwise from top-left
    corners = [((x + rx, y + ry), math.pi),
               ((x + w - rx, y + ry), 1.5 * math.pi),
               ((x + w - rx, y + h - ry), 0.0),
               ((x + rx, y + h - ry), 0.5 * math.pi)]
    for (ccx, ccy), a0 in corners:
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((ccx + rx * math.cos(a), ccy + ry * math.sin(a)))
    pts.append(pts[0])
    return pts


# ── fonts ────────────────────────────────────────────────────────────────────

def _font(style: dict, size: float):
    """The face a <text> element's style asks for, from profiles.font()."""
    family = "mono" if _is_mono(style.get("font-family")) else "inter"
    return profiles.font(size, _weight(style.get("font-weight")), family=family)


def _weight(v) -> int:
    if v is None:
        return 400
    v = str(v).strip().lower()
    if v.isdigit():
        return max(100, min(900, int(v)))
    return {"normal": 400, "bold": 700, "bolder": 800, "lighter": 300}.get(v, 400)


def _is_mono(family: str | None) -> bool:
    f = (family or "").lower()
    return "mono" in f or "consol" in f or "courier" in f


# ── dashes ───────────────────────────────────────────────────────────────────

def _dashed(pts, pattern):
    """Split a polyline into the 'on' runs of a stroke-dasharray."""
    pattern = [p for p in pattern if p >= 0]
    if not pattern or all(p == 0 for p in pattern):
        return [pts]
    if len(pattern) % 2:
        pattern = pattern * 2
    runs, cur = [], [pts[0]]
    idx, left, on = 0, pattern[0], True
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        t0 = 0.0
        while seg - t0 > 1e-9:
            step = min(left, seg - t0)
            t1 = t0 + step
            p1 = (a[0] + (b[0] - a[0]) * t1 / seg, a[1] + (b[1] - a[1]) * t1 / seg)
            if on:
                cur.append(p1)
            left -= step
            t0 = t1
            if left <= 1e-9:
                if on and len(cur) > 1:
                    runs.append(cur)
                on = not on
                cur = [p1] if on else []
                idx = (idx + 1) % len(pattern)
                left = pattern[idx]
                if left <= 0:      # a zero-length entry would spin forever
                    left = 1e-6
    if on and len(cur) > 1:
        runs.append(cur)
    return runs


# ── the collector ────────────────────────────────────────────────────────────

def _tag(el) -> str:
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def _style_of(el, inherited: dict) -> dict:
    st = dict(inherited)
    for k in INHERITED:
        v = el.get(k)
        if v is not None:
            st[k] = v
    inline = el.get("style")
    if inline:
        for decl in inline.split(";"):
            if ":" in decl:
                k, _, v = decl.partition(":")
                k = k.strip()
                if k in INHERITED:
                    st[k] = v.strip()
    return st


def _collect(el, matrix, style, items, warnings, depth=0):
    if depth > 40:
        return
    tag = _tag(el)
    if tag in IGNORED:
        return

    matrix = _mul(matrix, _transform(el.get("transform", "")))
    style = _style_of(el, style)

    if tag in CONTAINER:
        for child in el:
            _collect(child, matrix, style, items, warnings, depth + 1)
        return

    if tag not in DRAWABLE:
        if tag:
            warnings.append(f"<{tag}> is outside the supported SVG subset and was skipped")
        return

    if tag == "text":
        parts = [el.text or ""]
        for child in el:
            if _tag(child) == "tspan":
                parts.append(child.text or "")
            parts.append(child.tail or "")
        text = "".join(parts).strip()
        if text:
            items.append(dict(kind="text", m=matrix, style=style, text=text,
                              x=_f(el.get("x"), 0.0), y=_f(el.get("y"), 0.0)))
        return

    if tag == "rect":
        w, h = _f(el.get("width")), _f(el.get("height"))
        if w <= 0 or h <= 0:
            return
        rx, ry = el.get("rx"), el.get("ry")
        rxv = _f(rx, _f(ry, 0.0))
        ryv = _f(ry, rxv)
        subs = [(_rrect_pts(_f(el.get("x")), _f(el.get("y")), w, h, rxv, ryv), True)]
    elif tag == "circle":
        r = _f(el.get("r"))
        if r <= 0:
            return
        subs = [(_ellipse_pts(_f(el.get("cx")), _f(el.get("cy")), r, r), True)]
    elif tag == "ellipse":
        rx, ry = _f(el.get("rx")), _f(el.get("ry"))
        if rx <= 0 or ry <= 0:
            return
        subs = [(_ellipse_pts(_f(el.get("cx")), _f(el.get("cy")), rx, ry), True)]
    elif tag == "line":
        subs = [([(_f(el.get("x1")), _f(el.get("y1"))),
                  (_f(el.get("x2")), _f(el.get("y2")))], False)]
    elif tag in ("polyline", "polygon"):
        v = _nums(el.get("points", ""))
        pts = list(zip(v[0::2], v[1::2]))
        if len(pts) < 2:
            return
        closed = tag == "polygon"
        if closed:
            pts = pts + [pts[0]]
        subs = [(pts, closed)]
    else:  # path
        subs = _subpaths(el.get("d", ""))

    for pts, closed in subs:
        if len(pts) < 2:
            continue
        items.append(dict(kind="poly", m=matrix, style=style,
                          pts=[_apply(matrix, x, y) for x, y in pts],
                          closed=closed))


def _markers(root) -> dict:
    out = {}
    for m in root.iter():
        if _tag(m) != "marker":
            continue
        mid = m.get("id")
        if not mid:
            continue
        fill = None
        for child in m.iter():
            if _tag(child) in DRAWABLE:
                fill = child.get("fill") or fill
                if fill:
                    break
        out[mid] = dict(fill=fill,
                        mw=_f(m.get("markerWidth"), 3.0),
                        mh=_f(m.get("markerHeight"), 3.0))
    return out


# ── bounds and drawing ───────────────────────────────────────────────────────

def _text_metrics(it):
    st = it["style"]
    s = _scale_of(it["m"])
    size = _f(st.get("font-size"), 16.0) * s
    fnt = _font(st, size)
    w = fnt.getlength(it["text"])
    asc, desc = fnt.getmetrics()
    anchor = (st.get("text-anchor") or "start").strip()
    ax, ay = _apply(it["m"], it["x"], it["y"])
    if anchor == "middle":
        ax -= w / 2.0
    elif anchor == "end":
        ax -= w
    return fnt, ax, ay, w, asc, desc


def _bounds(items):
    xs0 = ys0 = float("inf")
    xs1 = ys1 = float("-inf")
    for it in items:
        if it["kind"] == "poly":
            sw = _f(it["style"].get("stroke-width"), 1.0) * _scale_of(it["m"]) / 2.0
            if _color(it["style"].get("stroke"), it["style"].get("color")) is None:
                sw = 0.0
            for x, y in it["pts"]:
                xs0, ys0 = min(xs0, x - sw), min(ys0, y - sw)
                xs1, ys1 = max(xs1, x + sw), max(ys1, y + sw)
        else:
            _, ax, ay, w, asc, desc = _text_metrics(it)
            xs0, ys0 = min(xs0, ax), min(ys0, ay - asc)
            xs1, ys1 = max(xs1, ax + w), max(ys1, ay + desc)
    if xs0 > xs1 or ys0 > ys1:
        return None
    return (xs0, ys0, xs1, ys1)


def _arrow(tip, prev, length, width):
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return None
    ux, uy = dx / d, dy / d
    bx, by = tip[0] - ux * length, tip[1] - uy * length
    px, py = -uy * width / 2.0, ux * width / 2.0
    return [tip, (bx + px, by + py), (bx - px, by - py)]


def _alpha(style, key) -> float:
    return max(0.0, min(1.0, _f(style.get(key), 1.0) * _f(style.get("opacity"), 1.0)))


def rasterise(svg_text: str, box_w: int, box_h: int, *, fit_viewbox: bool = True,
              current_color: str = "#FFFFFF"):
    """Render `svg_text` letterboxed into a box_w x box_h RGBA image.

    Returns (image, warnings). `image` is None only when the SVG could not be
    parsed or contained nothing drawable — the caller decides what to say.
    """
    warnings: list[str] = []
    if box_w < 2 or box_h < 2:
        return None, ["artwork box is too small to draw into"]

    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        return None, [f"art_svg is not well-formed XML: {e}"]

    items: list[dict] = []
    markers = _markers(root)
    base = dict(fill="black", stroke="none", color=current_color)
    _collect(root, IDENT, base, items, warnings)
    if not items:
        return None, warnings + ["art_svg contained nothing drawable"]

    # An unparseable colour draws nothing, which is easy to miss in a diagram.
    # Name it rather than leaving a hole where a misspelt token was.
    unparseable = set()
    for it in items:
        for key in ("fill", "stroke"):
            value = str(it["style"].get(key, "")).strip()
            if not value or value in ("none", "transparent", "currentColor"):
                continue
            if _color(value) is None:
                unparseable.add(value)
    if unparseable:
        warnings.append(f"not a colour, so nothing was drawn in it: "
                        f"{', '.join(sorted(unparseable))}. Diagram colours are "
                        f"#ACCENT, #INK, or a hex value.")

    # Fit to the drawn bounds (the template's getBBox() refit) or to the
    # declared viewBox.
    bounds = _bounds(items)
    if not fit_viewbox:
        vb = _nums(root.get("viewBox", ""))
        if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
            bounds = (vb[0], vb[1], vb[0] + vb[2], vb[1] + vb[3])
    if bounds is None:
        return None, warnings + ["art_svg has no measurable extent"]

    x0, y0, x1, y1 = bounds
    bw, bh = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
    if fit_viewbox:
        pad = max(6.0, max(bw, bh) * 0.03)
        x0, y0, bw, bh = x0 - pad, y0 - pad, bw + pad * 2, bh + pad * 2

    W, H = box_w * SS, box_h * SS
    scale = min(W / bw, H / bh)
    ox = (W - bw * scale) / 2.0 - x0 * scale
    oy = (H - bh * scale) / 2.0 - y0 * scale

    def dev(p):
        return (p[0] * scale + ox, p[1] * scale + oy)

    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    for it in items:
        st = it["style"]
        if it["kind"] == "text":
            col = _color(st.get("fill", "black"), st.get("color"))
            if col is None:
                continue
            # Load the face at device size. Anchor "s" is the alphabetic
            # baseline, which is what SVG's `y` on <text> means.
            size = _f(st.get("font-size"), 16.0) * _scale_of(it["m"]) * scale
            fnt = _font(st, size)
            anchor = {"middle": "ms", "end": "rs"}.get(
                (st.get("text-anchor") or "start").strip(), "ls")
            px, py = dev(_apply(it["m"], it["x"], it["y"]))
            a = int(round(255 * _alpha(st, "fill-opacity")))
            d.text((px, py), it["text"], font=fnt, fill=(*col, a), anchor=anchor)
            continue

        pts = [dev(p) for p in it["pts"]]
        fill = _color(st.get("fill"), st.get("color")) if it["closed"] else None
        stroke = _color(st.get("stroke"), st.get("color"))
        sw = max(1.0, _f(st.get("stroke-width"), 1.0) * _scale_of(it["m"]) * scale)

        if fill is not None and len(pts) > 2:
            d.polygon(pts, fill=(*fill, int(round(255 * _alpha(st, "fill-opacity")))))
        if stroke is None:
            continue

        sa = int(round(255 * _alpha(st, "stroke-opacity")))
        dash = _nums(st.get("stroke-dasharray", "")) if st.get("stroke-dasharray") not in (None, "none") else []
        runs = _dashed(pts, [v * _scale_of(it["m"]) * scale for v in dash]) if dash else [pts]
        for run in runs:
            if len(run) > 1:
                d.line(run, fill=(*stroke, sa), width=int(round(sw)), joint="curve")

        # Arrowheads: a triangle at the end of the connector, oriented along
        # it. Not general marker support.
        for key, tip_i, prev_i in (("marker-end", -1, -2), ("marker-start", 0, 1)):
            ref = st.get(key)
            if not ref or it["closed"]:
                continue
            mid = _URL.search(ref)
            spec = markers.get(mid.group(1)) if mid else None
            if spec is None:
                continue
            usw = _f(st.get("stroke-width"), 1.0) * _scale_of(it["m"]) * scale
            tri = _arrow(pts[tip_i], pts[prev_i], spec["mw"] * usw, spec["mh"] * usw)
            if tri:
                col = _color(spec["fill"], st.get("color")) or stroke
                d.polygon(tri, fill=(*col, sa))

    return im.resize((box_w, box_h), Image.LANCZOS), warnings

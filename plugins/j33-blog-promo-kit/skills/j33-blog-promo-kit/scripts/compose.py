"""Pillow renderer, used when Chromium is not available.

Geometry, type scales and colours come from profiles.py, so the layout matches
the Chromium path. Two known differences: the dark gradient is vertical rather
than angled, and `art: diagram` goes through svgpil.py, which renders the SVG
subset in references/layouts.md and warns about anything outside it.

Everything is drawn at 2x and resized with LANCZOS, for the same reason the
browser path renders at deviceScaleFactor 2: 1:1 type looks thin.
"""

from __future__ import annotations

import functools
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageOps

import profiles
import svgpil

SS = 2  # supersample factor


@functools.lru_cache(maxsize=2)
def _open_rgb(path: str) -> Image.Image:
    """Decode once per kit: the same photograph goes on all five canvases."""
    return Image.open(path).convert("RGB")


# ── rich-text runs, so the accent word can be tinted mid-headline ────────────

def _runs(text: str, accent: str) -> list[tuple[str, bool]]:
    """Split text into (chunk, is_accent) pairs. First match only."""
    if not accent:
        return [(text, False)]
    i = text.lower().find(accent.lower())
    if i < 0:
        return [(text, False)]
    out = []
    if i:
        out.append((text[:i], False))
    out.append((text[i:i + len(accent)], True))
    if i + len(accent) < len(text):
        out.append((text[i + len(accent):], False))
    return out


def _wrap_runs(runs, fnt, max_w, draw) -> list[list[tuple[str, bool]]]:
    """Greedy word wrap that carries the accent flag through the break."""
    words: list[tuple[str, bool, bool]] = []   # (word, accent, hard_break_after)
    for chunk, acc in runs:
        for li, line in enumerate(chunk.split("\n")):
            if li:
                if words:
                    words[-1] = (words[-1][0], words[-1][1], True)
                else:
                    words.append(("", acc, True))
            for w in line.split(" "):
                if w:
                    words.append((w, acc, False))

    lines: list[list[tuple[str, bool]]] = []
    cur: list[tuple[str, bool]] = []

    def width_of(parts):
        return draw.textlength(" ".join(p[0] for p in parts), font=fnt)

    for w, acc, brk in words:
        trial = cur + [(w, acc)]
        if cur and width_of(trial) > max_w:
            lines.append(cur)
            cur = [(w, acc)]
        else:
            cur = trial
        if brk:
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return [ln for ln in lines if ln]


def _draw_runs(draw, xy, line, fnt, base, accent_col):
    """Draw one wrapped line, switching colour per run. Returns advance width."""
    x, y = xy
    space = draw.textlength(" ", font=fnt)
    for i, (word, acc) in enumerate(line):
        if i:
            x += space
        draw.text((x, y), word, font=fnt, fill=accent_col if acc else base)
        x += draw.textlength(word, font=fnt)
    return x - xy[0]


# ── surfaces ─────────────────────────────────────────────────────────────────

def _surface(p: dict, W: int, H: int) -> tuple[Image.Image, list[str]]:
    """The background plate. Returns (image, warnings)."""
    s = p["surface"]
    warn: list[str] = []
    if s == "paper":
        im = Image.new("RGB", (W, H), p["c_paper"])
        # The grain is the plate itself, darkened, so it follows the theme.
        grain = tuple(int(v * 0.87) for v in ImageColor.getrgb(p["c_paper"])[:3])
        noise = Image.effect_noise((W, H), 14).convert("L")
        im = Image.composite(
            Image.new("RGB", (W, H), grain), im,
            noise.point(lambda v: 40 if v > 150 else 0),
        )
        return im, warn

    if s == "photo":
        try:
            base = ImageOps.fit(_open_rgb(p["photo"]), (W, H), Image.LANCZOS)
        except OSError as e:
            # The path exists (resolve() checked), so the file is undecodable.
            warn.append(f"photo could not be decoded ({e}); "
                        f"the scrim was drawn over a flat plate")
            base = Image.new("RGB", (W, H), profiles.PHOTO_DARK)
        # The scrim clears rightwards on wide/split, where the text stays in
        # the left half, and fades top-to-bottom on stack, where the headline
        # runs the full width. Same stops as the template's CSS.
        scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(scrim)
        r, g, b = ImageColor.getrgb(profiles.PHOTO_DARK)
        if p["layout"] == "stack":
            # linear-gradient(180deg, .90 -> .62)
            for y in range(H):
                t = y / max(1, H - 1)
                sd.line([(0, y), (W, y)],
                        fill=(r, g, b, int(round(255 * (0.90 - 0.28 * t)))))
        else:
            # .94 at 0, .80 at 38%, 0 at 68%, interpolated piecewise so the
            # weight matches the CSS gradient where the headline ends.
            for x in range(W):
                u = x / max(1, W - 1)
                if u <= 0.38:
                    a = 0.94 + (0.80 - 0.94) * (u / 0.38)
                elif u <= 0.68:
                    a = 0.80 * (1.0 - (u - 0.38) / 0.30)
                else:
                    a = 0.0
                sd.line([(x, 0), (x, H)], fill=(r, g, b, int(round(255 * a))))
        base = Image.alpha_composite(base.convert("RGBA"), scrim)
        tint = Image.new("RGBA", (W, H), tuple(p["c_photo_tint"]))
        return Image.alpha_composite(base, tint).convert("RGB"), warn

    # dark
    top = ImageColor.getrgb(p["c_dark_from"])
    bot = ImageColor.getrgb(p["c_dark_to"])
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / max(1, H - 1)
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    # Accent bloom, bottom right, like the CSS radial-gradient. The full glow
    # would be 1.7W x 2.0H placed at (0.30W, 0.30H); only its top-left corner
    # lands on the canvas, so build just that.
    gx, gy = int(W * 0.30), int(H * 0.30)
    vis_w, vis_h = W - gx, H - gy
    glow = (Image.radial_gradient("L")
            .crop((0, 0, round(256 * vis_w / (W * 1.7)), round(256 * vis_h / (H * 2.0))))
            .resize((vis_w, vis_h), Image.LANCZOS)
            .point(lambda v: max(0, 40 - int(v * 40 / 255))))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(Image.new("RGB", glow.size, p["c_accent"]), (gx, gy), glow)
    im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    # technical grid
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    step = W / 22
    x = 0.0
    while x < W:
        gd.line([(x, 0), (x, H)], fill=(255, 255, 255, 14)); x += step
    y = 0.0
    while y < H:
        gd.line([(0, y), (W, y)], fill=(255, 255, 255, 14)); y += step
    return Image.alpha_composite(im.convert("RGBA"), gl).convert("RGB"), warn


# ── the composer ─────────────────────────────────────────────────────────────

def render_one(spec: dict, canvas: str, out_dir: Path) -> dict:
    p = profiles.resolve(spec, canvas)
    W, H = p["w"] * SS, p["h"] * SS
    ix, iy = p["inset_x"] * SS, p["inset_y"] * SS
    gut = int(p["gutter"] * SS)

    im, warnings = _surface(p, W, H)
    draw = ImageDraw.Draw(im)
    # The rule and the code panel are translucent and drawn with alpha, so
    # they composite over whatever is underneath, photograph included.
    draw_a = ImageDraw.Draw(im, "RGBA")

    c_acc = p["c_accent"]
    c_rule = tuple(p["c_rule"])

    frame_w, frame_h = W - 2 * ix, H - 2 * iy
    text_w = int(frame_w * p["text_frac"])

    anton = p["display"] == "anton"

    def build(hsize: float):
        """Lay the text column out at a given headline size; return blocks + height."""
        blocks, y = [], 0
        if p["eyebrow"]:
            f = profiles.font(p["fs_eyebrow"] * SS, 700)
            blocks.append(("track", p["eyebrow"].upper(), f, c_acc, 0.16, y, "body"))
            y += int(p["fs_eyebrow"] * SS * 1.2 + p["u"] * SS * 1.6)

        hf = (profiles.font(hsize, family="anton") if anton
              else profiles.font(hsize, 900, 32))
        head = p["headline"].upper() if anton else p["headline"]
        lines = _wrap_runs(_runs(head, p["accent"]), hf, text_w, draw)
        lh = hsize * (1.02 if anton else 1.08)
        for ln in lines:
            blocks.append(("runs", ln, hf, p["c_fg"], 0, y, "display"))
            y += lh
        y = int(y)

        if p["subhead"]:
            f = profiles.font(p["fs_subhead"] * SS, 500)
            y += int(p["u"] * SS * 1.9)
            # matches the template's `max-width: 24em` on .subhead
            for ln in _wrap_runs([(p["subhead"], False)], f,
                                 min(text_w, int(f.size * 24)), draw):
                blocks.append(("runs", ln, f, p["c_subhead"], 0, y, "body"))
                y += int(p["fs_subhead"] * SS * 1.34)
        if p["kicker"]:
            y += int(p["u"] * SS * 2.6)
            blocks.append(("rule", None, None, c_rule, text_w, y, None))
            y += int(p["u"] * SS * 1.5)
            f = profiles.font(p["fs_kicker"] * SS, 700)
            blocks.append(("track", p["kicker"].upper(), f, p["c_kicker"], 0.10, y, "body"))
            y += int(p["fs_kicker"] * SS * 1.2)
        return blocks, y

    logo_f = profiles.font(p["fs_logo"] * SS, 800, 32)
    logo_h = int(p["fs_logo"] * SS * 1.0)
    logo_gap = int(p["u"] * SS * (3.4 if p["logo_top"] else 3.0))

    # The artwork box: a band below the text in `stack`, the column right of
    # it in `wide`/`split`. The text's vertical budget is the frame minus that
    # band and its gutter.
    if p["layout"] == "stack":
        art_w, art_h = frame_w, int(frame_h * p["stack_art_frac"])
        art_x, art_y = ix, iy + frame_h - art_h
    else:
        art_w, art_h = frame_w - text_w - gut, frame_h
        art_x, art_y = ix + text_w + gut, iy
    reserved = art_h + gut if p["layout"] == "stack" and p["art"] != "none" else 0

    size = p["fs_headline_max"] * SS
    floor = p["fs_headline_min"] * SS
    blocks, th = build(size)
    while th + logo_h + logo_gap + reserved > frame_h and size > floor:
        size -= SS
        blocks, th = build(size)
    if size <= floor:
        warnings.append("headline floored - cut words rather than lowering the floor")

    total_h = th + logo_h + logo_gap
    y0 = iy + max(0, (frame_h - total_h - reserved) // 2)
    x0 = ix

    logo_w = (draw.textlength("J33", font=logo_f)
              + draw.textlength(".AI", font=logo_f))

    def logo_at(y):
        # Never themed: the lockup is the mark, not an accent.
        x = x0
        draw.text((x, y), "J33", font=logo_f, fill=p["c_logo_j33"])
        x += draw.textlength("J33", font=logo_f)
        draw.text((x, y), ".AI", font=logo_f, fill=p["c_logo_ai"])

    # The union of the glyphs, for the manifest. verify.py samples the
    # background under these boxes rather than under the whole text column,
    # and holds display type and small text to different contrast bars.
    ink = {"display": [10 ** 9, 10 ** 9, -10 ** 9, -10 ** 9],
           "body": [10 ** 9, 10 ** 9, -10 ** 9, -10 ** 9]}

    def seen(cls, x, y, w, h):
        if cls not in ink:
            return
        b = ink[cls]
        b[0], b[1] = min(b[0], x), min(b[1], y)
        b[2], b[3] = max(b[2], x + w), max(b[3], y + h)

    y = y0
    if p["logo_top"]:
        logo_at(y)
        seen("display", x0, y, logo_w, logo_h)
        y += logo_h + logo_gap

    base_y = y
    for kind, payload, f, col, extra, oy, cls in blocks:
        yy = base_y + oy
        if kind == "runs":
            w = _draw_runs(draw, (x0, yy), payload, f, col, c_acc)
            seen(cls, x0, yy, w, f.size)
        elif kind == "track":
            x = x0
            tr = f.size * extra
            for ch in payload:
                draw.text((x, yy), ch, font=f, fill=col)
                x += draw.textlength(ch, font=f) + tr
            seen(cls, x0, yy, x - x0, f.size)
        elif kind == "rule":
            # Not counted as ink: it spans the column by design and is a
            # hairline at 22%.
            h = max(2 * SS, int(p["u"] * SS * 0.22))
            draw_a.rectangle([x0, yy, x0 + extra, yy + h], fill=col)

    if not p["logo_top"]:
        ly = base_y + th + logo_gap
        logo_at(ly)
        seen("display", x0, ly, logo_w, logo_h)

    # ── artwork ──────────────────────────────────────────────────────────────
    if p["art"] == "diagram":
        art, svg_warnings = svgpil.rasterise(
            p["art_svg"], art_w, art_h,
            fit_viewbox=p["fit_viewbox"], current_color=p["c_fg"],
        )
        warnings.extend(dict.fromkeys(svg_warnings))
        if art is not None:
            im.paste(art, (art_x, art_y), art)
    elif p["art"] == "photo":
        try:
            ph = _open_rgb(p["art_img"])
        except OSError as e:
            warnings.append(f"art_img could not be opened: {e}")
        else:
            # the template's `max-width:100%; max-height:100%` on an <img>
            ph = ImageOps.contain(ph, (art_w, art_h), Image.LANCZOS)
            im.paste(ph, (art_x + (art_w - ph.width) // 2,
                          art_y + (art_h - ph.height) // 2))
    elif p["art"] == "code":
        warnings.extend(_draw_code(im, draw_a, p, (art_x, art_y, art_w, art_h)))

    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / p["out_name"]
    im.resize((p["w"], p["h"]), Image.LANCZOS).save(final, "PNG")
    text_box = {k: ([int(round(v / SS)) for v in b]
                    if b[2] > b[0] and b[3] > b[1] else None)
                for k, b in ink.items()}
    return dict(canvas=canvas, path=final, w=p["w"], h=p["h"],
                headline_px=round(size / SS, 2), floored=size <= floor,
                warnings=warnings, text_box=text_box, payload=p)


def _draw_code(im, draw_a, p, box) -> list[str]:
    """Draw the code panel inside `box` = (x, y, w, h). Returns warnings."""
    warn: list[str] = []
    c = p["art_code"]
    lines = c.get("lines", [])
    if not lines:
        return warn
    bx, by, bw, bh = box

    fs = p["fs_code"] * SS
    mono = profiles.font(fs, 500, family="mono")
    if profiles.mono_font_path() is None:
        # Inter is proportional; code set in it stops looking like code.
        warn.append("no monospace font on this machine, so `art: code` was set "
                    "in Inter. Install DejaVu Sans Mono, or use art: diagram.")

    pad = int(p["u"] * SS * 2.5)
    lh = fs * 1.62
    box_h = min(bh, int(len(lines) * lh + pad * 2 + (fs * 2 if c.get("lang") else 0)))
    box_y = by + (bh - box_h) // 2
    draw_a.rounded_rectangle([bx, box_y, bx + bw, box_y + box_h],
                             radius=int(p["u"] * SS * 1.1),
                             fill=tuple(p["c_code_panel"]),
                             outline=tuple(p["c_code_edge"]), width=2 * SS)

    d = ImageDraw.Draw(im)
    y = box_y + pad
    if c.get("lang"):
        lf = profiles.font(p["fs_kicker"] * SS, 700)
        d.text((bx + pad, y), c["lang"].upper(), font=lf, fill=tuple(p["c_code_label"]))
        y += int(fs * 2)
    hl = set(c.get("highlight", []))
    for i, ln in enumerate(lines):
        d.text((bx + pad, y), ln, font=mono,
               fill=p["c_accent"] if i in hl else p["c_code_fg"])
        y += lh
    return warn


def render_all(spec: dict, out_dir: Path, canvases: list[str]) -> list[dict]:
    return [render_one(spec, c, out_dir) for c in canvases]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Render posters with Pillow (no browser).")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--canvas", action="append", default=None)
    a = ap.parse_args()

    spec = profiles.load_spec(a.spec)
    for r in render_all(spec, Path(a.out), a.canvas or profiles.ORDER):
        print(f"{r['canvas']:<10} {r['w']}x{r['h']}  {r['path'].name}")
        for w in r["warnings"]:
            print(f"           ! {w}")

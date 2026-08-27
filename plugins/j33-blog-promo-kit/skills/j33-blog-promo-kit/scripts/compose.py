"""Pillow renderer — the no-browser path.

Used when Playwright/Chromium is not available (notably ChatGPT's sandbox).
Geometry and type scales come from profiles.py, so this agrees with the
Chromium path on layout. Two honest differences:

  * the navy surface uses a vertical gradient rather than a 152 degree one
  * `art: diagram` needs cairosvg; without it the artwork is dropped and the
    caller is told, rather than silently producing a different picture

Everything is drawn at 2x and resized with LANCZOS, for the same reason the
browser path renders at deviceScaleFactor 2.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import profiles

SS = 2  # supersample factor

_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def font(size: float, weight: int = 400, opsz: float = 14.0,
         family: str = "inter") -> ImageFont.FreeTypeFont:
    key = (round(size, 1), weight, opsz, family)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if family == "anton":
        f = ImageFont.truetype(str(profiles.FONT_DIR / "Anton-Regular.ttf"), int(round(size)))
    else:
        f = ImageFont.truetype(str(profiles.FONT_DIR / "Inter.ttf"), int(round(size)))
        try:
            f.set_variation_by_axes([opsz, float(weight)])
        except Exception:
            pass  # static build; weight will just be Regular
    _FONT_CACHE[key] = f
    return f


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

def _surface(p: dict, W: int, H: int) -> Image.Image:
    s = p["surface"]
    if s == "paper":
        im = Image.new("RGB", (W, H), _hex(profiles.PAPER))
        noise = Image.effect_noise((W, H), 14).convert("L")
        im = Image.composite(
            Image.new("RGB", (W, H), (214, 205, 186)), im,
            noise.point(lambda v: 40 if v > 150 else 0),
        )
        return im

    if s == "photo":
        base = Image.new("RGB", (W, H), _hex(profiles.PHOTO_DARK))
        try:
            ph = Image.open(p["photo"]).convert("RGB")
            sc = max(W / ph.width, H / ph.height)
            ph = ph.resize((max(1, int(ph.width * sc)), max(1, int(ph.height * sc))),
                           Image.LANCZOS)
            base.paste(ph, ((W - ph.width) // 2, (H - ph.height) // 2))
        except Exception:
            pass
        # scrim: opaque on the text side, clearing across
        scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(scrim)
        r, g, b = _hex(profiles.PHOTO_DARK)
        for x in range(W):
            t = min(1.0, x / (W * 0.68))
            sd.line([(x, 0), (x, H)], fill=(r, g, b, int(240 * (1 - t) ** 1.25)))
        base = Image.alpha_composite(base.convert("RGBA"), scrim)
        tint = Image.new("RGBA", (W, H), (*_hex(profiles.NAVY), 46))
        return Image.alpha_composite(base, tint).convert("RGB")

    # navy
    top, bot = _hex(profiles.NAVY), _hex(profiles.NAVY_LIGHT)
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / max(1, H - 1)
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    # cyan bloom, bottom right — same gesture as the CSS radial-gradient
    glow = Image.radial_gradient("L").resize((int(W * 1.7), int(H * 2.0)), Image.LANCZOS)
    glow = glow.point(lambda v: max(0, 40 - int(v * 40 / 255)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(Image.new("RGB", glow.size, _hex(profiles.PRIMARY)),
                (int(W * 0.30), int(H * 0.30)), glow)
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
    return Image.alpha_composite(im.convert("RGBA"), gl).convert("RGB")


def _rasterise_svg(svg: str, box_w: int, box_h: int):
    try:
        import cairosvg
    except Exception:
        return None
    try:
        import io
        png = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                               output_width=box_w, output_height=box_h)
        return Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:
        return None


# ── the composer ─────────────────────────────────────────────────────────────

def render_one(spec: dict, canvas: str, out_dir: Path) -> dict:
    p = profiles.resolve(spec, canvas)
    W, H = p["w"] * SS, p["h"] * SS
    ix, iy = p["inset_x"] * SS, p["inset_y"] * SS
    gut = p["gutter"] * SS

    im = _surface(p, W, H)
    draw = ImageDraw.Draw(im)

    dark = p["surface"] != "paper"
    c_head = (255, 255, 255) if dark else _hex(profiles.NAVY)
    c_sub = _hex(profiles.BODY_LIGHT) if dark else (74, 74, 85)
    c_kick = _hex(profiles.BODY_LIGHT) if dark else _hex(profiles.NAVY)
    c_logo = (255, 255, 255) if dark else _hex(profiles.NAVY)
    c_acc = _hex(profiles.PRIMARY)
    # Pre-blend the rule rather than compositing a layer: it sits on a known
    # surface colour, so a flat RGB is exact and far simpler.
    if dark:
        bg = _hex(profiles.NAVY_LIGHT)
        c_rule = tuple(int(bg[i] + (255 - bg[i]) * 0.22) for i in range(3))
    else:
        c_rule = _hex(profiles.NAVY)

    frame_w, frame_h = W - 2 * ix, H - 2 * iy
    text_w = int(frame_w * (0.46 if p["layout"] == "wide"
                            else 0.52 if p["layout"] == "split" else 1.0))
    if p["art"] == "none" or (p["art"] == "diagram" and not p["art_svg"]):
        text_w = frame_w if p["layout"] == "stack" else int(frame_w * 0.78)

    anton = p.get("display") == "anton"
    warnings: list[str] = []

    def build(hsize: float):
        """Lay the text column out at a given headline size; return blocks + height."""
        blocks, y = [], 0
        if p["eyebrow"]:
            f = font(p["fs_eyebrow"] * SS, 700, 14)
            blocks.append(("track", p["eyebrow"].upper(), f,
                           c_acc if dark else c_acc, 0.16, y))
            y += int(p["fs_eyebrow"] * SS * 1.2 + p["u"] * SS * 1.6)

        hf = (font(hsize, 400, 32, "anton") if anton
              else font(hsize, 900, 32))
        head = p["headline"].upper() if anton else p["headline"]
        lines = _wrap_runs(_runs(head, p["accent"]), hf, text_w, draw)
        lh = hsize * (1.02 if anton else 1.08)
        for ln in lines:
            blocks.append(("runs", ln, hf, c_head, 0, y))
            y += lh
        y = int(y)

        if p["subhead"]:
            f = font(p["fs_subhead"] * SS, 500, 14)
            y += int(p["u"] * SS * 1.9)
            # matches the template's `max-width: 24em` on .subhead
            for ln in _wrap_runs([(p["subhead"], False)], f,
                                 min(text_w, int(f.size * 24)), draw):
                blocks.append(("runs", ln, f, c_sub, 0, y))
                y += int(p["fs_subhead"] * SS * 1.34)
        if p["kicker"]:
            y += int(p["u"] * SS * 2.6)
            blocks.append(("rule", None, None, c_rule, text_w, y))
            y += int(p["u"] * SS * 1.5)
            f = font(p["fs_kicker"] * SS, 700, 14)
            blocks.append(("track", p["kicker"].upper(), f, c_kick, 0.10, y))
            y += int(p["fs_kicker"] * SS * 1.2)
        return blocks, y

    logo_f = font(p["fs_logo"] * SS, 800, 32)
    logo_h = int(p["fs_logo"] * SS * 1.0)
    logo_gap = int(p["u"] * SS * (3.4 if dark else 3.0))

    art_h = 0
    if p["layout"] == "stack" and p["art"] != "none":
        art_h = int(max(frame_h * 0.36, 0)) + int(gut)

    size = p["fs_headline_max"] * SS
    floor = p["fs_headline_min"] * SS
    blocks, th = build(size)
    while th + logo_h + logo_gap + art_h > frame_h and size > floor:
        size -= SS
        blocks, th = build(size)
    if size <= floor:
        warnings.append("headline floored - cut words rather than lowering the floor")

    total_h = th + logo_h + logo_gap
    if p["layout"] == "stack":
        y0 = iy + max(0, (frame_h - total_h - art_h) // 2)
    else:
        y0 = iy + max(0, (frame_h - total_h) // 2)
    x0 = ix

    def logo_at(y):
        x = x0
        draw.text((x, y), "J33", font=logo_f, fill=c_logo)
        x += draw.textlength("J33", font=logo_f)
        draw.text((x, y), ".AI", font=logo_f, fill=c_acc)

    y = y0
    if dark:
        logo_at(y)
        y += logo_h + logo_gap

    base_y = y
    for kind, payload, f, col, extra, oy in blocks:
        yy = base_y + oy
        if kind == "runs":
            _draw_runs(draw, (x0, yy), payload, f, col, c_acc)
        elif kind == "track":
            x = x0
            tr = f.size * extra
            for ch in payload:
                draw.text((x, yy), ch, font=f, fill=col)
                x += draw.textlength(ch, font=f) + tr
        elif kind == "rule":
            h = max(2 * SS, int(p["u"] * SS * 0.22))
            draw.rectangle([x0, yy, x0 + extra, yy + h], fill=col)

    if not dark:
        logo_at(base_y + th + logo_gap)

    # ── artwork ──────────────────────────────────────────────────────────────
    if p["art"] == "diagram" and p["art_svg"]:
        if p["layout"] == "stack":
            bw, bh = frame_w, max(1, art_h - int(gut))
            bx, by = ix, iy + frame_h - bh
        else:
            bw, bh = frame_w - text_w - int(gut), frame_h
            bx, by = ix + text_w + int(gut), iy
        art = _rasterise_svg(p["art_svg"], bw, bh)
        if art is None:
            warnings.append(
                "diagram skipped: cairosvg not installed. "
                "pip install cairosvg, or use the Chromium renderer.")
        else:
            im.paste(art, (bx, by), art)
    elif p["art"] == "code" and p["art_code"]:
        _draw_code(im, p, ix, iy, frame_w, frame_h, text_w, gut, dark, SS)

    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / p["out_name"]
    im.resize((p["w"], p["h"]), Image.LANCZOS).save(final, "PNG", optimize=True)
    return dict(canvas=canvas, path=final, w=p["w"], h=p["h"],
                headline_px=round(size / SS, 2), floored=size <= floor,
                overflow=0, warnings=warnings)


def _draw_code(im, p, ix, iy, frame_w, frame_h, text_w, gut, dark, ss):
    c = p["art_code"]
    lines = c.get("lines", [])
    if not lines:
        return
    if p["layout"] == "stack":
        bx, bw = ix, frame_w
        bh = int(frame_h * 0.36)
        by = iy + frame_h - bh
    else:
        bx = ix + text_w + int(gut)
        bw = frame_w - text_w - int(gut)
        bh = frame_h
        by = iy

    fs = p["fs_code"] * ss
    try:
        mono = ImageFont.truetype("consola.ttf", int(fs))
    except Exception:
        mono = font(fs, 500, 14)

    pad = int(p["u"] * ss * 2.5)
    lh = fs * 1.62
    box_h = min(bh, int(len(lines) * lh + pad * 2 + (fs * 2 if c.get("lang") else 0)))
    box_y = by + (bh - box_h) // 2

    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    fill = (255, 255, 255, 12) if dark else (10, 13, 51, 11)
    edge = (255, 255, 255, 31) if dark else (10, 13, 51, 36)
    d.rounded_rectangle([bx, box_y, bx + bw, box_y + box_h],
                        radius=int(p["u"] * ss * 1.1), fill=fill,
                        outline=edge, width=2 * ss)
    im.paste(Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(im)

    y = box_y + pad
    if c.get("lang"):
        lf = font(p["fs_kicker"] * ss, 700, 14)
        d.text((bx + pad, y), c["lang"].upper(), font=lf,
               fill=(150, 160, 180) if dark else (120, 122, 140))
        y += int(fs * 2)
    hl = set(c.get("highlight", []))
    for i, ln in enumerate(lines):
        col = _hex(profiles.PRIMARY) if i in hl else (
            (230, 237, 246) if dark else _hex(profiles.NAVY))
        d.text((bx + pad, y), ln, font=mono, fill=col)
        y += lh


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

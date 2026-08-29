"""Minimal diagram primitives for generated technical documents.

Draws at SCALE x supersampling and downsamples with LANCZOS so the PNGs stay
crisp when Word scales them to page width. Everything is laid out in logical
pixels; the caller never thinks about the scale factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

SCALE = 3
FONT_DIR = "C:/Windows/Fonts"

# ── palette ────────────────────────────────────────────────────────────────
INK = "#1f2933"
MUTED = "#5c6b7a"
FAINT = "#8fa0b3"
WHITE = "#ffffff"

BLUE_F, BLUE_S = "#dce9fa", "#3f72b4"      # user-facing
GREY_F, GREY_S = "#eef1f5", "#93a3b5"      # system / neutral
GREEN_F, GREEN_S = "#dcf0e3", "#3f8f5f"    # active / good
AMBER_F, AMBER_S = "#fdf0d9", "#c98b2e"    # waiting / warning
RED_F, RED_S = "#fbe1e1", "#b85555"        # terminal / rejected
PURPLE_F, PURPLE_S = "#e8e2f7", "#6f5aa8"  # staff / internal
SLATE_F, SLATE_S = "#e3e8ee", "#5c6b7a"    # closed


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size * SCALE)


@dataclass
class Fonts:
    title: ImageFont.FreeTypeFont
    body: ImageFont.FreeTypeFont
    bold: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont
    small_bold: ImageFont.FreeTypeFont
    tiny: ImageFont.FreeTypeFont
    mono: ImageFont.FreeTypeFont


def fonts() -> Fonts:
    return Fonts(
        title=_font("segoeuib.ttf", 20),
        body=_font("segoeui.ttf", 14),
        bold=_font("segoeuib.ttf", 14),
        small=_font("segoeui.ttf", 12),
        small_bold=_font("segoeuib.ttf", 12),
        tiny=_font("segoeui.ttf", 10),
        mono=_font("consola.ttf", 12),
    )


class Canvas:
    def __init__(self, width: int, height: int, bg: str = WHITE) -> None:
        self.w, self.h = width, height
        self.img = Image.new("RGB", (width * SCALE, height * SCALE), bg)
        self.d = ImageDraw.Draw(self.img)
        self.f = fonts()

    # ── helpers ────────────────────────────────────────────────────────────
    def _s(self, *vals: float) -> tuple[float, ...]:
        return tuple(v * SCALE for v in vals)

    def text_size(self, s: str, font) -> tuple[float, float]:
        box = self.d.textbbox((0, 0), s, font=font)
        return (box[2] - box[0]) / SCALE, (box[3] - box[1]) / SCALE

    def wrap(self, s: str, font, max_w: float) -> list[str]:
        """Wrap on spaces; honours explicit | as a hard break."""
        lines: list[str] = []
        for hard in s.split("|"):
            words, cur = hard.split(), ""
            for word in words:
                trial = f"{cur} {word}".strip()
                if self.text_size(trial, font)[0] <= max_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = word
            lines.append(cur)
        return lines

    # ── primitives ─────────────────────────────────────────────────────────
    def text(self, x, y, s, font=None, fill=INK, anchor="lt"):
        font = font or self.f.body
        self.d.text(self._s(x, y), s, font=font, fill=fill, anchor=anchor)

    def box(
        self, x, y, w, h, label="", *, fill=GREY_F, stroke=GREY_S, font=None,
        text_fill=INK, radius=8, width=2, sub="", sub_fill=MUTED, dashed=False,
    ):
        font = font or self.f.body
        if dashed:
            self._dashed_rect(x, y, w, h, stroke, width, radius)
            if fill:
                self.d.rounded_rectangle(
                    self._s(x, y, x + w, y + h), radius=radius * SCALE, fill=fill
                )
                self._dashed_rect(x, y, w, h, stroke, width, radius)
        else:
            self.d.rounded_rectangle(
                self._s(x, y, x + w, y + h),
                radius=radius * SCALE, fill=fill, outline=stroke, width=width * SCALE,
            )
        if label:
            self._centre_text(x, y, w, h, label, font, text_fill, sub, sub_fill)
        return (x, y, w, h)

    def _centre_text(self, x, y, w, h, label, font, fill, sub="", sub_fill=MUTED):
        lines = self.wrap(label, font, w - 14)
        lh = self.text_size("Ag", font)[1] * 1.45
        sub_lines = self.wrap(sub, self.f.tiny, w - 14) if sub else []
        slh = self.text_size("Ag", self.f.tiny)[1] * 1.4 if sub_lines else 0
        total = len(lines) * lh + len(sub_lines) * slh
        cy = y + (h - total) / 2
        for line in lines:
            self.text(x + w / 2, cy, line, font, fill, anchor="ma")
            cy += lh
        for line in sub_lines:
            self.text(x + w / 2, cy + 1, line, self.f.tiny, sub_fill, anchor="ma")
            cy += slh

    def diamond(self, cx, cy, w, h, label="", *, fill=AMBER_F, stroke=AMBER_S, width=2):
        pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
        self.d.polygon([self._s(*p) for p in pts], fill=fill, outline=stroke)
        self.d.line(
            [self._s(*p) for p in pts + [pts[0]]], fill=stroke, width=width * SCALE
        )
        if label:
            self._centre_text(cx - w / 2, cy - h / 2, w, h, label, self.f.small, INK)

    def line(self, pts, *, fill=FAINT, width=2, dashed=False):
        if dashed:
            for i in range(len(pts) - 1):
                self._dashed_line(pts[i], pts[i + 1], fill, width)
        else:
            self.d.line([self._s(*p) for p in pts], fill=fill, width=width * SCALE,
                        joint="curve")

    def arrow(self, pts, *, fill=FAINT, width=2, label="", label_font=None,
              label_fill=MUTED, dashed=False, head=True, label_at=None,
              label_anchor="mm", label_bg=WHITE):
        self.line(pts, fill=fill, width=width, dashed=dashed)
        if head:
            self._head(pts[-2], pts[-1], fill)
        if label:
            font = label_font or self.f.small
            if label_at is None:
                mid = len(pts) // 2
                a, b = pts[mid - 1], pts[mid]
                label_at = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            self._label(label_at, label, font, label_fill, label_anchor, label_bg)

    def _label(self, at, s, font, fill, anchor, bg):
        lines = s.split("|")
        lh = self.text_size("Ag", font)[1] * 1.4
        wmax = max(self.text_size(ln, font)[0] for ln in lines)
        x, y = at
        # keep the label inside the canvas even when the arrow runs to the edge
        x = max(wmax / 2 + 6, min(x, self.w - wmax / 2 - 6))
        if bg:
            self.d.rectangle(
                self._s(x - wmax / 2 - 4, y - (len(lines) * lh) / 2 - 2,
                        x + wmax / 2 + 4, y + (len(lines) * lh) / 2 + 2),
                fill=bg,
            )
        cy = y - (len(lines) * lh) / 2
        for ln in lines:
            self.text(x, cy, ln, font, fill, anchor="ma")
            cy += lh

    def _head(self, a, b, fill, size=7):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        p1 = (b[0] - size * math.cos(ang - 0.45), b[1] - size * math.sin(ang - 0.45))
        p2 = (b[0] - size * math.cos(ang + 0.45), b[1] - size * math.sin(ang + 0.45))
        self.d.polygon([self._s(*b), self._s(*p1), self._s(*p2)], fill=fill)

    def _dashed_line(self, a, b, fill, width, dash=6, gap=4):
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        if dist == 0:
            return
        ux, uy = (b[0] - a[0]) / dist, (b[1] - a[1]) / dist
        pos = 0.0
        while pos < dist:
            end = min(pos + dash, dist)
            self.d.line(
                self._s(a[0] + ux * pos, a[1] + uy * pos,
                        a[0] + ux * end, a[1] + uy * end),
                fill=fill, width=width * SCALE,
            )
            pos = end + gap

    def _dashed_rect(self, x, y, w, h, stroke, width, radius):
        for a, b in (
            ((x + radius, y), (x + w - radius, y)),
            ((x + w, y + radius), (x + w, y + h - radius)),
            ((x + w - radius, y + h), (x + radius, y + h)),
            ((x, y + h - radius), (x, y + radius)),
        ):
            self._dashed_line(a, b, stroke, width)

    def badge(self, x, y, s, *, fill=BLUE_S, text_fill=WHITE, font=None, pad=6):
        font = font or self.f.tiny
        tw, th = self.text_size(s, font)
        w, h = tw + pad * 2, th + pad
        self.d.rounded_rectangle(self._s(x, y, x + w, y + h), radius=h * SCALE / 2,
                                 fill=fill)
        self.text(x + w / 2, y + h / 2, s, font, text_fill, anchor="mm")
        return w, h

    def caption(self, x, y, s, font=None, fill=MUTED):
        self.text(x, y, s, font or self.f.tiny, fill)

    def title(self, x, y, s):
        self.text(x, y, s, self.f.title, INK)

    def save(self, path: str, target_width: int | None = None) -> str:
        img = self.img
        tw = target_width or int(self.w * 1.6)
        img = img.resize((tw, round(tw * self.h / self.w)), Image.LANCZOS)
        img.save(path, "PNG", optimize=True)
        return path


# ── sequence-diagram helper ────────────────────────────────────────────────
class Sequence:
    """Lifeline sequence diagram. Messages are drawn top to bottom."""

    def __init__(self, width: int, actors: list[tuple[str, str]], *,
                 head_h: int = 46, top: int = 58, step: int = 44, bottom: int = 34):
        self.actors = actors
        self.n = len(actors)
        self.width = width
        self.head_h = head_h
        self.top = top
        self.step = step
        self.rows: list[dict] = []
        self.bottom_pad = bottom

    def msg(self, a: str, b: str, label: str, *, style="solid", colour=None,
            note=None, rows=1):
        self.rows.append(dict(kind="msg", a=a, b=b, label=label, style=style,
                              colour=colour, note=note, rows=rows))

    def note(self, over: str, text: str, *, span: tuple[str, str] | None = None,
             fill=AMBER_F, stroke=AMBER_S, rows=1):
        self.rows.append(dict(kind="note", over=over, span=span, text=text,
                              fill=fill, stroke=stroke, rows=rows))

    def sep(self, text: str, rows=1):
        self.rows.append(dict(kind="sep", text=text, rows=rows))

    def render(self, path: str, margin_x: int = 18) -> str:
        rows_total = sum(r["rows"] for r in self.rows)
        height = self.top + self.head_h + rows_total * self.step + self.bottom_pad
        c = Canvas(self.width, height)
        col_w = (self.width - 2 * margin_x) / self.n
        xs = {a[0]: margin_x + col_w * (i + 0.5) for i, a in enumerate(self.actors)}

        # lifelines
        for key, label in self.actors:
            x = xs[key]
            bw = min(col_w - 10, 150)
            c.box(x - bw / 2, self.top, bw, self.head_h, label,
                  fill=PURPLE_F, stroke=PURPLE_S, font=c.f.small_bold, radius=6)
            c.line([(x, self.top + self.head_h), (x, height - 16)],
                   fill="#c7d0da", width=2, dashed=True)

        y = self.top + self.head_h + 12
        for r in self.rows:
            if r["kind"] == "msg":
                ax, bx = xs[r["a"]], xs[r["b"]]
                colour = r["colour"] or (GREEN_S if r["style"] == "reply" else BLUE_S)
                dashed = r["style"] in ("reply", "dashed")
                if ax == bx:  # self-call
                    c.arrow([(ax, y), (ax + 40, y), (ax + 40, y + 16), (ax, y + 16)],
                            fill=colour, dashed=dashed)
                    c.text(ax + 48, y + 2, r["label"], c.f.small, MUTED)
                else:
                    d = 6 if bx > ax else -6
                    c.arrow([(ax + d, y), (bx - d, y)], fill=colour, dashed=dashed)
                    c._label(((ax + bx) / 2, y - 11), r["label"], c.f.small, INK,
                             "mm", WHITE)
            elif r["kind"] == "note":
                if r["span"]:
                    x1, x2 = xs[r["span"][0]], xs[r["span"][1]]
                    nx, nw = min(x1, x2) - 40, abs(x2 - x1) + 80
                else:
                    nx, nw = xs[r["over"]] - 78, 156
                nx = max(6, min(nx, self.width - nw - 6))
                c.box(nx, y - 12, nw, r["rows"] * self.step - 12, r["text"],
                      fill=r["fill"], stroke=r["stroke"], font=c.f.small, radius=5)
            elif r["kind"] == "sep":
                c.line([(margin_x, y), (self.width - margin_x, y)],
                       fill="#d5dce4", width=1)
                c._label((self.width / 2, y), r["text"], c.f.small_bold, MUTED,
                         "mm", WHITE)
            y += r["rows"] * self.step
        return c.save(path)

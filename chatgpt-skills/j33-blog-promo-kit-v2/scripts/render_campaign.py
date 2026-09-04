#!/usr/bin/env python3
"""Render five coordinated J33.AI campaign surfaces from source artwork.

The artwork is cropped to each surface. On top of it the renderer draws the category
label, the headline, an optional deck (the part of the title after a colon) and the
J33.AI wordmark. Text colour is chosen per surface from the background under the
text: warm white over dark areas, charcoal over light areas. A soft, local scrim is
added only where the text would otherwise miss the contrast target.
"""

from __future__ import annotations

import argparse
import functools
import itertools
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat


FORMATS = {
    "instagram": ((1080, 1350), "instagram.png"),
    "linkedin": ((1200, 627), "linkedin.png"),
    "x": ((1600, 900), "x.png"),
    "banner": ((1672, 941), "j33-banner.webp"),
    "thumbnail": ((800, 600), "j33-thumbnail.webp"),
}

PAPER = (248, 247, 244)  # warm white: text colour over dark backgrounds
CHARCOAL = (26, 26, 30)  # near-black: text colour over light backgrounds
BRAND_BLUE = (0, 153, 204)  # J33.AI official #0099CC, used for ".AI" only

FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Inter.ttf"
DEJAVU_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

# WCAG contrast the text must reach against the busiest patch of its background.
TARGET_CONTRAST = 6.0
# The scrim never gets more opaque than this, so it stays a soft shadow rather than a slab.
MAX_SCRIM_ALPHA = 200


@functools.lru_cache(maxsize=None)
def font(size: int, weight: int) -> ImageFont.FreeTypeFont:
    """Inter at a weight from 100 to 900. Falls back to DejaVu Sans when Inter is missing."""
    if FONT_FILE.exists():
        loaded = ImageFont.truetype(str(FONT_FILE), size)
        optical_size = min(32, max(14, size * 0.4))  # Inter's display cut for headlines, text cut for labels
        loaded.set_variation_by_axes([optical_size, weight])
        return loaded
    fallback = DEJAVU_BOLD if weight >= 600 else DEJAVU
    if fallback.exists():
        return ImageFont.truetype(str(fallback), size)
    raise FileNotFoundError(f"Font not found: {FONT_FILE} is missing and DejaVu Sans is not installed")


def cap_height(fnt: ImageFont.FreeTypeFont) -> int:
    """Height of a capital letter above the baseline, used to align text tops to the layout grid."""
    return -fnt.getbbox("H", anchor="ls")[1]


def parse_focal(value: str) -> tuple[float, float]:
    try:
        x, y = (float(part.strip()) for part in value.split(",", 1))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("focal point must be x,y between 0 and 1") from exc
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise argparse.ArgumentTypeError("focal point must be x,y between 0 and 1")
    return x, y


def parse_hex_color(value: str) -> tuple[int, int, int]:
    color = value.strip().lstrip("#")
    if len(color) != 6:
        raise argparse.ArgumentTypeError("colour must use six-digit hex, for example #FFFFFF")
    try:
        return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("colour must use six-digit hex, for example #FFFFFF") from exc


def cover(image: Image.Image, size: tuple[int, int], focal: tuple[float, float]) -> Image.Image:
    src = ImageOps.exif_transpose(image).convert("RGB")
    scale = max(size[0] / src.width, size[1] / src.height)
    resized = src.resize((math.ceil(src.width * scale), math.ceil(src.height * scale)), Image.Resampling.LANCZOS)
    left = round((resized.width - size[0]) * focal[0])
    top = round((resized.height - size[1]) * focal[1])
    left = max(0, min(left, resized.width - size[0]))
    top = max(0, min(top, resized.height - size[1]))
    return resized.crop((left, top, left + size[0], top + size[1]))


# --------------------------------------------------------------------------------------
# Text layout
# --------------------------------------------------------------------------------------


def split_title(title: str) -> tuple[str, str]:
    """'Headline: deck' becomes ('Headline', 'deck'). A title without a colon has no deck."""
    headline, separator, deck = title.partition(":")
    if separator and headline.strip() and deck.strip():
        return headline.strip(), deck.strip()
    return title.strip(), ""


def balanced_lines(text: str, fnt: ImageFont.FreeTypeFont, width: int, max_lines: int) -> list[str] | None:
    """Wrap into the fewest lines that fit, choosing the breaks that keep line lengths even.

    Penalised breaks: a last line shorter than 30% of the column, a break after "&",
    and a break between a number and the word it counts ("4 | Web Attacks").
    Returns None when the text needs more than max_lines or a single word is wider
    than the column.
    """
    words = text.split()
    line_width: dict[tuple[int, int], float] = {}
    for start in range(len(words)):
        for end in range(start + 1, len(words) + 1):
            line_width[start, end] = fnt.getlength(" ".join(words[start:end]))
    if any(line_width[index, index + 1] > width for index in range(len(words))):
        return None

    # Greedy wrapping gives the minimum number of lines.
    line_count, start = 1, 0
    for end in range(1, len(words) + 1):
        if line_width[start, end] > width:
            line_count += 1
            start = end - 1
    if line_count > max_lines:
        return None
    if line_count == 1:
        return [" ".join(words)]

    best_cost, best_lines = math.inf, None
    for breaks in itertools.combinations(range(1, len(words)), line_count - 1):
        bounds = (0, *breaks, len(words))
        widths = [line_width[a, b] for a, b in zip(bounds, bounds[1:])]
        if max(widths) > width:
            continue
        # Slack squared keeps every line close to the column width, so the lines stay even.
        cost = sum((width - w) ** 2 for w in widths)
        if widths[-1] < width * 0.3:
            cost += width ** 2  # orphan: a stub of a last line
        for index in breaks:
            before = words[index - 1]
            if before in ("&", "and") or before.rstrip(",.:").isdigit():
                cost += width ** 2  # "Injection & | CSRF" or "4 | Web Attacks"
        if cost < best_cost:
            best_cost = cost
            best_lines = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
    return best_lines


@dataclass
class Row:
    """One drawn line of text, positioned by its baseline relative to the top of the text block."""

    text: str
    font: ImageFont.FreeTypeFont
    baseline: int
    tracking: int = 0  # extra pixels between letters; only the category label is tracked


def layout_text_block(
    category: str,
    headline: str,
    deck: str,
    width: int,
    max_height: int,
    max_size: int,
) -> tuple[list[Row], int]:
    """Largest headline size at which category, headline and deck all fit the column.

    Returns the rows to draw and the block height. Headlines get at most three lines
    and decks at most two, so long titles shrink instead of stacking.
    """
    min_size = max(24, round(max_size * 0.4))
    for size in range(max_size, min_size - 1, -2):
        headline_font = font(size, 600)
        headline_lines = balanced_lines(headline, headline_font, width, max_lines=3)
        if headline_lines is None:
            continue

        rows: list[Row] = []
        y = 0
        if category:
            category_font = font(max(16, round(size * 0.30)), 600)
            y += cap_height(category_font)
            rows.append(Row(category.upper(), category_font, y, tracking=round(category_font.size * 0.12)))
            y += round(size * 0.70)

        y += cap_height(headline_font)
        headline_leading = round(size * 1.06)
        for line in headline_lines:
            rows.append(Row(line, headline_font, y))
            y += headline_leading
        y -= headline_leading  # back on the last headline baseline

        if deck:
            deck_font = font(max(20, round(size * 0.5)), 450)
            deck_lines = balanced_lines(deck, deck_font, width, max_lines=2)
            if deck_lines is None:
                continue
            y += round(size * 0.62) + cap_height(deck_font)
            deck_leading = round(deck_font.size * 1.25)
            for line in deck_lines:
                rows.append(Row(line, deck_font, y))
                y += deck_leading
            y -= deck_leading

        height = y + round(rows[-1].font.size * 0.25)  # room for descenders on the last line
        if height <= max_height:
            return rows, height
    raise ValueError(
        "Title is too long for this surface. Supply a faithful shorter title with --display-title or --short-title"
    )


def row_width(row: Row) -> float:
    if row.tracking:
        return sum(row.font.getlength(letter) + row.tracking for letter in row.text)
    return row.font.getlength(row.text)


def draw_rows(draw: ImageDraw.ImageDraw, rows: list[Row], x: int, top: int, color: tuple[int, int, int]) -> None:
    for row in rows:
        baseline = top + row.baseline
        if not row.tracking:
            draw.text((x, baseline), row.text, font=row.font, fill=color, anchor="ls")
            continue
        letter_x = x
        for letter in row.text:
            draw.text((letter_x, baseline), letter, font=row.font, fill=color, anchor="ls")
            letter_x += row.font.getlength(letter) + row.tracking


# --------------------------------------------------------------------------------------
# Colour and contrast
# --------------------------------------------------------------------------------------


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    linear = []
    for value in rgb:
        channel = value / 255
        linear.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    lighter, darker = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def background_under(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[tuple[int, int, int], int, int]:
    """Mean colour of the region plus its 15th and 85th percentile grey levels.

    The percentiles stand for the region's darkest and brightest patches: dark patches
    fight charcoal text, bright patches fight white text.
    """
    region = image.crop(box).convert("RGB")
    mean = tuple(round(value) for value in ImageStat.Stat(region).mean)
    histogram = region.convert("L").histogram()
    total = sum(histogram)
    dark_level = bright_level = 255
    seen = 0
    for level, count in enumerate(histogram):
        seen += count
        if dark_level == 255 and seen >= total * 0.15:
            dark_level = level
        if bright_level == 255 and seen >= total * 0.85:
            bright_level = level
    return mean, dark_level, bright_level


def adverse_patch(text_color: tuple[int, int, int], dark_level: int, bright_level: int) -> tuple[int, int, int]:
    """The background patch that reads worst against this text colour."""
    level = bright_level if relative_luminance(text_color) > 0.5 else dark_level
    return (level, level, level)


def local_scrim(
    canvas_size: tuple[int, int],
    box: tuple[int, int, int, int],
    feather: int,
    text_color: tuple[int, int, int],
    background_mean: tuple[int, int, int],
    adverse: tuple[int, int, int],
) -> Image.Image | None:
    """A soft patch behind the text, tinted from the background and only as opaque as contrast needs."""
    if relative_luminance(text_color) > 0.5:
        tint = tuple(round(value * 0.25) for value in background_mean)
    else:
        tint = tuple(round(255 - (255 - value) * 0.25) for value in background_mean)

    alpha = 0
    while alpha < MAX_SCRIM_ALPHA:
        blended = tuple(round(a * (1 - alpha / 255) + t * alpha / 255) for a, t in zip(adverse, tint))
        if contrast_ratio(text_color, blended) >= TARGET_CONTRAST:
            break
        alpha += 8
    if alpha == 0:
        return None

    mask = Image.new("L", canvas_size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=min(alpha, MAX_SCRIM_ALPHA))
    mask = mask.filter(ImageFilter.GaussianBlur(feather))
    scrim = Image.new("RGBA", canvas_size, (*tint, 0))
    scrim.putalpha(mask)
    return scrim


# --------------------------------------------------------------------------------------
# Surfaces
# --------------------------------------------------------------------------------------


def place_logo(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    logo: Image.Image | None,
    x: int,
    y: int,
    height: int,
    j33_color: tuple[int, int, int],
) -> None:
    if logo is not None:
        mark = ImageOps.contain(logo.convert("RGBA"), (height * 4, height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(mark, (x, y - mark.height))
        return
    wordmark_font = font(height, 700)
    draw.text((x, y - height), "J33", font=wordmark_font, fill=j33_color)
    width = draw.textbbox((x, y - height), "J33", font=wordmark_font)[2] - x
    draw.text((x + width, y - height), ".AI", font=wordmark_font, fill=BRAND_BLUE)


def render_one(
    name: str,
    size: tuple[int, int],
    artwork: Image.Image,
    title: str,
    category: str,
    logo: Image.Image | None,
    focal: tuple[float, float],
    text_anchor: str,
    text_color_override: tuple[int, int, int] | None,
    j33_color_override: tuple[int, int, int] | None,
) -> tuple[Image.Image, tuple[int, int, int], float]:
    """Render one surface. Returns the image, the text colour used and the title's contrast ratio."""
    canvas_w, canvas_h = size
    portrait = name == "instagram"
    base = cover(artwork, size, focal).convert("RGBA")

    margin = round(min(size) * 0.064)
    logo_height = max(24, round(min(size) * 0.04))
    logo_top = canvas_h - margin - logo_height

    # Column and type scale per surface.
    if portrait:
        column_width = round(canvas_w * 0.70)  # leaves the upper-right clear for a subject
        max_size = round(canvas_w * 0.074)
    elif name == "thumbnail":
        column_width = round(canvas_w * 0.60)
        max_size = round(canvas_h * 0.095)
    else:
        column_width = round(canvas_w * 0.46)
        max_size = round(canvas_h * 0.10)

    # Vertical band the text block may occupy.
    if portrait:
        band_top = round(canvas_h * 0.16)  # clear of the 1:1 grid crop, which removes the top 10%
        band_bottom = round(canvas_h * 0.82) - margin  # clear of the lower 18% where feed overlays sit
    else:
        band_top = round(margin * 1.4)
        band_bottom = logo_top - round(margin * 1.5)

    headline, deck = split_title(title)
    rows, block_height = layout_text_block(category, headline, deck, column_width, band_bottom - band_top, max_size)
    block_width = math.ceil(max(row_width(row) for row in rows))

    if text_anchor == "bottom":
        block_top = band_bottom - block_height
    elif portrait:
        block_top = band_top
    else:
        # Settle the block around the upper third, never past the band.
        block_top = max(band_top, min(round(canvas_h * 0.36 - block_height / 2), band_bottom - block_height))

    text_box = (margin, block_top, margin + block_width, block_top + block_height)
    mean, dark_level, bright_level = background_under(base, text_box)
    text_color = text_color_override or max((PAPER, CHARCOAL), key=lambda color: contrast_ratio(color, mean))

    # The scrim runs off the canvas on the left and on the anchored edge so it never shows a hard border.
    pad = round(margin * 1.5)
    scrim_box = (
        -pad * 4,
        -pad * 4 if text_anchor == "top" else block_top - pad,
        margin + block_width + pad,
        canvas_h + pad * 4 if text_anchor == "bottom" else block_top + block_height + pad,
    )
    adverse = adverse_patch(text_color, dark_level, bright_level)
    scrim = local_scrim(size, scrim_box, round(margin * 0.8), text_color, mean, adverse)
    if scrim is not None:
        base = Image.alpha_composite(base, scrim)

    _, dark_level, bright_level = background_under(base, text_box)
    contrast = contrast_ratio(text_color, adverse_patch(text_color, dark_level, bright_level))
    if contrast < TARGET_CONTRAST:
        print(
            f"warning: {name} title contrast {contrast:.1f}:1 is below {TARGET_CONTRAST}:1; "
            "try --focal or a plate with calmer negative space",
            file=sys.stderr,
        )

    # Wordmark: J33 takes the neutral that reads best on its own patch of background.
    logo_box = (margin, logo_top, margin + round(logo_height * 3.2), canvas_h - margin)
    logo_mean, logo_dark, logo_bright = background_under(base, logo_box)
    j33_color = j33_color_override or text_color_override or max(
        (PAPER, CHARCOAL), key=lambda color: contrast_ratio(color, logo_mean)
    )
    logo_scrim_box = (-logo_height * 4, logo_top - logo_height, logo_box[2] + logo_height, canvas_h + logo_height * 4)
    logo_scrim = local_scrim(
        size,
        logo_scrim_box,
        round(logo_height * 0.8),
        j33_color,
        logo_mean,
        adverse_patch(j33_color, logo_dark, logo_bright),
    )
    if logo_scrim is not None:
        base = Image.alpha_composite(base, logo_scrim)

    draw = ImageDraw.Draw(base)
    draw_rows(draw, rows, margin, block_top, text_color)
    place_logo(base, draw, logo, margin, canvas_h - margin, logo_height, j33_color)
    return base.convert("RGB"), text_color, contrast


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--art", required=True, type=Path, help="Landscape or crop-safe source artwork")
    parser.add_argument("--vertical-art", type=Path, help="Optional dedicated 4:5 source artwork")
    parser.add_argument("--title", required=True, help="Exact article title for reference")
    parser.add_argument("--display-title", help="Optional faithful shortened title for non-thumbnail images")
    parser.add_argument("--short-title", help="Faithful 3–8 word title for the thumbnail")
    parser.add_argument("--category", default="")
    parser.add_argument("--logo", type=Path, help="Transparent PNG J33.AI logo")
    parser.add_argument(
        "--text-anchor",
        choices=("top", "bottom"),
        default="top",
        help="Where the text block sits: top-left (default) or bottom-left, above the wordmark",
    )
    parser.add_argument(
        "--text-color",
        type=parse_hex_color,
        help="Override the automatic neutral title colour (warm white on dark, charcoal on light)",
    )
    parser.add_argument(
        "--j33-color",
        type=parse_hex_color,
        help="Override the neutral J33 colour; .AI always stays #0099CC",
    )
    parser.add_argument("--focal", type=parse_focal, default=(0.5, 0.5), help="Crop focal point x,y in the 0..1 range")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    if not FONT_FILE.exists():
        print(f"warning: {FONT_FILE} not found, falling back to DejaVu Sans", file=sys.stderr)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    landscape_art = Image.open(args.art)
    vertical_art = Image.open(args.vertical_art) if args.vertical_art else landscape_art
    logo = Image.open(args.logo) if args.logo else None
    display_title = args.display_title or args.title
    short_title = args.short_title or display_title

    for name, (size, filename) in FORMATS.items():
        rendered, text_color, contrast = render_one(
            name,
            size,
            vertical_art if name == "instagram" else landscape_art,
            short_title if name == "thumbnail" else display_title,
            args.category,
            logo,
            args.focal,
            args.text_anchor,
            args.text_color,
            args.j33_color,
        )
        output = args.output_dir / filename
        save_args = {"lossless": True, "method": 6} if output.suffix.lower() == ".webp" else {"optimize": True}
        rendered.save(output, **save_args)
        print(f"{output} {rendered.width}x{rendered.height} text #{'%02X%02X%02X' % text_color} contrast {contrast:.1f}:1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

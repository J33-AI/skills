"""Check a rendered kit before anyone sees it.

    python scripts/verify.py out/

Per file: exact pixel size; whether content survives the display crop (the
banner's 7:3, Instagram's 1:1 grid); contrast of the surface's text colour
against the background under the glyphs, 3:1 for display type and 4.5:1 for
smaller text; and .webp weight against the budget.

Reads `_kit.json` when kit.py has written one. Without it the canvas is
guessed from the filename and the surface from the image, and it says so.

Writes `_crop-<name>.png` previews of what the viewer gets.

It cannot tell you a line broke badly or the diagram hits the logo. Open the
PNGs too.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))

import profiles  # noqa: E402


def luminance(rgb) -> float:
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def background_of(im: Image.Image) -> tuple[int, int, int]:
    """Median colour of the top strip, a stand-in for a flat surface."""
    top = im.crop((0, 0, im.width, max(1, im.height // 20)))
    return tuple(int(v) for v in ImageStat.Stat(top).median[:3])


def text_boxes(im: Image.Image, info: dict) -> dict:
    """The horizontal span the type occupies, per size class.

    The renderers report where the glyphs landed. Only the x range is used;
    sampling runs the full frame height so the median finds background
    rather than an Anton stem.

    Without a manifest, fall back to the whole text column.
    """
    y0, y1 = info["inset_y"], im.height - info["inset_y"]
    box = info.get("text_box")
    if isinstance(box, dict) and any(box.values()):
        return {k: [v[0], y0, v[2], y1]
                for k, v in box.items() if v and len(v) == 4}
    x0 = info["inset_x"]
    x1 = x0 + int((im.width - 2 * x0) * info.get("text_frac", 1.0))
    return {"column": [x0, y0, x1, y1]}


def worst_background(im: Image.Image, box, fg, samples: int = 24):
    """The least favourable background colour under `box`.

    Samples columns across the box and takes each column's median down it:
    glyphs are a minority of any column's height, so the median lands on the
    background behind them. A border ring would read the photograph instead
    of the scrim.

    Returns (rgb, x) for the column that contrasts worst with `fg`.
    """
    x0, y0, x1, y1 = box
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(im.width, int(x1)), min(im.height, int(y1))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return background_of(im), x0

    worst, worst_x, worst_c = None, x0, float("inf")
    step = max(1, (x1 - x0) // samples)
    for x in range(x0, x1, step):
        col = im.crop((x, y0, x + 1, y1))
        med = tuple(int(v) for v in ImageStat.Stat(col).median[:3])
        c = contrast(fg, med)
        if c < worst_c:
            worst, worst_x, worst_c = med, x, c
    return worst, worst_x


def ink_fraction(im: Image.Image, thresh: int = 60) -> float:
    """Fraction of pixels on a strong edge.

    Type and diagram strokes produce edges well above 60; the navy grid and
    the gradients stay under 20, so a mean would not separate them.
    FIND_EDGES adds a bright border, so trim before measuring.
    """
    if im.width < 8 or im.height < 8:
        return 0.0
    g = (im.convert("L")
           .filter(ImageFilter.FIND_EDGES)
           .crop((2, 2, im.width - 2, im.height - 2)))
    hist = g.histogram()
    total = sum(hist)
    return sum(hist[thresh:]) / total if total else 0.0


def check(path: Path, canvas: str, out_dir: Path,
          info: dict | None = None) -> tuple[list[str], list[str]]:
    """Returns (issues, notes). Issues block; notes are advisory."""
    c = profiles.CANVASES[canvas]
    im = Image.open(path).convert("RGB")
    issues: list[str] = []
    notes: list[str] = []

    if info is None:
        # No manifest: assume the narrower text column, the reading least
        # likely to invent a contrast failure.
        info = dict(inset_x=c["inset_x"], inset_y=c["inset_y"], surface=None,
                    text_frac=profiles.text_frac(c["layout"], True))

    if im.size != (c["w"], c["h"]):
        issues.append(f"wrong size {im.width}x{im.height}, expected {c['w']}x{c['h']}")

    box = profiles.crop_box(canvas)
    if box:
        left, top, right, bottom = box
        kept = im.crop(box)
        kept.save(out_dir / f"_crop-{canvas}.png")

        strips = []
        if top > 0:
            strips.append(("top", im.crop((0, 0, im.width, top))))
        if bottom < im.height:
            strips.append(("bottom", im.crop((0, bottom, im.width, im.height))))
        if left > 0:
            strips.append(("left", im.crop((0, 0, left, im.height))))
        if right < im.width:
            strips.append(("right", im.crop((right, 0, im.width, im.height))))

        # On a photograph this test cannot tell the picture's own texture
        # from type, and full-bleed photography is meant to run into the
        # strip. Say what was measured and leave the judgement to the human.
        photo = info.get("surface") == "photo"
        for side, strip in strips:
            f = ink_fraction(strip)
            if f <= 0.002:
                continue
            where = (f"the {side} strip that the {c['crop_ratio']:.3f} display "
                     f"crop removes")
            if photo:
                notes.append(
                    f"{f * 100:.2f}% of {where} carries edges, but this is a "
                    f"photo surface and the check cannot tell the photograph's "
                    f"own texture from type - open _crop-{canvas}.png and look")
            else:
                issues.append(
                    f"content sits in {where} ({f * 100:.2f}% of that strip is "
                    f"ink) - see _crop-{canvas}.png")

    # Which type colour to test depends on the surface. The manifest names it;
    # without one, read it off the background: paper is light and takes navy
    # type, navy and photo are dark and take white.
    surface = info.get("surface")
    if surface is None:
        surface = "paper" if luminance(background_of(im)) > 0.5 else "navy"
    fg_hex = profiles.SURFACES[surface]["fg"]
    fg = ImageColor.getrgb(fg_hex)

    # WCAG puts large text at 3:1 and everything else at 4.5:1; the headline
    # here is four to six times the size of the eyebrow.
    bars = {"display": (3.0, "display type"), "body": (4.5, "small text"),
            "column": (4.5, "text")}
    for kind, box in sorted(text_boxes(im, info).items()):
        floor, label = bars.get(kind, (4.5, kind))
        bg, bg_x = worst_background(im, box, fg)
        ratio = contrast(fg, bg)
        if ratio < floor:
            issues.append(f"{label} ({fg_hex}) is {ratio:.1f}:1 against the "
                          f"background at x={bg_x}, below the {floor}:1 minimum")
        if kind != "display":
            continue
        cc = contrast(ImageColor.getrgb(profiles.PRIMARY), bg)
        if cc < 3.0:
            notes.append(f"accent cyan is {cc:.1f}:1 at x={bg_x} - fine for a "
                         f"display headline, too low for small text")

    # The website files ship as .webp, so the budget applies to those.
    budget = c["webp_kb"]
    if budget:
        webp = path.with_suffix(".webp")
        if webp.exists():
            kb = webp.stat().st_size // 1024
            if kb > budget:
                issues.append(f"{webp.name} is {kb}KB, over the {budget}KB budget")
        else:
            issues.append(f"no .webp for the website - re-run kit.py with --webp")

    return issues, notes


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    out_dir = Path(sys.argv[1])
    if not out_dir.is_dir():
        print(f"not a directory: {out_dir}", file=sys.stderr)
        return 2

    by_name: dict[str, Path] = {}
    info: dict[str, dict] = {}

    manifest = out_dir / "_kit.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for entry in data.get("canvases", []):
                f = out_dir / entry["file"]
                if entry["canvas"] in profiles.CANVASES and f.is_file():
                    by_name[entry["canvas"]] = f
                    info[entry["canvas"]] = entry
        except (ValueError, KeyError, OSError) as e:
            print(f"note: ignoring unreadable {manifest.name} ({e})")

    if not by_name:
        # No manifest: match on filename, most specific first, because
        # `banner` is `<slug>.png` and as a glob would swallow instagram.png.
        pool = [p for p in sorted(out_dir.glob("*.png"))
                if not p.name.startswith("_")]
        for canvas, c in profiles.CANVASES.items():
            if "{slug}" not in c["out"]:
                match = next((p for p in pool if p.name == c["out"]), None)
                if match:
                    by_name[canvas] = match
                    pool.remove(match)

        card = next((p for p in pool if p.stem.endswith("-card")), None)
        if card:
            by_name["card"] = card
            pool.remove(card)

        if pool:
            by_name["banner"] = pool[0]
        if by_name:
            print("note: no _kit.json here, so the surface and text column are "
                  "being guessed. Re-run through kit.py for exact checks.\n")

    if not by_name:
        print(f"no kit images found in {out_dir}", file=sys.stderr)
        return 2

    total = 0
    for canvas in profiles.ORDER:
        if canvas not in by_name:
            print(f"  {canvas:<10} MISSING")
            total += 1
            continue
        p = by_name[canvas]
        issues, notes = check(p, canvas, out_dir, info.get(canvas))
        kb = p.stat().st_size // 1024
        status = "ok" if not issues else f"{len(issues)} issue(s)"
        print(f"  {canvas:<10} {kb:>4}KB  {p.name}   {status}")
        for i in issues:
            print(f"             ! {i}")
        for n in notes:
            print(f"             - {n}")
        total += len(issues)

    print()
    if total:
        print(f"{total} issue(s). Fix the spec and re-render.")
    else:
        print("All checks passed. Now open the PNGs and look at them.")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())

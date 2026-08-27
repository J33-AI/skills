"""Check a rendered kit before anyone sees it.

    python scripts/verify.py out/

Checks, per file:
  * exact pixel dimensions
  * whether artwork survives the display crop (the banner's 7:3 and
    Instagram's 1:1 grid crop)
  * contrast of the surface-appropriate text colour against the background
  * file weight against the budget the shipped j33.ai images set

Also writes `_crop-<name>.png` previews so you can look at what the viewer
actually gets rather than trusting the arithmetic.

The script cannot tell you a line broke badly or the diagram collides with the
logo. Open the PNGs too.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))

import profiles  # noqa: E402

SIZE_BUDGET_KB = {"banner": 340, "card": 200}


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
    """Median colour of a border ring — a decent stand-in for the surface."""
    w, h = im.size
    ring = Image.new("RGB", (w, max(1, h // 20)))
    ring.paste(im.crop((0, 0, w, h // 20)), (0, 0))
    return tuple(int(v) for v in ImageStat.Stat(ring).median[:3])


def ink_fraction(im: Image.Image, thresh: int = 60) -> float:
    """Fraction of pixels sitting on a strong edge.

    Mean edge energy does not work here: the navy surface carries a 5% grid
    whose edges are everywhere, so every strip looks as busy as the artwork.
    Type and diagram strokes produce edges well above 60; the grid and the
    gradients stay under 20. FIND_EDGES fabricates a bright border, so trim
    before measuring.
    """
    if im.width < 8 or im.height < 8:
        return 0.0
    g = (im.convert("L")
           .filter(ImageFilter.FIND_EDGES)
           .crop((2, 2, im.width - 2, im.height - 2)))
    hist = g.histogram()
    total = sum(hist)
    return sum(hist[thresh:]) / total if total else 0.0


def check(path: Path, canvas: str, out_dir: Path) -> tuple[list[str], list[str]]:
    """Returns (issues, notes). Issues block; notes are advisory."""
    c = profiles.CANVASES[canvas]
    im = Image.open(path).convert("RGB")
    issues: list[str] = []
    notes: list[str] = []

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

        for side, strip in strips:
            f = ink_fraction(strip)
            if f > 0.002:
                issues.append(
                    f"content sits in the {side} strip that the "
                    f"{c['crop_ratio']:.3f} display crop removes "
                    f"({f * 100:.2f}% of that strip is ink) - "
                    f"see _crop-{canvas}.png")

    # Which foreground applies depends on the surface, and the surface is
    # readable from the background itself: paper is light and takes navy type,
    # navy and photo are dark and take white.
    bg = background_of(im)
    light = luminance(bg) > 0.5
    fg, fg_name = ((10, 13, 51), "navy #0A0D33") if light else ((255, 255, 255), "white")

    cf = contrast(fg, bg)
    if cf < 4.5:
        issues.append(f"body text ({fg_name}) is {cf:.1f}:1 on this background, "
                      f"below the 4.5:1 minimum")

    cc = contrast((0, 153, 204), bg)
    if cc < 3.0:
        notes.append(f"accent cyan is {cc:.1f}:1 here - fine for the display "
                     f"headline, too low for small text")

    # The website files ship as .webp, so that is what the budget applies to.
    # A heavy intermediate PNG is not a problem in itself.
    budget = SIZE_BUDGET_KB.get(canvas)
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

    # Resolve most-specific first. `banner` is `<slug>.png`, which as a glob is
    # just `*.png` and would otherwise swallow instagram.png.
    pool = [p for p in sorted(out_dir.glob("*.png")) if not p.name.startswith("_")]
    by_name: dict[str, Path] = {}

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
        issues, notes = check(p, canvas, out_dir)
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

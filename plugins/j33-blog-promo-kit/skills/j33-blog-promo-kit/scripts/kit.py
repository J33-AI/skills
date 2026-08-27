"""Orchestrator: one spec in, the full five-image kit out.

    python scripts/kit.py --spec spec.json --out out/

Picks the Chromium renderer when it is available and falls back to Pillow
otherwise, so the same spec produces a kit in Claude Code and in ChatGPT's
sandbox. Use --engine to force one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import profiles  # noqa: E402


def to_webp(png: Path, quality: int = 82) -> Path:
    from PIL import Image
    dst = png.with_suffix(".webp")
    Image.open(png).convert("RGB").save(dst, "WEBP", quality=quality, method=6)
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True, help="path to the spec JSON")
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--engine", choices=["auto", "chromium", "pil"], default="auto")
    ap.add_argument("--canvas", action="append", default=None,
                    help="restrict to one canvas; repeatable")
    ap.add_argument("--webp", action="store_true",
                    help="also emit .webp for the two website files")
    a = ap.parse_args()

    try:
        spec = profiles.load_spec(a.spec)
    except (ValueError, OSError) as e:
        print(f"spec error: {e}", file=sys.stderr)
        return 2

    todo = a.canvas or profiles.ORDER
    unknown = [c for c in todo if c not in profiles.CANVASES]
    if unknown:
        print(f"unknown canvas: {', '.join(unknown)}", file=sys.stderr)
        return 2

    engine = a.engine
    if engine == "auto":
        import render
        engine = "chromium" if render.available() else "pil"
        if engine == "pil":
            print("note: Chromium unavailable, using the Pillow renderer")

    out = Path(a.out)
    if engine == "chromium":
        import render
        results = render.render_all(spec, out, todo)
    else:
        import compose
        results = compose.render_all(spec, out, todo)

    print(f"\n{engine} · {len(results)} images -> {out}/\n")
    problems = 0
    for r in results:
        line = f"  {r['canvas']:<10} {r['w']:>4}x{r['h']:<4}  {r['path'].name}"
        if r.get("headline_px"):
            line += f"   headline {r['headline_px']}px"
        print(line)
        if r.get("floored"):
            problems += 1
            print("             ! headline hit the minimum size - cut words "
                  "rather than lowering the floor")
        for w in r.get("warnings", []):
            problems += 1
            print(f"             ! {w}")

    if a.webp:
        print()
        for r in results:
            if profiles.CANVASES[r["canvas"]]["website"]:
                w = to_webp(r["path"])
                print(f"  {w.name}  {w.stat().st_size // 1024}KB")

    print("\nNext: python scripts/verify.py " + str(out))
    if problems:
        print(f"({problems} warning(s) above)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

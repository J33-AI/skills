"""Chromium renderer, the high-fidelity path.

Renders the template at 2x onto the exact canvas viewport, then downsamples
with LANCZOS; 1:1 type looks thin and slightly ragged.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

import profiles

SCALE = 2  # deviceScaleFactor


def available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


# The union of the glyphs in the text column, one Range rect per rendered
# line, not the blocks holding them: an <h1> fills its column whatever the
# headline's length. Coordinates are relative to .poster, which is what gets
# screenshotted, so they are file pixels. Two boxes because verify.py holds
# display type and small text to different contrast bars.
TEXT_BOX_JS = """(() => {
  const poster = document.querySelector('.poster');
  if(!poster) return null;
  const pr = poster.getBoundingClientRect();
  const range = document.createRange();
  const union = sel => {
    let b = [Infinity, Infinity, -Infinity, -Infinity], found = false;
    document.querySelectorAll(sel).forEach(el => {
      if(getComputedStyle(el).display === 'none') return;
      range.selectNodeContents(el);
      for(const r of range.getClientRects()){
        if(r.width <= 0 || r.height <= 0) continue;
        found = true;
        b[0] = Math.min(b[0], r.left - pr.left);  b[1] = Math.min(b[1], r.top - pr.top);
        b[2] = Math.max(b[2], r.right - pr.left); b[3] = Math.max(b[3], r.bottom - pr.top);
      }
    });
    return found ? b.map(Math.round) : null;
  };
  return {
    display: union('.col-text .headline, .col-text .logo'),
    body:    union('.col-text .eyebrow, .col-text .subhead, .col-text .kicker')
  };
})()"""


def render_all(spec: dict, out_dir: Path, canvases: list[str]) -> list[dict]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-color-profile=srgb",
                                           "--disable-lcd-text"])
        try:
            # One context for the whole kit, so the fonts are fetched once.
            ctx = browser.new_context(device_scale_factor=SCALE)
            for name in canvases:
                payload = profiles.resolve(spec, name)

                # Absolute file URLs so images resolve regardless of cwd.
                for key in ("photo", "art_img"):
                    if payload.get(key):
                        payload[key] = Path(payload[key]).as_uri()

                page = ctx.new_page()
                page.set_viewport_size({"width": payload["w"], "height": payload["h"]})
                page.add_init_script(
                    "window.__PAYLOAD__ = " + json.dumps(payload) + ";"
                )
                page.goto(profiles.TEMPLATE.as_uri(), wait_until="load")
                page.wait_for_selector("html[data-ready='1']",
                                       state="attached", timeout=15000)
                page.evaluate("document.fonts.ready")

                fit = page.evaluate("window.__FIT__") or {}
                code_fit = page.evaluate("window.__CODE_FIT__") or {}
                box = page.evaluate(TEXT_BOX_JS)
                png = page.locator(".poster").screenshot()
                page.close()

                final = out_dir / payload["out_name"]
                (Image.open(io.BytesIO(png)).convert("RGB")
                      .resize((payload["w"], payload["h"]), Image.LANCZOS)
                      .save(final, "PNG"))

                warnings = []
                if code_fit.get("clipped"):
                    warnings.append("a code line is wider than the panel even at "
                                    "the minimum size - shorten it")
                results.append(dict(
                    canvas=name, path=final, w=payload["w"], h=payload["h"],
                    headline_px=fit.get("size"), floored=bool(fit.get("floored")),
                    warnings=warnings, text_box=box, payload=payload,
                ))
        finally:
            browser.close()
    return results


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Render posters via Chromium.")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--canvas", action="append", default=None,
                    help="restrict to one canvas; repeatable")
    a = ap.parse_args()

    spec = profiles.load_spec(a.spec)
    todo = a.canvas or profiles.ORDER
    for r in render_all(spec, Path(a.out), todo):
        flag = "  [headline floored - cut words]" if r["floored"] else ""
        print(f"{r['canvas']:<10} {r['w']}x{r['h']}  {r['path'].name}{flag}")
        for w in r["warnings"]:
            print(f"           ! {w}")

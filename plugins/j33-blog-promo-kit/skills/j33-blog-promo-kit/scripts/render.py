"""Chromium renderer — the high-fidelity path.

Renders the poster template at 2x onto the exact canvas viewport, then
downsamples with LANCZOS. Supersampling is what gives the type clean edges;
rendering 1:1 looks thin and slightly ragged.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import profiles


def available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


def _as_file_url(p: str | Path) -> str:
    return Path(p).resolve().as_uri()


def render_all(spec: dict, out_dir: Path, canvases: list[str], scale: int = 2) -> list[dict]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    tmp = out_dir / ".raw"
    tmp.mkdir(exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-color-profile=srgb",
                                           "--disable-lcd-text"])
        try:
            for name in canvases:
                payload = profiles.resolve(spec, name)

                # Absolute file URLs so images resolve regardless of cwd.
                for key in ("photo", "art_img"):
                    if payload.get(key):
                        payload[key] = _as_file_url(payload[key])

                page = browser.new_page(
                    viewport={"width": payload["w"], "height": payload["h"]},
                    device_scale_factor=scale,
                )
                page.add_init_script(
                    "window.__PAYLOAD__ = " + json.dumps(payload) + ";"
                )
                page.goto(_as_file_url(profiles.TEMPLATE), wait_until="load")
                page.wait_for_selector("html[data-ready='1']",
                                       state="attached", timeout=15000)
                page.evaluate("document.fonts.ready")

                fit = page.evaluate("window.__FIT__") or {}
                raw = tmp / f"{name}.png"
                page.locator(".poster").screenshot(path=str(raw))
                page.close()

                final = out_dir / payload["out_name"]
                _downsample(raw, final, payload["w"], payload["h"])

                results.append(dict(
                    canvas=name, path=final, w=payload["w"], h=payload["h"],
                    headline_px=fit.get("size"), floored=bool(fit.get("floored")),
                    overflow=fit.get("overflow", 0),
                ))
        finally:
            browser.close()

    for f in tmp.glob("*.png"):
        f.unlink()
    tmp.rmdir()
    return results


def _downsample(src: Path, dst: Path, w: int, h: int) -> None:
    im = Image.open(src).convert("RGB")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    im.save(dst, "PNG", optimize=True)


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

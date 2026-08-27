"""Regression tests for the render pipeline.

    python tests/test_kit.py            # everything
    python tests/test_kit.py -k svg     # one group

Needs Pillow and the stdlib. The Chromium tests skip when Playwright is not
installed. `VerifyNegative` breaks renders on purpose and checks that the
verifier catches them.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

import compose            # noqa: E402
import kit                # noqa: E402
import profiles           # noqa: E402
import render             # noqa: E402
import svgpil             # noqa: E402
import verify             # noqa: E402

EXAMPLES = SKILL / "assets" / "examples"
SIGNAL_SPEC = EXAMPLES / "signal-diagram.json"
EMBER_SPEC = EXAMPLES / "ember-diagram.json"
CRIMSON_SPEC = EXAMPLES / "crimson-code.json"
ALL_SPECS = (SIGNAL_SPEC, EMBER_SPEC, CRIMSON_SPEC)

# The shipped examples, rendered once with Pillow (plus webp and manifest) and
# shared by the tests that only read them. Tests that mutate a file copy it
# into their own directory first.
_KIT_DIR = tempfile.TemporaryDirectory()
_KITS: dict[Path, dict] = {}


def example_kit(spec_path: Path) -> dict:
    """{"out": dir, "results": {canvas: result}, "manifest": {...}} for one example."""
    if spec_path not in _KITS:
        out = Path(_KIT_DIR.name) / spec_path.stem
        spec = profiles.load_spec(spec_path)
        results = compose.render_all(spec, out, profiles.ORDER)
        for r in results:
            if profiles.CANVASES[r["canvas"]]["webp_kb"]:
                kit.to_webp(r["path"])
        manifest = kit.write_manifest(spec, out, "pil", results)
        _KITS[spec_path] = dict(out=out, manifest=manifest,
                                results={r["canvas"]: r for r in results})
    return _KITS[spec_path]


def tearDownModule():
    _KIT_DIR.cleanup()


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def solid(path: Path, rgb, size=(1600, 1000)) -> Path:
    Image.new("RGB", size, rgb).save(path)
    return path


def size_of(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def ink_alpha(im: Image.Image) -> float:
    """Fraction of the image that is not transparent."""
    a = im.getchannel("A")
    return sum(a.histogram()[16:]) / (im.width * im.height)


def art_column(p: dict) -> tuple[int, int, int, int]:
    """The artwork box of a rendered row layout, from its own payload.

    Derived so the tests do not pin positions the profile table may move.
    """
    frame_w = p["w"] - 2 * p["inset_x"]
    x0 = p["inset_x"] + int(frame_w * p["text_frac"]) + int(p["gutter"])
    return (x0, p["inset_y"], p["w"] - p["inset_x"], p["h"] - p["inset_y"])


class TmpDirCase(unittest.TestCase):
    """A fresh output directory per test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)


# ── geometry ─────────────────────────────────────────────────────────────────

class Geometry(unittest.TestCase):

    def test_canvas_dimensions_are_exact(self):
        # These five numbers are the contract with j33.ai and the platforms.
        expected = {
            "banner": (1600, 873), "card": (1659, 948),
            "instagram": (1080, 1350), "x": (1600, 900),
            "linkedin": (1200, 1200),
        }
        for name, (w, h) in expected.items():
            with self.subTest(name):
                self.assertEqual((profiles.CANVASES[name]["w"],
                                  profiles.CANVASES[name]["h"]), (w, h))

    def test_banner_crop_band(self):
        # 1600x873 shown at 7:3 keeps a 686px band: 93px off the top, 94 off
        # the bottom. The docs round both to ~94.
        self.assertEqual(profiles.crop_box("banner"), (0, 93, 1600, 779))

    def test_instagram_grid_crop_band(self):
        # 1080x1350 centre-cropped to 1:1 in the profile grid.
        self.assertEqual(profiles.crop_box("instagram"), (0, 135, 1080, 1215))

    def test_uncropped_canvases_report_no_box(self):
        for name in ("card", "x", "linkedin"):
            with self.subTest(name):
                self.assertIsNone(profiles.crop_box(name))

    def test_safe_inset_clears_the_crop(self):
        """An inset below its crop would start the layout inside the strip
        the viewer never sees."""
        for name in ("banner", "instagram"):
            with self.subTest(name):
                box = profiles.crop_box(name)
                self.assertGreater(profiles.CANVASES[name]["inset_y"], box[1])

    def test_text_frac(self):
        self.assertEqual(profiles.text_frac("stack", True), 1.0)
        self.assertEqual(profiles.text_frac("wide", True), 0.46)
        self.assertEqual(profiles.text_frac("split", True), 0.52)
        # No artwork: the text column takes the room the art would have had.
        self.assertEqual(profiles.text_frac("wide", False), 0.78)
        self.assertEqual(profiles.text_frac("stack", False), 1.0)


# ── spec loading ─────────────────────────────────────────────────────────────

class SpecLoading(TmpDirCase):

    def load(self, **overrides):
        spec = {"slug": "s", "headline": "H"}
        spec.update(overrides)
        return profiles.load_spec(write_json(self.out / "spec.json", spec))

    def test_requires_headline_and_slug(self):
        with self.assertRaisesRegex(ValueError, "headline"):
            self.load(headline="")
        with self.assertRaisesRegex(ValueError, "slug"):
            self.load(slug="")

    def test_rejects_unknown_surface_and_art(self):
        with self.assertRaisesRegex(ValueError, "surface"):
            self.load(surface="chrome")
        with self.assertRaisesRegex(ValueError, "art mode"):
            self.load(art="hologram")

    def test_photo_surface_requires_a_photo(self):
        with self.assertRaisesRegex(ValueError, "requires a 'photo'"):
            profiles.resolve(self.load(surface="photo"), "banner")

    def test_missing_image_is_rejected_not_silently_dropped(self):
        spec = self.load(surface="photo", photo="nope.jpg")
        with self.assertRaisesRegex(ValueError, "not a file"):
            profiles.resolve(spec, "banner")

    def test_image_path_resolves_relative_to_the_spec(self):
        solid(self.out / "shot.png", (120, 120, 120), (400, 300))
        spec = self.load(surface="photo", photo="shot.png")
        p = profiles.resolve(spec, "banner")
        self.assertEqual(Path(p["photo"]).resolve(),
                         (self.out / "shot.png").resolve())

    def test_payload_carries_no_loader_bookkeeping(self):
        """render.py serialises the payload to JSON; `_base` must not leak in."""
        p = profiles.resolve(self.load(), "banner")
        self.assertFalse([k for k in p if k.startswith("_")])
        json.dumps(p)   # must not raise

    def test_overrides_apply_per_canvas(self):
        spec = self.load(art="code", art_code={"lines": ["x = 1"]},
                         overrides={"instagram": {"art": "none"}})
        self.assertEqual(profiles.resolve(spec, "instagram")["art"], "none")
        self.assertEqual(profiles.resolve(spec, "banner")["art"], "code")


# ── the SVG subset ───────────────────────────────────────────────────────────

class SvgSubset(unittest.TestCase):

    def rast(self, svg, w=400, h=300, **kw):
        return svgpil.rasterise(svg, w, h, **kw)

    def test_shipped_example_renders_without_warnings(self):
        spec = json.loads(SIGNAL_SPEC.read_text(encoding="utf-8"))
        svg = profiles.paint_svg(spec["art_svg"], "#0099CC", "#FFFFFF")
        im, warns = self.rast(svg, 700, 620)
        self.assertEqual(warns, [])
        self.assertIsNotNone(im)
        self.assertGreater(ink_alpha(im), 0.02)

    def test_unpainted_token_is_reported_not_silently_dropped(self):
        svg = ('<svg viewBox="0 0 100 100"><rect x="10" y="10" width="80" '
               'height="80" fill="#ACCENT"/></svg>')
        _, warns = self.rast(svg)
        self.assertTrue(any("#ACCENT" in w for w in warns), warns)

    def test_malformed_xml_is_reported_not_raised(self):
        im, warns = self.rast("<svg><rect")
        self.assertIsNone(im)
        self.assertTrue(any("well-formed" in w for w in warns))

    def test_unsupported_element_warns_and_keeps_going(self):
        svg = ('<svg viewBox="0 0 100 100">'
               '<foreignObject x="0" y="0" width="9" height="9"/>'
               '<rect x="10" y="10" width="80" height="80" fill="#FFFFFF"/></svg>')
        im, warns = self.rast(svg)
        self.assertTrue(any("foreignObject" in w for w in warns))
        self.assertGreater(ink_alpha(im), 0.3)   # the rect still drew

    def test_shapes_all_produce_ink(self):
        shapes = {
            "rect": '<rect x="10" y="10" width="80" height="80"/>',
            "circle": '<circle cx="50" cy="50" r="40"/>',
            "ellipse": '<ellipse cx="50" cy="50" rx="40" ry="25"/>',
            "line": '<line x1="10" y1="10" x2="90" y2="90"/>',
            "polyline": '<polyline points="10,10 50,90 90,10"/>',
            "polygon": '<polygon points="10,10 90,10 50,90"/>',
            "path-lines": '<path d="M10 10 H90 V90 Z"/>',
            "path-cubic": '<path d="M10 50 C 30 10, 70 90, 90 50"/>',
            "path-quad": '<path d="M10 50 Q 50 10 90 50"/>',
            "path-arc": '<path d="M10 50 A 40 30 0 0 1 90 50"/>',
        }
        for name, body in shapes.items():
            with self.subTest(name):
                svg = (f'<svg viewBox="0 0 100 100"><g fill="none" '
                       f'stroke="#FFFFFF" stroke-width="3">{body}</g></svg>')
                im, warns = self.rast(svg)
                self.assertEqual(warns, [])
                self.assertGreater(ink_alpha(im), 0.005, name)

    def test_dasharray_leaves_gaps(self):
        base = '<svg viewBox="0 0 100 20"><line x1="0" y1="10" x2="100" y2="10" %s/></svg>'
        style = 'stroke="#FFFFFF" stroke-width="4"'
        solid_im, _ = self.rast(base % style, 400, 80)
        dashed_im, _ = self.rast(base % (style + ' stroke-dasharray="6 6"'), 400, 80)
        self.assertLess(ink_alpha(dashed_im), ink_alpha(solid_im) * 0.75)

    def test_marker_end_draws_an_arrowhead(self):
        marker = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
                  'markerWidth="5" markerHeight="5" orient="auto">'
                  '<path d="M0 0 L10 5 L0 10 z" fill="#FFFFFF"/></marker></defs>')

        def connector(extra):
            return ('<svg viewBox="0 0 100 100">' + marker +
                    '<path d="M10 50 H90" stroke="#FFFFFF" stroke-width="3" '
                    'fill="none" ' + extra + '/></svg>')

        plain, _ = self.rast(connector(""))
        arrow, _ = self.rast(connector('marker-end="url(#a)"'))
        self.assertGreater(ink_alpha(arrow), ink_alpha(plain) * 1.15)

    def test_text_anchor_middle_centres_the_label(self):
        svg = ('<svg viewBox="0 0 200 60"><text x="100" y="40" font-family="Inter" '
               'font-size="30" fill="#FFFFFF" text-anchor="middle">HH</text></svg>')
        im, _ = self.rast(svg, 400, 120, fit_viewbox=False)
        cols = [x for x in range(im.width)
                if im.crop((x, 0, x + 1, im.height)).getchannel("A").getextrema()[1] > 16]
        self.assertTrue(cols)
        centre = (cols[0] + cols[-1]) / 2
        self.assertAlmostEqual(centre, im.width / 2, delta=im.width * 0.06)

    def test_currentcolor_follows_the_surface(self):
        svg = ('<svg viewBox="0 0 100 100"><rect x="10" y="10" width="80" '
               'height="80" fill="currentColor"/></svg>')
        im, _ = self.rast(svg, 100, 100, current_color="#0099CC")
        self.assertEqual(im.getpixel((50, 50))[:3], (0, 153, 204))

    def test_declared_viewbox_is_honoured_when_not_fitting(self):
        # A small mark in a large viewBox stays small when fitting is off, and
        # grows to fill the box when it is on.
        svg = ('<svg viewBox="0 0 400 400"><rect x="180" y="180" width="40" '
               'height="40" fill="#FFFFFF"/></svg>')
        loose, _ = self.rast(svg, 200, 200, fit_viewbox=False)
        tight, _ = self.rast(svg, 200, 200, fit_viewbox=True)
        self.assertLess(ink_alpha(loose), 0.05)
        self.assertGreater(ink_alpha(tight), 0.5)


# ── themes ───────────────────────────────────────────────────────────────────

class Themes(TmpDirCase):
    """The article colours the plate and the accent; the lockup never moves."""

    def payload(self, canvas="banner", **spec):
        base = {"slug": "s", "headline": "One Two Three"}
        base.update(spec)
        return profiles.resolve(
            profiles.load_spec(write_json(self.out / "spec.json", base)), canvas)

    def test_default_theme_keeps_the_house_palette(self):
        p = self.payload()
        self.assertEqual(p["theme"], "signal")
        self.assertEqual(p["c_accent"], profiles.BRAND_CYAN)
        self.assertEqual(p["c_dark_from"], "#0A0D33")
        self.assertEqual(p["c_paper"], "#F6F0E2")

    def test_theme_moves_the_plate_and_the_accent(self):
        p = self.payload(theme="ember")
        self.assertEqual(p["c_accent"], "#F26A1B")
        self.assertEqual((p["c_dark_from"], p["c_dark_to"]),
                         profiles.THEMES["ember"]["dark"])

    def test_paper_takes_the_deeper_accent(self):
        dark = self.payload(theme="ember", surface="dark")["c_accent"]
        paper = self.payload(theme="ember", surface="paper")["c_accent"]
        self.assertNotEqual(dark, paper)
        self.assertLess(verify.luminance(ImageColor.getrgb(paper)),
                        verify.luminance(ImageColor.getrgb(dark)))

    def test_lockup_never_follows_the_theme(self):
        for theme in profiles.THEMES:
            with self.subTest(theme):
                dark = self.payload(theme=theme, surface="dark")
                paper = self.payload(theme=theme, surface="paper")
                self.assertEqual(dark["c_logo_ai"], profiles.BRAND_CYAN)
                self.assertEqual(paper["c_logo_ai"], profiles.BRAND_CYAN)
                self.assertEqual(dark["c_logo_j33"], "#FFFFFF")
                self.assertEqual(paper["c_logo_j33"], profiles.NAVY)

    def test_mono_falls_back_to_the_surface_ink(self):
        self.assertEqual(self.payload(theme="mono", surface="dark")["c_accent"],
                         "#FFFFFF")
        self.assertEqual(self.payload(theme="mono", surface="paper")["c_accent"],
                         profiles.NAVY)

    def test_every_theme_accent_clears_the_lockup(self):
        """A near-cyan accent would make the '.AI' read as a failed match."""
        for name, theme in profiles.THEMES.items():
            for accent in theme["accent"] or ():
                with self.subTest(f"{name}/{accent}"):
                    self.assertFalse(profiles.clashes_with_lockup(accent))

    def test_navy_is_still_accepted_as_a_surface_name(self):
        self.assertEqual(self.payload(surface="navy")["surface"], "dark")

    def test_unknown_theme_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown theme"):
            self.payload(theme="neon")

    def test_accent_hex_overrides_the_theme(self):
        self.assertEqual(self.payload(theme="ember", accent_hex="#7C2A92")["c_accent"],
                         "#7C2A92")

    def test_accent_hex_too_near_the_lockup_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "degrees of the lockup"):
            self.payload(accent_hex="#00B4C8")

    def test_accent_hex_that_is_not_a_colour_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not a colour"):
            self.payload(accent_hex="ember")

    def test_near_grey_accents_are_allowed_beside_the_lockup(self):
        # slate sits at a cyan-ish hue but is too desaturated to compete.
        self.assertFalse(profiles.clashes_with_lockup("#8E97A3"))

    def test_diagram_tokens_take_the_render_colours(self):
        svg = '<svg viewBox="0 0 10 10"><rect fill="#INK" stroke="#ACCENT"/></svg>'
        dark = self.payload(theme="crimson", surface="dark",
                            art="diagram", art_svg=svg)["art_svg"]
        self.assertIn('fill="#FFFFFF"', dark)
        self.assertIn('stroke="#E23744"', dark)
        paper = self.payload(theme="crimson", surface="paper",
                             art="diagram", art_svg=svg)["art_svg"]
        self.assertIn(f'fill="{profiles.NAVY}"', paper)
        self.assertIn('stroke="#B4232F"', paper)

    def test_every_theme_renders_and_verifies_on_both_plates(self):
        for theme in profiles.THEMES:
            for surface in ("dark", "paper"):
                with self.subTest(f"{theme}/{surface}"):
                    out = self.out / f"{theme}-{surface}"
                    spec = profiles.load_spec(write_json(self.out / "s.json", {
                        "slug": theme, "eyebrow": "THEME",
                        "headline": "A Claim Worth Reading Twice",
                        "accent": "Worth Reading", "subhead": "One line under it.",
                        "kicker": "ONE · TWO · THREE",
                        "theme": theme, "surface": surface, "art": "none"}))
                    r = compose.render_all(spec, out, ["x"])[0]
                    entry = kit.write_manifest(spec, out, "pil", [r])["canvases"][0]
                    issues, _ = verify.check(r["path"], "x", out, entry)
                    self.assertEqual(issues, [])


# ── the Pillow renderer ──────────────────────────────────────────────────────

class PillowRenderer(TmpDirCase):

    def test_renders_every_canvas_at_the_exact_size(self):
        for r in example_kit(SIGNAL_SPEC)["results"].values():
            with self.subTest(r["canvas"]):
                self.assertEqual(size_of(r["path"]), (r["w"], r["h"]))
                self.assertEqual(r["warnings"], [])

    def test_diagram_reaches_the_artwork_column(self):
        """Assert on ink in the art column, not only on the absence of a warning."""
        r = example_kit(SIGNAL_SPEC)["results"]["banner"]
        art = Image.open(r["path"]).convert("RGB").crop(art_column(r["payload"]))
        self.assertGreater(verify.ink_fraction(art), 0.004)
        self.assertEqual(r["warnings"], [])

    def test_art_photo_is_placed(self):
        d = self.out / "spec"
        d.mkdir()
        solid(d / "rack.png", (200, 60, 60), (800, 600))
        spec = profiles.load_spec(write_json(d / "s.json", {
            "slug": "rack", "headline": "A Rack", "surface": "navy",
            "art": "photo", "art_img": "rack.png"}))
        r = compose.render_all(spec, self.out, ["banner"])[0]
        box = art_column(r["payload"])
        # The photo is the only strongly red thing on a navy canvas: count the
        # pixels that are both high in red and low in green.
        red, green, _ = Image.open(r["path"]).convert("RGB").crop(box).split()
        strong_red = ImageChops.darker(red.point(lambda v: 255 if v > 150 else 0),
                                       green.point(lambda v: 255 if v < 110 else 0))
        area = (box[2] - box[0]) * (box[3] - box[1])
        self.assertGreater(strong_red.histogram()[255], area * 0.5)

    def test_reports_the_glyph_box_for_both_size_classes(self):
        r = example_kit(SIGNAL_SPEC)["results"]["banner"]
        box = r["text_box"]
        self.assertIsNotNone(box["display"])
        self.assertIsNotNone(box["body"])
        for kind, b in box.items():
            with self.subTest(kind):
                self.assertLess(b[0], b[2])
                self.assertLess(b[1], b[3])
                # Inside the safe area, which is what the layout promises.
                self.assertGreaterEqual(b[0], profiles.CANVASES["banner"]["inset_x"] - 2)


# ── the manifest ─────────────────────────────────────────────────────────────

class Manifest(unittest.TestCase):

    def test_manifest_describes_every_rendered_file(self):
        k = example_kit(CRIMSON_SPEC)
        on_disk = json.loads((k["out"] / kit.MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(on_disk, k["manifest"])
        self.assertEqual([c["canvas"] for c in on_disk["canvases"]], profiles.ORDER)
        for entry in on_disk["canvases"]:
            with self.subTest(entry["canvas"]):
                self.assertTrue((k["out"] / entry["file"]).is_file())
                self.assertEqual(entry["surface"], "paper")
                self.assertIn("text_box", entry)
        # crimson-code drops the artwork on the two portrait canvases.
        art = {c["canvas"]: c["art"] for c in on_disk["canvases"]}
        self.assertEqual(art["instagram"], "none")
        self.assertEqual(art["banner"], "code")


# ── the verifier, on good output ─────────────────────────────────────────────

class VerifyPositive(TmpDirCase):

    def test_examples_pass_every_check(self):
        for spec_path in ALL_SPECS:
            k = example_kit(spec_path)
            for entry in k["manifest"]["canvases"]:
                with self.subTest(f"{spec_path.name}/{entry['canvas']}"):
                    issues, _ = verify.check(k["out"] / entry["file"], entry["canvas"],
                                             k["out"], entry)
                    self.assertEqual(issues, [])

    def test_verify_still_maps_files_without_a_manifest(self):
        shutil.copytree(example_kit(SIGNAL_SPEC)["out"], self.out, dirs_exist_ok=True)
        (self.out / kit.MANIFEST).unlink()
        argv = sys.argv
        sys.argv = ["verify", str(self.out)]
        try:
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(verify.main(), 0)
        finally:
            sys.argv = argv
        report = captured.getvalue()
        self.assertIn("no _kit.json", report)
        for canvas in profiles.ORDER:
            self.assertIn(canvas, report)


# ── the verifier, on output it should reject ─────────────────────────────────

class VerifyNegative(TmpDirCase):

    def banner_copy(self) -> tuple[Path, dict]:
        """A private copy of the navy example's banner PNG (no webp) and its
        manifest entry, to break without touching the shared kit."""
        k = example_kit(SIGNAL_SPEC)
        src = k["results"]["banner"]["path"]
        dst = self.out / src.name
        shutil.copy(src, dst)
        entry = next(c for c in k["manifest"]["canvases"] if c["canvas"] == "banner")
        return dst, entry

    def render_one(self, spec_path, canvas):
        spec = profiles.load_spec(spec_path)
        r = compose.render_all(spec, self.out, [canvas])[0]
        manifest = kit.write_manifest(spec, self.out, "pil", [r])
        return r["path"], manifest["canvases"][0]

    def test_content_in_the_cropped_strip_is_caught(self):
        path, entry = self.banner_copy()
        clean, _ = verify.check(path, "banner", self.out, entry)
        self.assertEqual([i for i in clean if "strip" in i], [],
                         "control render should be clean")

        with Image.open(path) as src:
            im = src.convert("RGB")
        d = ImageDraw.Draw(im)
        # A caption sitting where the 7:3 crop will remove it.
        d.rectangle([200, 20, 1400, 70], fill=(255, 255, 255))
        im.save(path)
        issues, _ = verify.check(path, "banner", self.out, entry)
        self.assertTrue(any("top strip" in i for i in issues), issues)

    def test_low_contrast_type_is_caught(self):
        """White type over a white photograph must not pass. The scrim clears
        rightwards on a wide canvas, so the end of the headline lands on bare
        photo."""
        d = self.out / "spec"
        d.mkdir()
        solid(d / "white.png", (255, 255, 255), (2000, 1200))
        spec_path = write_json(d / "s.json", {
            "slug": "blown-out", "headline": "Every Word Of This Is Invisible",
            "subhead": "And so is this line.", "kicker": "UNREADABLE",
            "surface": "photo", "photo": "white.png", "art": "none"})
        path, entry = self.render_one(spec_path, "banner")
        issues, _ = verify.check(path, "banner", self.out, entry)
        self.assertTrue(any("below the" in i for i in issues), issues)

    def test_recoloured_lockup_is_caught(self):
        """The ".AI" keeps the brand cyan whatever the theme."""
        spec = profiles.load_spec(EMBER_SPEC)
        r = compose.render_all(spec, self.out, ["banner"])[0]
        entry = kit.write_manifest(spec, self.out, "pil", [r])["canvases"][0]
        clean, _ = verify.check(r["path"], "banner", self.out, entry)
        self.assertEqual([i for i in clean if "lockup" in i], [],
                         "control render should carry the brand cyan")

        # Repaint the cyan in the theme's orange, as a themed lockup would be.
        with Image.open(r["path"]) as src:
            im = src.convert("RGB")
        target = ImageColor.getrgb(profiles.BRAND_CYAN)
        mask = Image.merge("RGB", [
            ch.point(lambda x, v=v: 255 if abs(x - v) <= 12 else 0)
            for ch, v in zip(im.split(), target)]).convert("L").point(
                lambda x: 255 if x > 250 else 0)
        im.paste(ImageColor.getrgb("#F26A1B"), mask=mask)
        im.save(r["path"])
        issues, _ = verify.check(r["path"], "banner", self.out, entry)
        self.assertTrue(any("lockup" in i for i in issues), issues)

    def test_wrong_dimensions_are_caught(self):
        path, entry = self.banner_copy()
        with Image.open(path) as im:
            im.resize((1200, 655)).save(path)
        issues, _ = verify.check(path, "banner", self.out, entry)
        self.assertTrue(any("wrong size" in i for i in issues), issues)

    def test_missing_webp_is_caught_for_website_files(self):
        path, entry = self.banner_copy()
        issues, _ = verify.check(path, "banner", self.out, entry)
        self.assertTrue(any("webp" in i for i in issues), issues)

    def test_photo_surface_downgrades_the_crop_check_to_a_note(self):
        """Full-bleed photography is meant to run into the strip, so on a photo
        surface the crop check is a note, not a failure."""
        d = self.out / "spec"
        d.mkdir()
        # Something with edges everywhere, which is what trips the ink test.
        noise = Image.effect_noise((1600, 1000), 90).convert("RGB")
        noise.save(d / "busy.png")
        spec_path = write_json(d / "s.json", {
            "slug": "busy", "headline": "A Photograph With Texture",
            "surface": "photo", "photo": "busy.png", "art": "none"})
        path, entry = self.render_one(spec_path, "banner")
        issues, notes = verify.check(path, "banner", self.out, entry)
        self.assertEqual([i for i in issues if "strip" in i], [])
        self.assertTrue(any("strip" in n and "photo surface" in n for n in notes),
                        notes)


# ── the two engines must agree ───────────────────────────────────────────────

@unittest.skipUnless(render.available(), "Playwright/Chromium not installed")
class EngineParity(unittest.TestCase):
    """Every shipped example through Chromium, rendered once for both tests."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.kits = {}
        for spec_path in ALL_SPECS:
            out = Path(cls.tmp.name) / spec_path.stem
            spec = profiles.load_spec(spec_path)
            results = render.render_all(spec, out, profiles.ORDER)
            for r in results:
                if profiles.CANVASES[r["canvas"]]["webp_kb"]:
                    kit.to_webp(r["path"])
            cls.kits[spec_path] = dict(
                out=out, results=results,
                manifest=kit.write_manifest(spec, out, "chromium", results))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_both_engines_produce_the_same_kit(self):
        for spec_path, k in self.kits.items():
            pil = example_kit(spec_path)["results"]
            self.assertEqual([r["canvas"] for r in k["results"]], list(pil))
            for a in k["results"]:
                b = pil[a["canvas"]]
                with self.subTest(f"{spec_path.stem}/{a['canvas']}"):
                    self.assertEqual(a["path"].name, b["path"].name)
                    self.assertEqual(size_of(a["path"]), size_of(b["path"]))
                    for kind in ("display", "body"):
                        self.assertIsNotNone(a["text_box"][kind])
                        self.assertIsNotNone(b["text_box"][kind])

    def test_chromium_output_passes_verification(self):
        for spec_path, k in self.kits.items():
            for entry in k["manifest"]["canvases"]:
                with self.subTest(f"{spec_path.stem}/{entry['canvas']}"):
                    issues, _ = verify.check(k["out"] / entry["file"],
                                             entry["canvas"], k["out"], entry)
                    self.assertEqual(issues, [])

    def test_chromium_keeps_the_lockup_cyan_on_a_themed_kit(self):
        """The template must not let the theme reach the '.AI'."""
        for r in self.kits[EMBER_SPEC]["results"]:
            with self.subTest(r["canvas"]):
                with Image.open(r["path"]) as im:
                    px = verify.brand_cyan_pixels(im.convert("RGB"))
                self.assertGreater(px, verify.LOCKUP_MIN_PIXELS)


if __name__ == "__main__":
    unittest.main(verbosity=2)

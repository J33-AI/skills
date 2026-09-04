"""Tests for the text layer of render_campaign.py: title splitting, wrapping, colour choice, contrast."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import render_campaign as rc  # noqa: E402

TITLE = "CORS, XSS, SQL Injection & CSRF: 4 Web Attacks Explained"
DARK = (30, 30, 34)
LIGHT = (235, 232, 226)
MID_GREY = (128, 128, 128)


def flat_plate(color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (2400, 1600), color)


def test_split_title_on_first_colon():
    assert rc.split_title(TITLE) == ("CORS, XSS, SQL Injection & CSRF", "4 Web Attacks Explained")
    assert rc.split_title("No colon here") == ("No colon here", "")
    assert rc.split_title("Trailing colon:") == ("Trailing colon:", "")


def test_balanced_lines_keeps_number_with_its_noun_and_avoids_stub_last_line():
    fnt = rc.font(60, 600)
    # Narrow enough that greedy wrapping would break right after the "4".
    width = round(fnt.getlength("CORS, XSS, SQL Injection & CSRF: 4 Web") * 0.98)
    lines = rc.balanced_lines(TITLE, fnt, width, max_lines=3)
    assert len(lines) == 2
    assert not lines[0].endswith("4")
    assert not lines[0].endswith("&")
    assert fnt.getlength(lines[-1]) >= width * 0.3


def test_balanced_lines_returns_none_when_a_word_cannot_fit():
    assert rc.balanced_lines("Supercalifragilistic", rc.font(60, 600), 50, max_lines=3) is None


def test_balanced_lines_gives_up_early_when_too_many_lines_are_needed():
    thirty_words = " ".join(["Authentication"] * 30)
    assert rc.balanced_lines(thirty_words, rc.font(60, 600), 600, max_lines=3) is None


@pytest.mark.parametrize("plate, expected", [(DARK, rc.PAPER), (LIGHT, rc.CHARCOAL)])
def test_text_colour_follows_background(plate, expected):
    _, color, _ = rc.render_one(
        "banner", (1672, 941), flat_plate(plate), TITLE, "Web Security", None, (0.5, 0.5), "top", None, None
    )
    assert color == expected


def test_text_colour_override_wins():
    _, color, _ = rc.render_one(
        "banner", (1672, 941), flat_plate(DARK), TITLE, "", None, (0.5, 0.5), "top", (255, 255, 255), None
    )
    assert color == (255, 255, 255)


@pytest.mark.parametrize("plate", [DARK, LIGHT, MID_GREY])
@pytest.mark.parametrize("anchor", ["top", "bottom"])
def test_every_surface_renders_at_size_and_reaches_the_contrast_target(plate, anchor):
    for name, (size, _) in rc.FORMATS.items():
        image, _, contrast = rc.render_one(
            name, size, flat_plate(plate), TITLE, "Web Security", None, (0.5, 0.5), anchor, None, None
        )
        assert image.size == size
        assert contrast >= rc.TARGET_CONTRAST, f"{name} on {plate} anchored {anchor}: {contrast:.1f}:1"


def test_too_long_title_asks_for_a_shorter_one():
    with pytest.raises(ValueError, match="shorter title"):
        rc.render_one(
            "thumbnail", (800, 600), flat_plate(DARK), " ".join(["Authentication"] * 30), "", None,
            (0.5, 0.5), "top", None, None,
        )

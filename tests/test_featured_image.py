"""
tests/test_featured_image.py

Tests for the generated featured-image card (plan section 4.4).
"""

from PIL import Image

from blog_engine.core.featured_image import render

# Pixel inside the lane band (top accent bar, y < BAND_HEIGHT)
BAND_PIXEL = (600, 10)

LANE_RGB = {
    "consulting": (0x93, 0xB4, 0xFF),  # #93b4ff
    "building": (0x8E, 0xD5, 0xFF),    # #8ed5ff
}


def test_render_produces_1200x630_png(tmp_path):
    out = tmp_path / "card.png"
    render("A Test Title", "Dev Notes", "building", str(out))
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (1200, 630)


def test_lane_band_consulting(tmp_path):
    out = tmp_path / "card.png"
    render("A Test Title", "Convoso", "consulting", str(out))
    with Image.open(out) as img:
        assert img.getpixel(BAND_PIXEL) == LANE_RGB["consulting"]


def test_lane_band_building(tmp_path):
    out = tmp_path / "card.png"
    render("A Test Title", "Games", "building", str(out))
    with Image.open(out) as img:
        assert img.getpixel(BAND_PIXEL) == LANE_RGB["building"]


def test_lane_none_falls_back_to_consulting_colour(tmp_path):
    out = tmp_path / "card.png"
    render("A Test Title", "Misc", None, str(out))
    with Image.open(out) as img:
        assert img.getpixel(BAND_PIXEL) == LANE_RGB["consulting"]


def test_render_succeeds_with_font_path_none(tmp_path):
    out = tmp_path / "card.png"
    render("A Test Title", "Dev Notes", "building", str(out), font_path=None)
    with Image.open(out) as img:
        assert img.size == (1200, 630)


def test_render_succeeds_with_missing_font_file(tmp_path):
    out = tmp_path / "card.png"
    render(
        "A Test Title",
        "Dev Notes",
        "building",
        str(out),
        font_path=str(tmp_path / "missing.ttf"),
    )
    assert out.exists()

"""
blog_engine/core/featured_image.py

Generate branded featured images for blog posts, per
docs/notes/2026-09-23-blog-redesign-plan.md section 4.4: a 1200x630 card in
the lane colour on dark navy #0b1220, title in Inter 800, small category
label, brand mark bottom-left. The same image serves as OpenGraph and
Dev.to cover.
"""

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1200
HEIGHT = 630
BACKGROUND = "#0b1220"

# Dark-mode lane accents from the plan's section 4.2 -- the card always
# renders on the dark background regardless of site light/dark mode.
LANE_COLORS = {
    "consulting": "#93b4ff",
    "building": "#8ed5ff",
}
DEFAULT_LANE_COLOR = LANE_COLORS["consulting"]

TEXT_COLOR = "#e5e9f2"
MUTED_COLOR = "#9aa6bd"
BRAND_MARK = "RFD IT Services"

BAND_HEIGHT = 24  # lane colour band across the top edge
MARGIN = 72
TITLE_SIZE = 64
LABEL_SIZE = 28
BRAND_SIZE = 24


def _load_font(font_path: str | None, size: int):
    """
    Load `font_path` at `size`; fall back to ImageFont.load_default() when
    font_path is None, missing, or truetype raises OSError. Rendering must
    succeed either way — no font file is guaranteed present.
    """
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_title(title: str, draw: ImageDraw.ImageDraw, font, max_width: int) -> list[str]:
    """Simple word-wrap: split on spaces, keep each line within max_width."""
    lines = []
    current = ""
    for word in title.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render(
    title: str,
    category: str,
    lane: str | None,
    out_path: str,
    font_path: str | None = None
) -> None:
    """
    Render a 1200x630 PNG featured-image card to `out_path`.

    `lane` ("consulting" | "building" | None) picks the band and label
    colour; None falls back to the consulting accent.
    """
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    accent = LANE_COLORS.get(lane, DEFAULT_LANE_COLOR)

    # Lane colour band across the top edge
    draw.rectangle([(0, 0), (WIDTH, BAND_HEIGHT)], fill=accent)

    title_font = _load_font(font_path, TITLE_SIZE)
    label_font = _load_font(font_path, LABEL_SIZE)
    brand_font = _load_font(font_path, BRAND_SIZE)

    if category:
        draw.text((MARGIN, 96), str(category).upper(), font=label_font, fill=accent)

    try:
        ascent, descent = title_font.getmetrics()
        line_height = ascent + descent + 12
    except AttributeError:
        line_height = TITLE_SIZE + 12

    y = 160
    for line in _wrap_title(str(title or ""), draw, title_font, WIDTH - 2 * MARGIN):
        draw.text((MARGIN, y), line, font=title_font, fill=TEXT_COLOR)
        y += line_height

    draw.text((MARGIN, HEIGHT - MARGIN), BRAND_MARK, font=brand_font, fill=MUTED_COLOR)

    image.save(out_path, "PNG")

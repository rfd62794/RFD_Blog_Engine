#!/usr/bin/env python3
"""Build the rfd-blog WordPress child theme into theme/dist/rfd-blog.zip.

Stdlib only. Verifies theme.json parses, that every non-font file the theme
references exists, reports missing font files (they are an install-time input
Robert supplies, not a build defect), and zips the theme directory.

Exits 0 when the zip is written — fonts absent or present. Exits non-zero only
on a real defect: invalid theme.json or a missing referenced file.
"""

import json
import sys
import zipfile
from pathlib import Path

THEME_ROOT = Path(__file__).resolve().parent
THEME_DIR = THEME_ROOT / "rfd-blog"
DIST_DIR = THEME_ROOT / "dist"
ZIP_PATH = DIST_DIR / "rfd-blog.zip"

# Every file the theme's style.css header, functions.php enqueue calls, and
# block templates reference. Missing any of these is a build defect.
REQUIRED_FILES = [
    "style.css",
    "theme.json",
    "functions.php",
    "templates/home.html",
    "templates/single.html",
    "templates/archive.html",
    "parts/header.html",
    "parts/footer.html",
    "patterns/lane-cta-consulting.php",
    "patterns/lane-cta-building.php",
]

FONT_SRC_PREFIX = "file:./"


def fail(message: str) -> "SystemExit":
    print(f"BUILD FAILED: {message}", file=sys.stderr)
    return SystemExit(1)


def main() -> int:
    if not THEME_DIR.is_dir():
        raise fail(f"theme directory missing: {THEME_DIR}")

    # 1. theme.json must be valid JSON.
    theme_json_path = THEME_DIR / "theme.json"
    try:
        theme_json = json.loads(theme_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise fail(f"theme.json is not valid JSON: {exc}")

    # 2. Every non-font file the theme references must exist on disk.
    missing = [f for f in REQUIRED_FILES if not (THEME_DIR / f).is_file()]
    if missing:
        raise fail("missing theme files: " + ", ".join(missing))

    style_css = (THEME_DIR / "style.css").read_text(encoding="utf-8")
    if "Theme Name:" not in style_css or "Template:" not in style_css:
        raise fail("style.css is missing its child-theme header block")
    functions_php = (THEME_DIR / "functions.php").read_text(encoding="utf-8")
    if "wp_enqueue_style" not in functions_php:
        raise fail("functions.php does not enqueue the stylesheet")

    # 3. Report missing font files listed in theme.json fontFace entries.
    #    Fonts are supplied at install time — absent here is expected, not fatal.
    font_srcs = []
    for family in theme_json.get("settings", {}).get("typography", {}).get("fontFamilies", []):
        for face in family.get("fontFace", []):
            for src in face.get("src", []):
                if isinstance(src, str) and src.startswith(FONT_SRC_PREFIX):
                    font_srcs.append(src[len(FONT_SRC_PREFIX):])
    missing_fonts = [s for s in font_srcs if not (THEME_DIR / s).is_file()]
    if missing_fonts:
        print("Missing font files (expected - Robert supplies these at install):")
        for src in missing_fonts:
            print(f"  - {src}")
    else:
        print("All font files present.")

    # 4. Zip the theme directory.
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in THEME_DIR.rglob("*") if p.is_file())
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, f"rfd-blog/{path.relative_to(THEME_DIR).as_posix()}")
    print(f"Wrote {ZIP_PATH} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

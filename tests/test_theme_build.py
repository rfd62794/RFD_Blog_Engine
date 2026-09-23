"""Tests for theme/build.py and the rfd-blog child theme files.

No WordPress runtime is involved — these verify the theme files on disk and
the zip that build.py produces.
"""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
THEME_DIR = REPO_ROOT / "theme" / "rfd-blog"
BUILD_PY = REPO_ROOT / "theme" / "build.py"
ZIP_PATH = REPO_ROOT / "theme" / "dist" / "rfd-blog.zip"

EXPECTED_THEME_FILES = [
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

EXPECTED_PALETTE_SLUGS = {
    "bg", "surface", "text", "muted", "line",
    "accent", "accent-soft", "result",
    "lane-consulting", "lane-building",
}

EXPECTED_FONT_FILES = [
    "assets/fonts/inter-latin-400-normal.woff2",
    "assets/fonts/inter-latin-600-normal.woff2",
    "assets/fonts/inter-latin-800-normal.woff2",
    "assets/fonts/jetbrains-mono-latin-400-normal.woff2",
]


def run_build() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BUILD_PY)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_theme_files_exist():
    for rel in EXPECTED_THEME_FILES:
        assert (THEME_DIR / rel).is_file(), f"missing theme file: {rel}"


def test_theme_json_valid_with_palette():
    theme_json = json.loads((THEME_DIR / "theme.json").read_text(encoding="utf-8"))
    palette = theme_json["settings"]["color"]["palette"]
    slugs = {entry["slug"] for entry in palette}
    assert EXPECTED_PALETTE_SLUGS <= slugs


def test_theme_json_has_two_font_face_families():
    theme_json = json.loads((THEME_DIR / "theme.json").read_text(encoding="utf-8"))
    families = theme_json["settings"]["typography"]["fontFamilies"]
    with_faces = [f for f in families if f.get("fontFace")]
    assert len(with_faces) == 2
    srcs = [
        src
        for family in with_faces
        for face in family["fontFace"]
        for src in face["src"]
    ]
    assert all(src.startswith("file:./assets/fonts/") for src in srcs)


def test_theme_json_layout_widths():
    theme_json = json.loads((THEME_DIR / "theme.json").read_text(encoding="utf-8"))
    layout = theme_json["settings"]["layout"]
    assert layout["contentSize"] == "720px"
    assert layout["wideSize"] == "1080px"


def test_style_css_child_header_and_tokens():
    css = (THEME_DIR / "style.css").read_text(encoding="utf-8")
    assert "Theme Name: RFD Blog" in css
    assert "Template: twentytwentyfive" in css
    assert "prefers-color-scheme: dark" in css
    assert "--lane-building" in css
    assert "--lane-consulting" in css
    assert ".arcade-card" in css


def test_functions_php_lane_map():
    php = (THEME_DIR / "functions.php").read_text(encoding="utf-8")
    assert "wp_enqueue_style" in php
    for slug in (
        "contact-center", "convoso", "dnc-compliance", "dialer-ops",
        "sheets-automation", "dev-notes", "games", "agents-automation",
        "sessions",
    ):
        assert slug in php
    assert "body_class" in php
    assert "post_class" in php


def test_build_succeeds_and_reports_missing_fonts():
    result = run_build()
    assert result.returncode == 0, result.stderr
    # Fonts are supplied at install time; build.py must report them missing
    # without failing.
    for font in EXPECTED_FONT_FILES:
        assert font in result.stdout


def test_build_writes_zip_with_expected_files():
    result = run_build()
    assert result.returncode == 0, result.stderr
    assert ZIP_PATH.is_file()
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = set(zf.namelist())
    for rel in EXPECTED_THEME_FILES:
        assert f"rfd-blog/{rel}" in names, f"zip missing rfd-blog/{rel}"

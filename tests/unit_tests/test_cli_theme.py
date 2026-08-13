"""Tests for the brand palette, glyph sets, and gradient helpers."""

from __future__ import annotations

from agentflow_cli.cli.core.theme import (
    ASCII_GLYPHS,
    BRAND_RAMP,
    UNICODE_GLYPHS,
    dim_hex,
    glyphs_for,
    gradient_rule,
    gradient_text,
    sample_ramp,
)


def test_ramp_endpoints_are_exact() -> None:
    assert sample_ramp(0.0) == BRAND_RAMP[0]
    assert sample_ramp(1.0) == BRAND_RAMP[-1]


def test_ramp_is_clamped_outside_the_unit_interval() -> None:
    assert sample_ramp(-5.0) == BRAND_RAMP[0]
    assert sample_ramp(12.0) == BRAND_RAMP[-1]


def test_ramp_interpolates_between_stops() -> None:
    # A midpoint between two stops must be a new color, not either neighbour,
    # or wide gradient bars would show visible banding.
    midpoint = sample_ramp(0.5 / (len(BRAND_RAMP) - 1))
    assert midpoint not in {BRAND_RAMP[0], BRAND_RAMP[1]}
    assert midpoint.startswith("#") and len(midpoint) == 7


def test_ramp_handles_degenerate_palettes() -> None:
    assert sample_ramp(0.4, ()) == "#ffffff"
    assert sample_ramp(0.4, ("#123456",)) == "#123456"


def test_dim_hex_scales_toward_black_and_clamps() -> None:
    assert dim_hex("#ffffff", 0.5) == "#808080"
    assert dim_hex("#ffffff", 0.0) == "#000000"
    assert dim_hex("#abcdef", 5.0) == "#abcdef"


def test_gradient_text_styles_every_character_distinctly() -> None:
    text = gradient_text("agentflow", bold=True)
    assert text.plain == "agentflow"
    styles = [span.style for span in text.spans]
    assert len(styles) == len("agentflow")
    assert all(style.startswith("bold #") for style in styles)
    assert len(set(styles)) > 1


def test_gradient_text_offset_shifts_the_sweep() -> None:
    base = [span.style for span in gradient_text("agentflow").spans]
    shifted = [span.style for span in gradient_text("agentflow", offset=0.5).spans]
    assert base != shifted


def test_gradient_rule_matches_requested_width() -> None:
    rule = gradient_rule(24, glyphs=UNICODE_GLYPHS)
    assert len(rule.plain) == 24
    assert set(rule.plain) == {UNICODE_GLYPHS.rule}


def test_glyph_selection_follows_encoding_support() -> None:
    assert glyphs_for(True) is UNICODE_GLYPHS
    assert glyphs_for(False) is ASCII_GLYPHS


def test_ascii_glyphs_are_pure_ascii() -> None:
    for field in (
        ASCII_GLYPHS.check,
        ASCII_GLYPHS.cross,
        ASCII_GLYPHS.arrow,
        ASCII_GLYPHS.pending,
        ASCII_GLYPHS.tree_branch,
        ASCII_GLYPHS.cursor,
        *ASCII_GLYPHS.spinner,
        *ASCII_GLYPHS.shades,
    ):
        assert field.isascii(), f"{field!r} is not ASCII"

"""Brand palette, glyph sets, and gradient helpers for the Agentflow terminal UI.

Everything visual in the CLI resolves through this module so a single palette
change restyles intros, timelines, tables, and completion screens at once.
Glyphs are separated from color because a terminal can support one without the
other: ASCII fallbacks keep the layout identical when Unicode is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from rich.theme import Theme


# Cyan -> violet -> magenta. Sampled continuously, so stop count only affects
# how much hue travel each segment carries, never the smoothness of the result.
BRAND_RAMP: tuple[str, ...] = (
    "#22d3ee",
    "#38bdf8",
    "#60a5fa",
    "#818cf8",
    "#a78bfa",
    "#c084fc",
    "#e879f9",
    "#f472b6",
)

# Used for rows that are done, running, and not started, respectively.
STATE_RAMP: tuple[str, ...] = ("#34d399", "#22d3ee", "#4b5563")

AGENTFLOW_THEME = Theme(
    {
        "agentflow.success": "bold #34d399",
        "agentflow.error": "bold #f87171",
        "agentflow.warning": "bold #fbbf24",
        "agentflow.info": "#38bdf8",
        "agentflow.muted": "dim #94a3b8",
        "agentflow.title": "bold #c084fc",
        "agentflow.brand": "bold #22d3ee",
        "agentflow.command": "bold #f8fafc",
        "agentflow.progress": "#38bdf8",
        "agentflow.accent": "#a78bfa",
        "agentflow.pending": "#4b5563",
        "agentflow.rule": "#312e81",
        "agentflow.chip": "bold #f8fafc on #4c1d95",
        "agentflow.header": "on #16161f",
        "agentflow.elapsed": "dim #64748b",
    }
)


@dataclass(frozen=True)
class Glyphs:
    """Symbol set for one invocation, chosen by terminal encoding support."""

    check: str
    cross: str
    warn: str
    info: str
    bullet: str
    arrow: str
    pending: str
    active: str
    skipped: str
    rule: str
    thin_rule: str
    node: str
    diamond: str
    caret: str
    block: str
    cursor: str
    tree_stem: str
    tree_branch: str
    tree_end: str
    spinner: tuple[str, ...]
    shades: tuple[str, ...]


UNICODE_GLYPHS = Glyphs(
    check="✓",
    cross="✗",
    warn="▲",
    info="•",
    bullet="•",
    arrow="→",
    pending="○",
    active="◆",
    skipped="⊘",
    rule="━",
    thin_rule="─",
    node="◉",
    diamond="◆",
    caret="▸",
    block="█",
    cursor="▌",
    tree_stem="┃",
    tree_branch="┣",
    tree_end="┗",
    spinner=("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"),
    shades=(" ", "░", "▒", "▓", "█"),
)

ASCII_GLYPHS = Glyphs(
    check="OK",
    cross="X",
    warn="!",
    info="*",
    bullet="*",
    arrow="->",
    pending="o",
    active="*",
    skipped="-",
    rule="=",
    thin_rule="-",
    node="O",
    diamond="*",
    caret=">",
    block="#",
    cursor="|",
    tree_stem="|",
    tree_branch="+",
    tree_end="\\",
    spinner=("|", "/", "-", "\\"),
    shades=(" ", ".", ":", "+", "#"),
)


def glyphs_for(unicode: bool) -> Glyphs:
    """Return the glyph set matching the terminal's encoding support."""
    return UNICODE_GLYPHS if unicode else ASCII_GLYPHS


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def sample_ramp(position: float, ramp: tuple[str, ...] = BRAND_RAMP) -> str:
    """Sample a continuous color from ``ramp`` at ``position`` in ``[0, 1]``.

    Interpolating between stops rather than snapping to the nearest one is what
    keeps a wide gradient bar from showing visible banding.
    """
    if not ramp:
        return "#ffffff"
    if len(ramp) == 1:
        return ramp[0]

    clamped = min(max(position, 0.0), 1.0)
    scaled = clamped * (len(ramp) - 1)
    index = int(scaled)
    if index >= len(ramp) - 1:
        return ramp[-1]

    blend = scaled - index
    start = _hex_to_rgb(ramp[index])
    end = _hex_to_rgb(ramp[index + 1])
    return _rgb_to_hex(
        (
            round(start[0] + (end[0] - start[0]) * blend),
            round(start[1] + (end[1] - start[1]) * blend),
            round(start[2] + (end[2] - start[2]) * blend),
        )
    )


def dim_hex(value: str, factor: float) -> str:
    """Scale a hex color toward black, for pending or background elements."""
    red, green, blue = _hex_to_rgb(value)
    scale = min(max(factor, 0.0), 1.0)
    return _rgb_to_hex((round(red * scale), round(green * scale), round(blue * scale)))


def gradient_text(
    value: str,
    *,
    ramp: tuple[str, ...] = BRAND_RAMP,
    bold: bool = False,
    offset: float = 0.0,
    span: float = 1.0,
) -> Text:
    """Paint ``value`` with a per-character sweep through ``ramp``.

    ``offset`` shifts the sweep so successive frames can animate a shimmer
    without rebuilding the palette.
    """
    text = Text()
    length = max(len(value), 1)
    weight = "bold " if bold else ""
    for index, character in enumerate(value):
        position = (offset + (index / length) * span) % 1.0
        text.append(character, style=f"{weight}{sample_ramp(position, ramp)}")
    return text


def gradient_rule(
    width: int,
    *,
    glyphs: Glyphs,
    thin: bool = False,
    offset: float = 0.0,
) -> Text:
    """Build a full-width gradient rule used to frame branded sections."""
    character = glyphs.thin_rule if thin else glyphs.rule
    return gradient_text(character * max(width, 1), offset=offset)

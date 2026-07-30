"""Terminal-native animation engine for the Agentflow CLI.

The intro always plays on the full canvas; what differs is who owns that canvas.
Inside an :class:`~agentflow_cli.cli.core.screen.AppFrame` the frame already
holds the alternate screen and keeps it, so the sequence renders in place and
collapses into the frame's pinned chrome. Without a frame the intro claims a
temporary screen of its own and hands the terminal back, then prints a durable
header — because a released alternate screen is discarded, and everything the
command goes on to print has to survive in the normal buffer.

Frames are generated from a normalized ``0.0 -> 1.0`` timeline rather than a
fixed frame list so the same choreography adapts to terminal width, refresh
rate, and the reduced-motion budget without being re-authored.
"""

from __future__ import annotations

import math
import time
from contextlib import nullcontext

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.text import Text

from agentflow_cli.cli.constants import CLI_VERSION
from agentflow_cli.cli.core.screen import BACKGROUND
from agentflow_cli.cli.core.theme import (
    BRAND_RAMP,
    Glyphs,
    dim_hex,
    glyphs_for,
    gradient_rule,
    gradient_text,
    sample_ramp,
)


INTRO_DURATION_SECONDS = 1.25
INTRO_FPS = 30
_MIN_CINEMATIC_HEIGHT = 16
# Column distance over which the reveal front and the shimmer stay lit.
_REVEAL_FRONT_WIDTH = 1.6
_SHIMMER_WIDTH = 2.5
_MIN_CINEMATIC_WIDTH = 62

# 5x5 block glyphs. Only the letters in "AGENTFLOW" are needed; anything else
# falls back to the compact wordmark.
_BLOCK_FONT: dict[str, tuple[str, ...]] = {
    "A": (" ███ ", "█   █", "█████", "█   █", "█   █"),
    "G": (" ████", "█    ", "█  ██", "█   █", " ████"),
    "E": ("█████", "█    ", "████ ", "█    ", "█████"),
    "N": ("█   █", "██  █", "█ █ █", "█  ██", "█   █"),
    "T": ("█████", "  █  ", "  █  ", "  █  ", "  █  "),
    "F": ("█████", "█    ", "████ ", "█    ", "█    "),
    "L": ("█    ", "█    ", "█    ", "█    ", "█████"),
    "O": (" ███ ", "█   █", "█   █", "█   █", " ███ "),
    "W": ("█   █", "█   █", "█ █ █", "██ ██", "█   █"),
}
_WORDMARK = "AGENTFLOW"
_BLOCK_ROWS = 5

# Each command reveals its own pipeline during the intro, so the animation
# doubles as a preview of what the command is about to do.
_SIGNATURES: dict[str, tuple[str, ...]] = {
    "api": ("config", "runtime", "server", "ready"),
    "dev": ("config", "runtime", "server", "playground"),
    "play": ("config", "runtime", "server", "playground"),
    "init": ("template", "graph", "config", "project"),
    "build": ("source", "deps", "image", "ship"),
    "test": ("collect", "run", "assert", "report"),
    "eval": ("discover", "load", "score", "report"),
    "audit": ("python", "core", "config", "port"),
    "skills": ("detect", "resolve", "install", "activate"),
}
_DEFAULT_SIGNATURE = ("boot", "load", "ready")

_TAGLINES: dict[str, str] = {
    "api": "Serving your agent over REST and WebSocket.",
    "dev": "Local agent runtime with live reload.",
    "play": "Local agent runtime, wired to the playground.",
    "init": "Scaffolding a production-shaped agent project.",
    "build": "Packaging your agent for deployment.",
    "test": "Exercising your agent's test suite.",
    "eval": "Scoring your agent against evaluation sets.",
    "audit": "Auditing your Agentflow environment.",
}
_DEFAULT_TAGLINE = "Build, run, and inspect intelligent agent systems."


def render_command_intro(
    console: Console,
    *,
    command: str,
    subtitle: str | None,
    unicode: bool,
    persistent_screen: bool = False,
) -> None:
    """Play the command intro on the full canvas.

    ``persistent_screen`` means the caller already owns an alternate screen that
    it intends to keep. The sequence then plays in place and skips the durable
    header, because the caller pins its own chrome once the intro finishes.
    """
    glyphs = glyphs_for(unicode)
    if _can_play_cinematic(console):
        _play_cinematic(
            console,
            command=command,
            subtitle=subtitle,
            glyphs=glyphs,
            own_screen=not persistent_screen,
        )
    else:
        _play_inline(console, command=command, glyphs=glyphs)

    if persistent_screen:
        return

    render_session_header(
        console,
        command=command,
        subtitle=subtitle,
        glyphs=glyphs,
        version=CLI_VERSION,
    )


def render_session_header(
    console: Console,
    *,
    command: str,
    subtitle: str | None,
    glyphs: Glyphs,
    version: str | None = None,
) -> None:
    """Print the persistent branded band that identifies the running command."""
    width = _usable_width(console)
    console.print(gradient_rule(width, glyphs=glyphs))

    identity = Text(" ", style="agentflow.header")
    identity.append(f"{glyphs.diamond} ", style="agentflow.brand")
    identity.append_text(gradient_text("agentflow", bold=True))
    identity.append(f" {glyphs.caret} ", style="agentflow.muted")
    identity.append(command, style="agentflow.command")
    if version:
        identity.append(" " * max(width - identity.cell_len - len(version) - 1, 1))
        identity.append(version, style="agentflow.muted")
    _pad_to_width(identity, width)
    console.print(identity)

    if subtitle:
        caption = Text(" ", style="agentflow.header")
        caption.append(subtitle, style="agentflow.muted")
        _pad_to_width(caption, width)
        console.print(caption)

    console.print(gradient_rule(width, glyphs=glyphs, thin=True, offset=0.35))
    console.print()


def _can_play_cinematic(console: Console) -> bool:
    return (
        console.is_terminal
        and console.height >= _MIN_CINEMATIC_HEIGHT
        and console.width >= _MIN_CINEMATIC_WIDTH
    )


def _play_cinematic(
    console: Console,
    *,
    command: str,
    subtitle: str | None,
    glyphs: Glyphs,
    own_screen: bool = True,
) -> None:
    """Run the full-canvas reveal, optionally claiming a screen of its own."""
    frame_interval = 1.0 / INTRO_FPS
    frame_count = max(int(INTRO_DURATION_SECONDS * INTRO_FPS), 1)
    tagline = _TAGLINES.get(command.lower(), subtitle or _DEFAULT_TAGLINE)

    with (
        console.screen(style=f"on {BACKGROUND}", hide_cursor=True) if own_screen else nullcontext(),
        Live(
            console=console,
            auto_refresh=False,
            transient=True,
            redirect_stdout=False,
            redirect_stderr=False,
        ) as live,
    ):
        started = time.monotonic()
        for frame in range(frame_count + 1):
            progress = frame / frame_count
            live.update(
                _cinematic_frame(
                    console,
                    command=command,
                    tagline=tagline,
                    glyphs=glyphs,
                    progress=progress,
                ),
                refresh=True,
            )
            # Sleep against the wall clock so a slow terminal shortens the
            # sequence instead of stretching it past its motion budget.
            target = started + (frame + 1) * frame_interval
            remaining = target - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)


def _play_inline(console: Console, *, command: str, glyphs: Glyphs) -> None:
    """Short in-buffer reveal for short terminals and nested screens."""
    frame_count = 12
    with Live(
        console=console,
        auto_refresh=False,
        transient=True,
        redirect_stdout=False,
        redirect_stderr=False,
    ) as live:
        for frame in range(frame_count + 1):
            progress = frame / frame_count
            live.update(
                Group(
                    Align.center(_compact_wordmark(progress, glyphs)),
                    Align.center(_signature_nodes(command, progress, glyphs)),
                ),
                refresh=True,
            )
            time.sleep(0.045)


def _cinematic_frame(
    console: Console,
    *,
    command: str,
    tagline: str,
    glyphs: Glyphs,
    progress: float,
) -> RenderableType:
    """Compose one frame of the intro from its independently timed layers."""
    width = _usable_width(console)
    reveal = _ease_out(_phase(progress, 0.05, 0.55))
    shimmer = _phase(progress, 0.45, 0.9)
    chrome = _phase(progress, 0.55, 0.85)
    typing = _phase(progress, 0.6, 0.95)
    pipeline = _phase(progress, 0.25, 1.0)

    layers: list[RenderableType] = [
        Align.center(_aurora(width, progress, glyphs, rows=2)),
        Text(""),
    ]
    layers.extend(Align.center(line) for line in _block_wordmark(reveal, shimmer, glyphs))
    layers.append(Text(""))

    if chrome > 0:
        layers.append(Align.center(_command_chip(command, chrome, glyphs)))
        layers.append(Text(""))
    if typing > 0:
        layers.append(Align.center(_typed(tagline, typing, glyphs)))
        layers.append(Text(""))

    layers.append(Align.center(_signature_nodes(command, pipeline, glyphs)))
    layers.append(Align.center(_signature_labels(command, pipeline)))
    layers.append(Text(""))
    layers.append(Align.center(_load_bar(progress, glyphs, width=min(width - 8, 44))))

    return Align.center(
        Group(*layers),
        vertical="middle",
        height=max(console.height - 1, 12),
        style=f"on {BACKGROUND}",
    )


def _block_wordmark(reveal: float, shimmer: float, glyphs: Glyphs) -> list[Text]:
    """Render AGENTFLOW as block letters swept in by a moving light front."""
    if glyphs.block != "█":
        return [_compact_wordmark(reveal, glyphs)]

    columns = _wordmark_columns()
    total = len(columns[0])
    front = reveal * (total + 6) - 3
    shimmer_front = shimmer * (total + 10) - 5

    lines: list[Text] = []
    for row in range(_BLOCK_ROWS):
        line = Text()
        for index in range(total):
            character = columns[row][index]
            if character == " " or index > front:
                line.append(" ")
                continue
            distance = front - index
            shimmer_distance = abs(shimmer_front - index)
            if distance < _REVEAL_FRONT_WIDTH:
                line.append(character, style="bold #ffffff")
            elif shimmer > 0 and shimmer_distance < _SHIMMER_WIDTH:
                line.append(character, style="bold #f5f3ff")
            else:
                line.append(character, style=f"bold {sample_ramp(index / total)}")
        lines.append(line)
    return lines


def _wordmark_columns() -> tuple[str, ...]:
    """Lay the block font out once per row, letters separated by a column."""
    rows: list[str] = []
    for row in range(_BLOCK_ROWS):
        rows.append(" ".join(_BLOCK_FONT[letter][row] for letter in _WORDMARK))
    return tuple(rows)


def _compact_wordmark(reveal: float, glyphs: Glyphs) -> Text:
    """Spaced wordmark used when block letters do not fit or render."""
    visible = max(int(reveal * len(_WORDMARK)), 0)
    text = Text()
    text.append_text(gradient_text(" ".join(_WORDMARK[:visible]), bold=True))
    if visible < len(_WORDMARK):
        text.append(glyphs.cursor, style="bold #ffffff")
    return text


def _command_chip(command: str, intensity: float, glyphs: Glyphs) -> Text:
    """Pill showing which command the intro belongs to."""
    color = dim_hex("#4c1d95", 0.35 + 0.65 * intensity)
    chip = Text(style=f"on {color}")
    chip.append(f"  {glyphs.diamond} ", style="#a78bfa")
    chip.append(command.lower(), style="bold #f8fafc")
    chip.append("  ")
    return chip


def _typed(value: str, progress: float, glyphs: Glyphs) -> Text:
    """Type ``value`` out one character at a time with a blinking caret."""
    visible = int(_ease_out(progress) * len(value))
    text = Text(value[:visible], style="#cbd5f5")
    if visible < len(value) or int(progress * 12) % 2 == 0:
        text.append(glyphs.cursor, style="#22d3ee")
    return text


def _aurora(width: int, progress: float, glyphs: Glyphs, *, rows: int) -> Text:
    """Soft moving shade field that gives the canvas depth behind the logo."""
    span = min(width, 56)
    # Skip the blank shade: the band should read as one flowing ribbon rather
    # than a dotted line with holes punched through it.
    tiers = glyphs.shades[1:]
    text = Text()
    for row in range(rows):
        for column in range(span):
            wave = math.sin((column / 7.0) + progress * 6.0 + row * 1.3)
            level = int((wave + 1.0) / 2.0 * (len(tiers) - 1))
            tint = dim_hex(sample_ramp(column / span), 0.30 + 0.20 * row)
            text.append(tiers[level], style=tint)
        if row < rows - 1:
            text.append("\n")
    return text


def _signature_for(command: str) -> tuple[str, ...]:
    return _SIGNATURES.get(command.lower(), _DEFAULT_SIGNATURE)


def _signature_nodes(command: str, progress: float, glyphs: Glyphs) -> Text:
    """Node-and-link chain that fills in as the intro advances."""
    stages = _signature_for(command)
    segments = len(stages) * 2 - 1
    filled = progress * segments
    text = Text()
    for index in range(segments):
        active = index < filled
        position = index / max(segments - 1, 1)
        color = sample_ramp(position) if active else "#3f3f56"
        if index % 2 == 0:
            text.append(glyphs.node if active else glyphs.pending, style=f"bold {color}")
        else:
            text.append(glyphs.rule * 3 if active else glyphs.thin_rule * 3, style=color)
    return text


def _signature_labels(command: str, progress: float) -> Text:
    """Stage names under the chain, brightening in step with their node."""
    stages = _signature_for(command)
    reached = progress * len(stages)
    text = Text()
    for index, stage in enumerate(stages):
        if index:
            text.append("  ")
        if index < reached:
            text.append(stage, style=f"bold {sample_ramp(index / max(len(stages) - 1, 1))}")
        else:
            text.append(stage, style="#3f3f56")
    return text


def _load_bar(progress: float, glyphs: Glyphs, *, width: int) -> Text:
    """Hairline meter showing how much of the intro remains."""
    span = max(width, 10)
    filled = int(progress * span)
    text = Text()
    for index in range(span):
        if index < filled:
            text.append(glyphs.thin_rule, style=sample_ramp(index / span, BRAND_RAMP))
        else:
            text.append(glyphs.thin_rule, style="#242438")
    return text


def _phase(progress: float, start: float, end: float) -> float:
    """Map a global timeline position into one layer's local ``0..1`` window."""
    if progress <= start:
        return 0.0
    if progress >= end:
        return 1.0
    return (progress - start) / (end - start)


def _ease_out(value: float) -> float:
    """Cubic ease-out; motion decelerates instead of stopping abruptly."""
    clamped = min(max(value, 0.0), 1.0)
    return 1.0 - (1.0 - clamped) ** 3


def _usable_width(console: Console) -> int:
    return max(min(console.width, 100) - 1, 20)


def _pad_to_width(text: Text, width: int) -> None:
    padding = width - text.cell_len
    if padding > 0:
        text.append(" " * padding)

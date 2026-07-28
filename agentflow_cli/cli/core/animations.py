"""Terminal-native animation assets and renderers.

Frames stay independent from colors so terminal themes and accessibility
preferences can decide how semantic roles are rendered at runtime.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.text import Text


@dataclass(frozen=True)
class AnimationFrame:
    """One terminal animation frame with its display duration."""

    lines: tuple[str, ...]
    duration: float = 0.07


_UNICODE_FRAMES = (
    AnimationFrame(("                    ", "         ·          ", "                    ")),
    AnimationFrame(("                    ", "       ·─◆─·        ", "                    ")),
    AnimationFrame(("       ╭───╮        ", "       │ ◆ │        ", "       ╰───╯        ")),
    AnimationFrame(("   ◆───╭───╮───◆    ", "       │ A │        ", "   ◆───╰───╯───◆    ")),
    AnimationFrame(("   ◆───╭───╮───◆    ", "       │ AF│  AGENT ", "   ◆───╰───╯───◆    ")),
    AnimationFrame(
        ("   ◆───╭───╮───◆    ", "       │ AF│  AGENTFLOW", "   ◆───╰───╯───◆    "),
        0.12,
    ),
)

_ASCII_FRAMES = (
    AnimationFrame(("                    ", "         .          ", "                    ")),
    AnimationFrame(("                    ", "       .-O-.        ", "                    ")),
    AnimationFrame(("       +---+        ", "       | O |        ", "       +---+        ")),
    AnimationFrame(("   O---+---+---O    ", "       | A |        ", "   O---+---+---O    ")),
    AnimationFrame(("   O---+---+---O    ", "       | AF|  AGENT ", "   O---+---+---O    ")),
    AnimationFrame(
        ("   O---+---+---O    ", "       | AF|  AGENTFLOW", "   O---+---+---O    "),
        0.12,
    ),
)


def render_command_intro(
    console: Console,
    *,
    command: str,
    subtitle: str | None,
    unicode: bool,
) -> None:
    """Play a short best-effort intro and leave a useful static final frame."""
    frames = _UNICODE_FRAMES if unicode else _ASCII_FRAMES
    with Live(
        _frame_renderable(frames[0], command, subtitle),
        console=console,
        refresh_per_second=15,
        transient=True,
        redirect_stdout=False,
        redirect_stderr=False,
    ) as live:
        for frame in frames:
            live.update(_frame_renderable(frame, command, subtitle), refresh=True)
            time.sleep(frame.duration)

    console.print(_final_renderable(command, subtitle, unicode))


def _frame_renderable(
    frame: AnimationFrame,
    command: str,
    subtitle: str | None,
) -> RenderableType:
    art = Text("\n".join(frame.lines), style="agentflow.brand")
    label = Text.assemble(
        ("  agentflow ", "agentflow.title"),
        (command, "agentflow.command"),
    )
    parts: list[RenderableType] = [Align.center(art), Align.center(label)]
    if subtitle:
        parts.append(Align.center(Text(subtitle, style="agentflow.muted")))
    return Group(*parts)


def _final_renderable(command: str, subtitle: str | None, unicode: bool) -> RenderableType:
    connector = "◆" if unicode else "O"
    line = Text.assemble(
        (f"{connector} ", "agentflow.brand"),
        ("agentflow", "agentflow.title"),
        (" / ", "agentflow.muted"),
        (command, "agentflow.command"),
        (f" {connector}", "agentflow.brand"),
    )
    parts: list[RenderableType] = [Align.center(line)]
    if subtitle:
        parts.append(Align.center(Text(subtitle, style="agentflow.muted")))
    return Group(*parts)

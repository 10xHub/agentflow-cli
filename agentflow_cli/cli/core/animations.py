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


_BRAND_UNICODE_FRAMES = (
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

_BRAND_ASCII_FRAMES = (
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

_NETWORK_UNICODE_FRAMES = (
    AnimationFrame(("        ◌          ", "        │          ", "    ◌───◆───◌      ")),
    AnimationFrame(("        ◉          ", "        ┃          ", "    ◌───◆───◌      ")),
    AnimationFrame(("        ◌          ", "        │          ", "    ◉━━━◆━━━◉      ")),
    AnimationFrame(("    ◌───◆───◌      ", "        ┃          ", "    ◉━━━◆━━━◉      ")),
    AnimationFrame(("    ◉━━━◆━━━◉      ", "        ┃          ", "    ◉━━━◆━━━◉      "), 0.12),
)

_NETWORK_ASCII_FRAMES = (
    AnimationFrame(("        o          ", "        |          ", "    o---O---o      ")),
    AnimationFrame(("        O          ", "        |          ", "    o---O---o      ")),
    AnimationFrame(("        o          ", "        |          ", "    O===O===O      ")),
    AnimationFrame(("    o---O---o      ", "        |          ", "    O===O===O      ")),
    AnimationFrame(("    O===O===O      ", "        |          ", "    O===O===O      "), 0.12),
)

_SCAFFOLD_UNICODE_FRAMES = (
    AnimationFrame(("    ╭           ╮  ", "                   ", "    ╰           ╯  ")),
    AnimationFrame(("    ╭───────────╮  ", "    │  +        │  ", "    ╰───────────╯  ")),
    AnimationFrame(("    ╭───────────╮  ", "    │  + graph/ │  ", "    ╰───────────╯  ")),
    AnimationFrame(("    ╭───────────╮  ", "    │  ✓ config │  ", "    ╰───────────╯  ")),
    AnimationFrame(("    ╭───────────╮  ", "    │ ✓ PROJECT │  ", "    ╰───────────╯  "), 0.12),
)

_SCAFFOLD_ASCII_FRAMES = (
    AnimationFrame(("    +           +  ", "                   ", "    +           +  ")),
    AnimationFrame(("    +-----------+  ", "    |  +        |  ", "    +-----------+  ")),
    AnimationFrame(("    +-----------+  ", "    |  + graph/ |  ", "    +-----------+  ")),
    AnimationFrame(("    +-----------+  ", "    |  OK config|  ", "    +-----------+  ")),
    AnimationFrame(("    +-----------+  ", "    | OK PROJECT|  ", "    +-----------+  "), 0.12),
)

_PIPELINE_UNICODE_FRAMES = (
    AnimationFrame(("  source  ·  image  ·  ship ", "          ░░░░░░░░        ")),
    AnimationFrame(("  source  ◆  image  ·  ship ", "          ██░░░░░░        ")),
    AnimationFrame(("  source  ◆  image  ◆  ship ", "          █████░░░        ")),
    AnimationFrame(("  source  ◆  image  ◆  ship ", "          ████████        "), 0.12),
)

_PIPELINE_ASCII_FRAMES = (
    AnimationFrame(("  source  .  image  .  ship ", "          [        ]      ")),
    AnimationFrame(("  source  O  image  .  ship ", "          [==      ]      ")),
    AnimationFrame(("  source  O  image  O  ship ", "          [=====   ]      ")),
    AnimationFrame(("  source  O  image  O  ship ", "          [========]      "), 0.12),
)

_CHECK_UNICODE_FRAMES = (
    AnimationFrame(("    ◌  ◌  ◌  ◌       ", "    scanning…          ")),
    AnimationFrame(("    ●  ◌  ◌  ◌       ", "    evaluating…        ")),
    AnimationFrame(("    ✓  ●  ◌  ◌       ", "    evaluating…        ")),
    AnimationFrame(("    ✓  ✓  ●  ◌       ", "    scoring…           ")),
    AnimationFrame(("    ✓  ✓  ✓  ✓       ", "    all checks complete"), 0.12),
)

_CHECK_ASCII_FRAMES = (
    AnimationFrame(("    o  o  o  o       ", "    scanning...        ")),
    AnimationFrame(("    O  o  o  o       ", "    evaluating...      ")),
    AnimationFrame(("    OK O  o  o       ", "    evaluating...      ")),
    AnimationFrame(("    OK OK O  o       ", "    scoring...         ")),
    AnimationFrame(("    OK OK OK OK      ", "    checks complete    "), 0.12),
)


def render_command_intro(
    console: Console,
    *,
    command: str,
    subtitle: str | None,
    unicode: bool,
    persistent_screen: bool = False,
) -> None:
    """Play a short best-effort intro and leave a useful static final frame."""
    if command.lower() in {"play", "dev", "typing"}:
        render_typing_splash(
            console,
            command=command,
            subtitle=subtitle,
            unicode=unicode,
            persistent_screen=persistent_screen,
        )
        console.print(_final_renderable(command, subtitle, unicode))
        return

    frames = _frames_for(command, unicode)
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


def render_typing_splash(
    console: Console,
    *,
    command: str,
    subtitle: str | None,
    unicode: bool,
    persistent_screen: bool = False,
) -> None:
    """Use the terminal's alternate screen for a full-canvas typing reveal."""
    word = "AGENTFLOW"
    cursor = "▌" if unicode else "|"
    visible_states = [word[:index] for index in range(len(word) + 1)]
    visible_states.extend((word, word))

    with Live(
        _typing_renderable(
            console,
            visible="",
            cursor=cursor,
            show_cursor=True,
            command=command,
            subtitle=subtitle,
            unicode=unicode,
        ),
        console=console,
        screen=not persistent_screen,
        auto_refresh=False,
        transient=True,
        redirect_stdout=False,
        redirect_stderr=False,
    ) as live:
        for index, visible in enumerate(visible_states):
            show_cursor = index < len(word) or index % 2 == 0
            live.update(
                _typing_renderable(
                    console,
                    visible=visible,
                    cursor=cursor,
                    show_cursor=show_cursor,
                    command=command,
                    subtitle=subtitle,
                    unicode=unicode,
                ),
                refresh=True,
            )
            time.sleep(0.075 if index <= len(word) else 0.16)


def _typing_renderable(
    console: Console,
    *,
    visible: str,
    cursor: str,
    show_cursor: bool,
    command: str,
    subtitle: str | None,
    unicode: bool,
) -> RenderableType:
    node = "◆" if unicode else "O"
    rail = "━━━━" if unicode else "===="
    eyebrow = Text(f"{node}{rail} AGENT RUNTIME {rail}{node}", style="bold magenta")
    typed = Text(" ".join(visible), style="bold bright_cyan")
    if show_cursor:
        typed.append(cursor, style="bold white")
    description = Text(
        subtitle or "Build, run, and inspect intelligent agent systems.",
        style="white",
    )
    mode = Text(f"agentflow {command}", style="dim cyan")
    hint = Text("Preparing your interactive workspace…", style="dim white")
    content = Group(
        Align.center(eyebrow),
        Text(""),
        Align.center(typed),
        Text(""),
        Align.center(description),
        Text(""),
        Align.center(mode),
        Text(""),
        Align.center(hint),
    )
    return Align.center(
        content,
        vertical="middle",
        height=max(console.height, 12),
        style="on grey3",
    )


def _frames_for(command: str, unicode: bool) -> tuple[AnimationFrame, ...]:
    normalized = command.lower()
    if normalized in {"api", "dev", "play"}:
        return _NETWORK_UNICODE_FRAMES if unicode else _NETWORK_ASCII_FRAMES
    if normalized == "init":
        return _SCAFFOLD_UNICODE_FRAMES if unicode else _SCAFFOLD_ASCII_FRAMES
    if normalized == "build":
        return _PIPELINE_UNICODE_FRAMES if unicode else _PIPELINE_ASCII_FRAMES
    if normalized in {"eval", "test"}:
        return _CHECK_UNICODE_FRAMES if unicode else _CHECK_ASCII_FRAMES
    return _BRAND_UNICODE_FRAMES if unicode else _BRAND_ASCII_FRAMES


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

"""Persistent full-screen application frame for the Agentflow CLI.

The frame claims the terminal's alternate screen for the whole command and keeps
branded chrome pinned while the command's output scrolls between it:

    row 1..4      header — gradient rule, identity, subtitle, divider
    row 5..H-2    body   — everything the command prints, scrolling
    row H-1..H    footer — divider and status/hint bar

Pinning is done with a DEC scrolling region (``CSI top;bottom r``) rather than a
Rich ``Layout``. That matters: a layout would require every line of output to be
routed through one renderable, which breaks the moment a command shells out to
pytest, streams Uvicorn logs, or hands the terminal to a Questionary prompt. A
scrolling region is enforced by the terminal itself, so ordinary writes — from
this process or a child — simply scroll inside the body and leave the chrome
untouched.

Because an alternate screen is discarded when released, ``close()`` pauses on a
"press Enter" footer first, so a fast command cannot erase its own result.
"""

from __future__ import annotations

import io
import sys

from rich.console import Console
from rich.text import Text

from agentflow_cli.cli.core.theme import (
    AGENTFLOW_THEME,
    Glyphs,
    gradient_rule,
    gradient_text,
)


# Background painted across the alternate screen, so the frame reads as its own
# surface rather than a cleared prompt.
BACKGROUND = "#0b0b12"
_BACKGROUND_RGB = tuple(int(BACKGROUND[index : index + 2], 16) for index in (1, 3, 5))
_PAINT = "\x1b[48;2;{};{};{}m".format(*_BACKGROUND_RGB)

_SAVE_CURSOR = "\x1b7"
_RESTORE_CURSOR = "\x1b8"
_CLEAR_SCREEN = "\x1b[2J"
_RESET_REGION = "\x1b[r"
_RESET_SGR = "\x1b[0m"

_HEADER_ROWS = 4
_FOOTER_ROWS = 2
# Below this there is not enough room left for a usable body between the chrome.
_MIN_FRAME_HEIGHT = 14
_MIN_FRAME_WIDTH = 50


def _at(row: int, column: int = 1) -> str:
    return f"\x1b[{row};{column}H"


def _scroll_region(top: int, bottom: int) -> str:
    return f"\x1b[{top};{bottom}r"


class AppFrame:
    """Own the alternate screen and keep header/footer chrome pinned to it."""

    def __init__(self, console: Console, *, glyphs: Glyphs, color: bool) -> None:
        self._console = console
        self._glyphs = glyphs
        self._color = color
        self._open = False
        self._chrome = False
        self._command = ""
        self._hint = ""
        self._height = 0
        self._width = 0

    @property
    def active(self) -> bool:
        """Whether this frame currently owns the alternate screen."""
        return self._open

    @property
    def chrome_installed(self) -> bool:
        """Whether pinned header/footer chrome is currently drawn."""
        return self._chrome

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> bool:
        """Enter and paint the alternate screen. Returns False if unsupported."""
        if self._open or not self._console.is_terminal or not self._color:
            return False

        self._height = self._console.height
        self._width = self._console.width
        if self._height < _MIN_FRAME_HEIGHT or self._width < _MIN_FRAME_WIDTH:
            return False

        # A legacy console reports itself as a terminal but refuses the alternate
        # buffer. Bail before painting, or the scrolling region below would be
        # applied to the user's real scrollback and outlive the process.
        if not self._console.set_alt_screen(True):
            return False

        self._write(_PAINT + _CLEAR_SCREEN + _at(1))
        self._open = True
        return True

    def install_chrome(
        self,
        *,
        command: str,
        subtitle: str | None,
        version: str | None = None,
        hint: str | None = None,
    ) -> None:
        """Draw the pinned header and footer and confine output to the body."""
        if not self._open:
            return

        self._command = command
        self._hint = hint or "Ctrl+C to cancel"
        body_top = _HEADER_ROWS + 1
        body_bottom = self._height - _FOOTER_ROWS

        self._write(_CLEAR_SCREEN)
        self._draw_header(command=command, subtitle=subtitle, version=version)
        self._draw_footer(self._hint)
        # Confine scrolling to the body, then park the cursor at its top so the
        # first line of output lands directly under the header.
        self._write(_scroll_region(body_top, body_bottom) + _at(body_top))
        self._chrome = True

    def close(self, *, hold: bool = True) -> None:
        """Pause on a closing hint, then release the screen and restore the terminal."""
        if not self._open:
            return
        self._open = False

        if self._chrome:
            self._draw_footer(
                "Press Enter to close",
                anchored=True,
                style="agentflow.brand",
            )
            self._chrome = False

        if hold:
            self._wait_for_enter()

        self._write(_RESET_REGION + _RESET_SGR)
        self._console.set_alt_screen(False)
        self._console.show_cursor(True)

    # ------------------------------------------------------------------
    # Chrome rendering
    # ------------------------------------------------------------------

    def _draw_header(
        self,
        *,
        command: str,
        subtitle: str | None,
        version: str | None,
    ) -> None:
        glyphs = self._glyphs
        width = self._width

        identity = Text(" ", style="agentflow.header")
        identity.append(f"{glyphs.diamond} ", style="agentflow.brand")
        identity.append_text(gradient_text("agentflow", bold=True))
        identity.append(f" {glyphs.caret} ", style="agentflow.muted")
        identity.append(command, style="agentflow.command")
        if version:
            identity.append(" " * max(width - identity.cell_len - len(version) - 1, 1))
            identity.append(version, style="agentflow.muted")
        _pad(identity, width)

        caption = Text(" ", style="agentflow.header")
        caption.append(subtitle or "", style="agentflow.muted")
        _pad(caption, width)

        rows = (
            gradient_rule(width, glyphs=glyphs),
            identity,
            caption,
            gradient_rule(width, glyphs=glyphs, thin=True, offset=0.35),
        )
        buffer = _SAVE_CURSOR
        for offset, row in enumerate(rows, start=1):
            buffer += _at(offset) + self._to_ansi(row)
        self._write(buffer + _RESTORE_CURSOR)

    def _draw_footer(
        self,
        hint: str,
        *,
        anchored: bool = False,
        style: str = "agentflow.muted",
    ) -> None:
        glyphs = self._glyphs
        width = self._width

        status = Text(" ", style="agentflow.header")
        status.append(f"{glyphs.caret} ", style="agentflow.accent")
        status.append(hint, style=style)
        if self._command:
            label = f"agentflow {self._command}"
            status.append(" " * max(width - status.cell_len - len(label) - 1, 1))
            status.append(label, style="agentflow.muted")
        _pad(status, width)

        # An anchored footer keeps the cursor parked on it, so there is nothing
        # to save and restore around the write.
        buffer = "" if anchored else _SAVE_CURSOR
        buffer += _at(self._height - 1) + self._to_ansi(
            gradient_rule(width, glyphs=glyphs, thin=True, offset=0.6)
        )
        buffer += _at(self._height) + self._to_ansi(status)
        self._write(buffer + (_at(self._height, width) if anchored else _RESTORE_CURSOR))

    def _to_ansi(self, renderable: Text) -> str:
        """Render one chrome row to a positioned, self-contained escape string.

        Chrome is written directly rather than printed, because printing would
        scroll the body region; a standalone console keeps that rendering from
        disturbing the main console's cursor state.
        """
        target = Console(
            file=io.StringIO(),
            theme=AGENTFLOW_THEME,
            force_terminal=True,
            color_system="truecolor",
            width=self._width,
            highlight=False,
            soft_wrap=True,
        )
        with target.capture() as captured:
            target.print(renderable, end="")
        return captured.get()

    # ------------------------------------------------------------------
    # Terminal plumbing
    # ------------------------------------------------------------------

    def _write(self, payload: str) -> None:
        if not self._color:
            # Without color the terminal is not trusted with cursor control either.
            return
        self._console.file.write(payload)
        self._console.file.flush()

    @staticmethod
    def _wait_for_enter() -> None:
        if not sys.stdin.isatty():
            return
        try:
            sys.stdin.readline()
        except (OSError, ValueError, KeyboardInterrupt):
            return


def _pad(text: Text, width: int) -> None:
    padding = width - text.cell_len
    if padding > 0:
        text.append(" " * padding)

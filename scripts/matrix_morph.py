#!/usr/bin/env python3
"""
matrix_morph.py — a fast "decode" morph transition for tmux window switches.

Triggered by an after-select-window hook, it runs inside a full-screen
tmux popup that overlays the client. It:

  1. captures the *previous* window's visible characters (the source),
  2. captures the *new* (now current) window's characters (the target),
  3. animates source chars dissolving into green Matrix glyphs,
  4. then resolves those glyphs into the target chars,

and exits, letting tmux reveal the real new window underneath. The whole
thing is tuned to ~250-300ms so it reads as a quick flash, not a delay.
"""

import os
import sys
import time
import random
import subprocess

# --- tunables (override via env) -------------------------------------------
# The effect is a short color-only chromatic flash over the REAL new window
# content. Keep the characters fixed in place: no offsets, glyph swaps, or
# newline-driven full-screen redraws that can read as shake/judder.
ABERR_FRAMES = int(os.environ.get("MATRIX_FRAMES", "2"))     # distortion frames
ABERR_MS = int(os.environ.get("MATRIX_FRAME_MS", "20"))      # per-frame delay
# total ~ 2*20 = 40ms sleeps + ~60ms startup ≈ 110ms — basically instant

# Colors
TARGET = "\033[38;5;245m"  # soft grey for the real text
# Neon accents for the chromatic-aberration bands.
NEON_CYAN = "\033[38;5;51m"
NEON_MAG = "\033[38;5;201m"
RESET = "\033[0m"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
BG = "\033[48;2;15;17;26m"   # theme dark (#0f111a) popup background
CLR = BG + "\033[2J"


def term_size():
    try:
        cols = int(os.environ.get("COLUMNS") or 0)
        rows = int(os.environ.get("LINES") or 0)
        if cols and rows:
            return cols, rows
    except ValueError:
        pass
    sz = os.get_terminal_size()
    return sz.columns, sz.lines


def tmux(*args):
    return subprocess.run(
        ["tmux", *args], capture_output=True, text=True
    ).stdout


def capture_active(cols, rows):
    """Capture the active pane's visible content into a rows x cols grid,
    anchored at local (0,0). The popup is sized/positioned to sit exactly
    over this pane, so 0,0 lines up perfectly with the real content and no
    surrounding chrome (pane borders / status line) is disturbed."""
    grid = [[" "] * cols for _ in range(rows)]
    content = tmux("capture-pane", "-p")
    for r, line in enumerate(content.split("\n")[:rows]):
        for c, ch in enumerate(line[:cols]):
            if ch != "":
                grid[r][c] = ch
    return grid


def main():
    cols, rows = term_size()
    cols = max(1, cols)
    rows = max(1, rows)

    target = capture_active(cols, rows)              # active pane of new window

    out = sys.stdout.write

    # Compute the color bands ONCE so every frame is identical — nothing moves
    # between frames, so there is no judder, just a steady color flash.
    band = {}  # row -> tint
    for _ in range(random.randint(1, 2)):
        top = random.randint(0, rows - 1)
        height = random.randint(1, 2)
        tint = NEON_CYAN if random.random() < 0.5 else NEON_MAG
        for r in range(top, min(rows, top + height)):
            band[r] = tint

    def row_at(r):
        """Move directly to row r without emitting newlines.

        Full-width lines followed by CRLF can trigger terminal autowrap/scroll
        at the bottom edge of the popup, which looks like the pane shook. Direct
        cursor addressing keeps the overlay spatially stable.
        """
        return f"\033[{r + 1};1H"

    def render_aberration():
        """Chromatic color bands over the REAL window content.

        Fixed in place — purely a color glitch on the content, no movement and
        no character substitutions.
        """
        frame = []
        for r in range(rows):
            tint = band.get(r)
            toks = []
            for c in range(cols):
                ch = target[r][c]
                toks.append((tint or TARGET) + ch if ch != " " else " ")
            frame.append(row_at(r) + "".join(toks) + RESET)
        return "".join(frame)

    def render_clean():
        """The real window content, undistorted — the settle frame."""
        frame = []
        for r in range(rows):
            frame.append(row_at(r) + TARGET + "".join(target[r]) + RESET)
        return "".join(frame)

    out(HIDE + CLR)
    sys.stdout.flush()

    for _ in range(ABERR_FRAMES):
        out(render_aberration())
        sys.stdout.flush()
        time.sleep(ABERR_MS / 1000.0)

    out(render_clean())       # settle on the clean new window
    sys.stdout.flush()

    out(SHOW + RESET)
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write(SHOW + RESET)
    finally:
        sys.stdout.write(SHOW)
        sys.stdout.flush()

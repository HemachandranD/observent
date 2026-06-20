#!/usr/bin/env python3
"""Generate the observent banner logo (pixel-block wordmark, Claude Code palette).

Run from the repo root to (re)write ``assets/logo.svg``::

    python assets/logo.gen.py

The SVG is fully machine-generated from the 5x7 pixel font below — edit this
script (font, colours, spacing, tagline) and re-run rather than hand-editing
the rects in the SVG.
"""

import os

# 5x7 pixel font — only the letters the wordmark needs.
FONT = {
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "N": ["10001", "11001", "11001", "10101", "10011", "10011", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
}

CELL = 13          # grid cell size
BLOCK = 11         # drawn block size (leaves a gap -> "built from blocks" look)
RADIUS = 2.5
LSPACE = 13        # gap between letters

W, H = 1000, 340
CREAM = "#F5F4EE"
CORAL = "#CC785C"
CORAL_HI = "#E8956B"
WORD = "OBSERVENT"
TAGLINE = "Observability for Multi-Agent Apps"


def word_width(word):
    w = 0
    for i, ch in enumerate(word):
        w += len(FONT[ch][0]) * CELL
        if i < len(word) - 1:
            w += LSPACE
    return w


def draw_word(word, x0, y0, fill):
    rects = []
    x = x0
    for ch in word:
        glyph = FONT[ch]
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == "1":
                    bx = x + c * CELL + (CELL - BLOCK) / 2
                    by = y0 + r * CELL + (CELL - BLOCK) / 2
                    rects.append(
                        f'<rect x="{bx:.1f}" y="{by:.1f}" width="{BLOCK}" '
                        f'height="{BLOCK}" rx="{RADIUS}" fill="{fill}"/>'
                    )
        x += len(glyph[0]) * CELL + LSPACE
    return rects


def build_svg():
    y1 = 64
    rects = draw_word(WORD, (W - word_width(WORD)) / 2, y1, CREAM)

    ty = y1 + 7 * CELL + 56          # timeline baseline, below the wordmark
    tx0, tx1 = 250, 750
    n = 7
    dots = [
        f'<circle cx="{tx0 + (tx1 - tx0) * i / (n - 1):.1f}" cy="{ty}" '
        f'r="5" fill="{CORAL_HI}"/>'
        for i in range(n)
    ]

    word_svg = "".join("\n  " + r for r in rects)
    dots_svg = "\n  ".join(dots)

    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{WORD.lower()}">
  <defs>
    <radialGradient id="glow" cx="50%" cy="100%" r="75%">
      <stop offset="0" stop-color="{CORAL}" stop-opacity="0.45"/>
      <stop offset="0.55" stop-color="{CORAL}" stop-opacity="0.10"/>
      <stop offset="1" stop-color="{CORAL}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="0" y="0" width="{W}" height="{H}" rx="32" fill="#1A1917"/>
  <rect x="0" y="0" width="{W}" height="{H}" rx="32" fill="url(#glow)"/>
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="31" fill="none" stroke="{CORAL}" stroke-opacity="0.18" stroke-width="2"/>

  <!-- {WORD} -->{word_svg}

  <!-- timeline -->
  <line x1="{tx0}" y1="{ty}" x2="{tx1}" y2="{ty}" stroke="{CORAL}" stroke-opacity="0.35" stroke-width="2"/>
  {dots_svg}
  <text x="{W/2}" y="{ty + 38}" text-anchor="middle" font-family="ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, Consolas, monospace" font-size="22" letter-spacing="1" fill="#C89078">{TAGLINE}</text>
</svg>
'''


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.svg")
    with open(out, "w") as f:
        f.write(build_svg())
    print(f"wrote {out} ({W}x{H})")


if __name__ == "__main__":
    main()

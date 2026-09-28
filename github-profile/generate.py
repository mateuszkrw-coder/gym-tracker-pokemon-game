#!/usr/bin/env python3
"""Builds assets/hello.svg, the animated terminal shown on the GitHub profile.

Edit the settings below, then run:  python3 generate.py
No dependencies. The SVG loops forever using SMIL animation, which GitHub
plays when the file is embedded in a README with <img>.
"""

import random
from pathlib import Path

# --- Settings -------------------------------------------------------------

USER = "mateusz"
HOST = "github"
GREETING = "Hi, I'm Mateusz"
# (text, colour) pieces of the line under the greeting.
MESSAGE = [("Thanks for stopping by! Go check out my ", "text"),
           ("repositories", "accent"), (" ↓", "text")]
# Listed by `ls ~/repos`. Leave empty to skip that command.
REPOS = ["cosmic-clocks", "gym-tracker-pokemon-game",
         "odoo-process-xray", "shopify-odoo-connector"]
# How long the finished screen stays up before `clear` restarts the loop.
READ_TIME = 7.0

# "Hello!" in the figlet font ANSI Shadow. Drawn as shapes rather than text,
# so it looks the same whatever monospace font the viewer has.
BANNER = [
    "██╗  ██╗███████╗██╗     ██╗      ██████╗ ██╗",
    "██║  ██║██╔════╝██║     ██║     ██╔═══██╗██║",
    "███████║█████╗  ██║     ██║     ██║   ██║██║",
    "██╔══██║██╔══╝  ██║     ██║     ██║   ██║╚═╝",
    "██║  ██║███████╗███████╗███████╗╚██████╔╝██╗",
    "╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝",
]

COLORS = {
    "bg": "#0d1117", "bar": "#161b22", "border": "#30363d",
    "muted": "#7d8590", "text": "#e6edf3", "user": "#7ee787",
    "path": "#79c0ff", "dir": "#79c0ff", "accent": "#56d4dd",
}
GRADIENT = ["#56d4dd", "#a371f7", "#f778ba", "#56d4dd"]  # loops seamlessly

# --- Layout ---------------------------------------------------------------

FONT = ("SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',"
        "'Liberation Mono',monospace")
FS = 15          # font size
CW = 9           # width of one character cell
LH = 21          # line height
BH = 18          # banner row height
COLS = 64        # terminal width in characters
PAD = 24
BAR = 34         # title bar height
WIDTH = PAD * 2 + COLS * CW

rng = random.Random(7)


def keystroke():
    return rng.uniform(0.06, 0.13)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cx(col):
    return PAD + col * CW


def text(y, col, s, fill, bold=False):
    # One x per character keeps every glyph on the grid whatever font the
    # viewer ends up with.
    xs = " ".join(f"{cx(col + i):g}" for i in range(len(s)))
    weight = ' font-weight="700"' if bold else ""
    return (f'<text x="{xs}" y="{y:g}" fill="{fill}"{weight} '
            f'xml:space="preserve">{esc(s)}</text>')


class Scene:
    def __init__(self):
        self.items = []     # (appear_time, svg)
        self.cursors = []

    def add(self, t, svg):
        self.items.append((t, svg))

    def command(self, y, cmd, appear, idle):
        """A prompt that sits for `idle` seconds, then types `cmd`.
        Returns the moment Enter is pressed."""
        col = 0
        parts = []
        for s, color, bold in [(f"{USER}@{HOST}", "user", True),
                               (":", "muted", False), ("~", "path", False),
                               ("$ ", "muted", False)]:
            parts.append(text(y, col, s, COLORS[color], bold))
            col += len(s)
        self.add(appear, "".join(parts))
        t = start = appear + idle
        moves = []
        for i, ch in enumerate(cmd):
            self.add(t, text(y, col + i, ch, COLORS["text"]))
            moves.append((t, col + i + 1))
            t += keystroke()
        enter = t + 0.35
        self.cursors.append(dict(y=y, col=col, appear=appear, start=start,
                                 moves=moves, enter=enter))
        return enter


def discrete(attr, events, dur):
    """[(time, value)] -> an <animate> that steps through the values and
    repeats every `dur` seconds, so everything in the scene stays in sync."""
    points = {}
    for t, v in sorted(events, key=lambda e: e[0]):
        points[round(t / dur, 5)] = v
    keys = sorted(points)
    assert keys[0] == 0, "events must start at t=0"
    if keys[-1] != 1:
        points[1] = points[keys[-1]]
        keys.append(1)
    return (f'<animate attributeName="{attr}" dur="{dur:.3f}s" '
            f'repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{";".join(f"{k:g}" for k in keys)}" '
            f'values="{";".join(str(points[k]) for k in keys)}"/>')


def cursor(c, dur):
    """Blinks while the prompt is idle, then stays solid and follows the
    typing. Hidden once Enter is pressed."""
    shown = [(0, 0)]
    t, on = c["appear"], 1
    while t < c["start"] - 1e-6:
        shown.append((t, on))
        t, on = t + 0.5, 1 - on
    shown.append((c["start"], 1))
    if c["enter"] < dur - 1e-6:
        shown.append((c["enter"], 0))
    moves = [(0, c["col"])] + c["moves"]
    return (f'<rect x="{cx(c["col"])}" y="{c["y"] - 13:g}" width="{CW - 0.5:g}" '
            f'height="17" fill="{COLORS["text"]}" opacity="0">'
            f'{discrete("opacity", shown, dur)}'
            f'{discrete("x", [(t, cx(col)) for t, col in moves], dur)}</rect>')


def banner_row(top, line, last):
    """One row of the ANSI Shadow banner: full blocks become rectangles and
    the double box-drawing lines become strokes."""
    blocks, lines = [], []
    col = 0
    while col < len(line):
        if line[col] == "█":
            end = col
            while end < len(line) and line[end] == "█":
                end += 1
            h = BH if last else BH + 0.5   # overlap the next row: no seams
            blocks.append(f"M{cx(col):g} {top:g}h{(end - col) * CW:g}v{h:g}"
                          f"h{-(end - col) * CW:g}z")
            col = end
            continue
        L, R, T, B = cx(col), cx(col + 1), top, top + BH
        a, b = L + CW / 2 - 2, L + CW / 2 + 2      # vertical pair
        p, q = T + BH / 2 - 2, T + BH / 2 + 2      # horizontal pair
        lines.append({
            "═": f"M{L} {p}H{R}M{L} {q}H{R}",
            "║": f"M{a} {T}V{B}M{b} {T}V{B}",
            "╗": f"M{L} {p}H{b}V{B}M{L} {q}H{a}V{B}",
            "╔": f"M{R} {p}H{a}V{B}M{R} {q}H{b}V{B}",
            "╝": f"M{L} {q}H{b}V{T}M{L} {p}H{a}V{T}",
            "╚": f"M{R} {q}H{a}V{T}M{R} {p}H{b}V{T}",
        }.get(line[col], ""))
        col += 1
    return (f'<path d="{"".join(blocks)}" fill="url(#shine)"/>'
            f'<path d="{"".join(lines)}" fill="none" stroke="url(#shine)" '
            f'stroke-width="1.3" stroke-opacity=".8"/>')


def ls_rows(names):
    """Column-major layout like `ls`, using the fewest rows that fit."""
    for nrows in range(1, len(names) + 1):
        cols = [names[i:i + nrows] for i in range(0, len(names), nrows)]
        widths = [max(map(len, c)) + 2 for c in cols]
        if sum(widths) - 2 <= COLS:
            return [[(c[r], w) for c, w in zip(cols, widths) if r < len(c)]
                    for r in range(nrows)]


def build():
    s = Scene()
    y = BAR + 26

    # 1. ./hello.sh prints the banner and the greeting
    t = s.command(y, "./hello.sh", 0.0, 1.2)
    top = y + 12
    for i, line in enumerate(BANNER):
        s.add(t + 0.05 + i * 0.07,
              banner_row(top + i * BH, line, i == len(BANNER) - 1))
    t += 0.2 + len(BANNER) * 0.07
    y = top + len(BANNER) * BH + LH + 8

    s.add(t, text(y, 0, GREETING, COLORS["text"], bold=True))
    wx = cx(len(GREETING) + 1)
    turns = ";".join(f"{a} {wx + 12:g} {y - 2:g}"
                     for a in (0, 14, -8, 14, -4, 10, 0, 0))
    s.add(t, f'<text x="{wx:g}" y="{y:g}" font-family="\'Apple Color Emoji\','
             f'\'Segoe UI Emoji\',\'Noto Color Emoji\',sans-serif">👋'
             f'<animateTransform attributeName="transform" type="rotate" '
             f'dur="2.4s" repeatCount="indefinite" '
             f'keyTimes="0;.1;.2;.3;.4;.5;.6;1" values="{turns}"/></text>')
    y += LH
    t += 0.12
    col, parts = 0, []
    for piece, color in MESSAGE:
        parts.append(text(y, col, piece, COLORS[color]))
        col += len(piece)
    s.add(t, "".join(parts))
    y += LH * 1.5
    t += 0.3

    # 2. ls ~/repos
    if REPOS:
        t = s.command(y, "ls ~/repos", t, 0.9)
        for row in ls_rows(REPOS):
            y += LH
            col, parts = 0, []
            for name, width in row:
                parts.append(text(y, col, name, COLORS["dir"], bold=True))
                col += width
            s.add(t + 0.05, "".join(parts))
        y += LH
        t += 0.1

    # 3. an idle prompt, then `clear`: Enter restarts the loop
    dur = s.command(y, "clear", t, READ_TIME)

    body = []
    for appear, svg in s.items:
        if appear <= 0:
            body.append(svg)
        else:
            anim = discrete("opacity", [(0, 0), (appear, 1)], dur)
            body.append(f'<g opacity="0">{anim}{svg}</g>')
    body += [cursor(c, dur) for c in s.cursors]
    return render(body, y + 24)


def render(body, h):
    w = WIDTH
    bw = len(BANNER[0]) * CW
    stops = "".join(f'<stop offset="{i / (len(GRADIENT) - 1):g}" '
                    f'stop-color="{c}"/>' for i, c in enumerate(GRADIENT))
    dots = "".join(f'<circle cx="{20 + i * 20}" cy="{BAR / 2:g}" r="6" '
                   f'fill="{c}"/>'
                   for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h:g}" width="{w}" height="{h:g}" font-family="{FONT}" font-size="{FS}">
<title>{esc(GREETING)}! Thanks for stopping by, go check out my repositories.</title>
<defs>
<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="{PAD}" y1="0" x2="{PAD + bw}" y2="0" spreadMethod="repeat">{stops}<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{bw} 0" dur="6s" repeatCount="indefinite"/></linearGradient>
<clipPath id="window"><rect width="{w}" height="{h:g}" rx="10"/></clipPath>
</defs>
<g clip-path="url(#window)">
<rect width="{w}" height="{h:g}" fill="{COLORS["bg"]}"/>
<rect width="{w}" height="{BAR}" fill="{COLORS["bar"]}"/>
<path d="M0 {BAR - 0.5}H{w}" stroke="{COLORS["border"]}"/>
</g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1:g}" rx="10" fill="none" stroke="{COLORS["border"]}"/>
{dots}
<text x="{w / 2:g}" y="{BAR / 2 + 4.5:g}" text-anchor="middle" font-size="13" fill="{COLORS["muted"]}">{esc(f"{USER}@{HOST}: ~")}</text>
{chr(10).join(body)}
</svg>
"""


if __name__ == "__main__":
    out = Path(__file__).with_name("assets") / "hello.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out}")

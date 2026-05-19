#!/usr/bin/env python3
"""Render a .txt terminal capture as a dark-theme PNG for README assets."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (28, 28, 30)
FG = (230, 230, 235)
PROMPT = (120, 200, 140)
MUTED = (140, 140, 150)
PAD = 24
LINE_H = 20
MAX_WIDTH = 920


def _font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        p = Path(name)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def render(text: str, out: Path) -> None:
    lines = text.rstrip("\n").split("\n")
    font = _font(13)
    # Wrap long lines
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= 110:
            wrapped.append(line)
            continue
        while len(line) > 110:
            wrapped.append(line[:110])
            line = line[110:]
        if line:
            wrapped.append(line)

    w = min(MAX_WIDTH, max((len(ln) for ln in wrapped), default=40) * 8 + PAD * 2)
    h = PAD * 2 + len(wrapped) * LINE_H
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    y = PAD
    for line in wrapped:
        color = FG
        if line.startswith("$"):
            color = PROMPT
        elif line.startswith("(") or "mock" in line.lower():
            color = MUTED
        draw.text((PAD, y), line, fill=color, font=font)
        y += LINE_H
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    print(f"wrote {out} ({w}x{h})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_txt")
    ap.add_argument("output_png")
    args = ap.parse_args()
    render(Path(args.input_txt).read_text(), Path(args.output_png))


if __name__ == "__main__":
    main()

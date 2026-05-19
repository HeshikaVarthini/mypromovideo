"""Lightweight chart rendering using Pillow (no matplotlib required)."""

from __future__ import annotations

import tempfile
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


COLORS = ["#1A365D", "#0096D6", "#38B2AC", "#ED8936", "#9F7AEA"]
BG = "#FFFFFF"
TEXT = "#334155"
TITLE = "#1A365D"


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str = "",
    horizontal: bool = False,
    width: int = 900,
    height: int = 500,
) -> str:
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    title_font = _font(18)
    label_font = _font(11)
    value_font = _font(10)

    draw.text((width // 2, 18), title, fill=TITLE, font=title_font, anchor="mt")

    margin_left = 120 if horizontal else 60
    margin_right = 40
    margin_top = 55
    margin_bottom = 80 if not horizontal else 50

    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom

    max_val = max(values) if values else 1
    max_val = max_val * 1.15 or 1

    n = len(values)
    if n == 0:
        path = tempfile.mktemp(suffix=".png")
        img.save(path)
        return path

    if horizontal:
        bar_h = chart_h / n * 0.65
        gap = chart_h / n * 0.35
        for i, (label, val) in enumerate(zip(labels, values)):
            y = margin_top + i * (bar_h + gap)
            bar_len = (val / max_val) * chart_w
            color = COLORS[i % len(COLORS)]
            draw.rectangle(
                [margin_left, y, margin_left + bar_len, y + bar_h],
                fill=color,
            )
            short = label[:18] + ("…" if len(label) > 18 else "")
            draw.text((margin_left - 8, y + bar_h / 2), short, fill=TEXT, font=label_font, anchor="rm")
            draw.text(
                (margin_left + bar_len + 5, y + bar_h / 2),
                _fmt(val),
                fill=TEXT,
                font=value_font,
                anchor="lm",
            )
    else:
        bar_w = chart_w / n * 0.55
        gap = chart_w / n * 0.45
        for i, (label, val) in enumerate(zip(labels, values)):
            x = margin_left + i * (bar_w + gap)
            bar_height = (val / max_val) * chart_h
            y_top = margin_top + chart_h - bar_height
            color = COLORS[i % len(COLORS)]
            draw.rectangle(
                [x, y_top, x + bar_w, margin_top + chart_h],
                fill=color,
            )
            short = label[:12] + ("…" if len(label) > 12 else "")
            draw.text(
                (x + bar_w / 2, margin_top + chart_h + 8),
                short,
                fill=TEXT,
                font=label_font,
                anchor="mt",
            )
            draw.text(
                (x + bar_w / 2, y_top - 6),
                _fmt(val),
                fill=TEXT,
                font=value_font,
                anchor="mb",
            )

    if ylabel:
        draw.text((12, height // 2), ylabel, fill=TEXT, font=label_font)

    path = tempfile.mktemp(suffix=".png")
    img.save(path, "PNG")
    return path


def _fmt(val: float) -> str:
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val/1_000:.1f}K"
    if val == int(val):
        return str(int(val))
    return f"{val:.1f}"

"""Professional chart rendering with Pillow."""

from __future__ import annotations

import tempfile
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

COLORS = ["#E11D48", "#0F2744", "#3B82F6", "#06B6D4", "#8B5CF6"]
BG = "#FAFBFC"
CHART_BG = "#FFFFFF"
TEXT = "#334155"
TITLE = "#0F2744"
GRID = "#E2E8F0"
ACCENT_LINE = "#E11D48"


def _font(size: int, bold: bool = False):
    names = ["segoeuib.ttf", "Segoe UI Bold.ttf", "arialbd.ttf", "arial.ttf"] if bold else [
        "segoeui.ttf", "Segoe UI.ttf", "arial.ttf"
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str = "",
    horizontal: bool = False,
    width: int = 1000,
    height: int = 560,
) -> str:
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Chart panel
    pad = 24
    panel = [pad, pad, width - pad, height - pad]
    _rounded_rect(draw, panel, 16, CHART_BG)
    draw.rectangle([panel[0], panel[1], panel[0] + 6, panel[3]], fill=ACCENT_LINE)

    title_font = _font(20, bold=True)
    label_font = _font(12)
    value_font = _font(11, bold=True)

    draw.text((panel[0] + 24, panel[1] + 18), title, fill=TITLE, font=title_font)

    margin_left = panel[0] + 130 if horizontal else panel[0] + 50
    margin_right = panel[2] - 30
    margin_top = panel[1] + 58
    margin_bottom = panel[3] - 50 if not horizontal else panel[3] - 30

    chart_w = margin_right - margin_left
    chart_h = margin_bottom - margin_top

    max_val = max(values) * 1.12 if values else 1

    # Grid lines
    for g in range(5):
        if horizontal:
            gy = margin_top + chart_h * g / 4
            draw.line([(margin_left, gy), (margin_right, gy)], fill=GRID, width=1)
        else:
            gx = margin_left + chart_w * g / 4
            draw.line([(gx, margin_top), (gx, margin_bottom)], fill=GRID, width=1)

    n = len(values)
    if n == 0:
        path = tempfile.mktemp(suffix=".png")
        img.save(path, "PNG")
        return path

    if horizontal:
        bar_h = chart_h / n * 0.58
        gap = chart_h / n * 0.42
        for i, (label, val) in enumerate(zip(labels, values)):
            y = margin_top + i * (bar_h + gap) + gap * 0.2
            bar_len = max((val / max_val) * chart_w, 6)
            color = COLORS[i % len(COLORS)]
            _rounded_rect(draw, [margin_left, y, margin_left + bar_len, y + bar_h], 6, color)
            short = label[:20] + ("…" if len(label) > 20 else "")
            draw.text((margin_left - 10, y + bar_h / 2), short, fill=TEXT, font=label_font, anchor="rm")
            draw.text((margin_left + bar_len + 8, y + bar_h / 2), _fmt(val), fill=TITLE, font=value_font, anchor="lm")
    else:
        bar_w = chart_w / n * 0.52
        gap = chart_w / n * 0.48
        for i, (label, val) in enumerate(zip(labels, values)):
            x = margin_left + i * (bar_w + gap) + gap * 0.25
            bar_height = max((val / max_val) * chart_h, 6)
            y_top = margin_bottom - bar_height
            color = COLORS[i % len(COLORS)]
            _rounded_rect(draw, [x, y_top, x + bar_w, margin_bottom], 6, color)
            short = label[:14] + ("…" if len(label) > 14 else "")
            draw.text((x + bar_w / 2, margin_bottom + 10), short, fill=TEXT, font=label_font, anchor="mt")
            draw.text((x + bar_w / 2, y_top - 8), _fmt(val), fill=TITLE, font=value_font, anchor="mb")

    path = tempfile.mktemp(suffix=".png")
    img.save(path, "PNG", quality=95)
    return path


def _fmt(val: float) -> str:
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val/1_000:.1f}K"
    if val == int(val):
        return str(int(val))
    return f"{val:.1f}"

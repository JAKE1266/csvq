"""终端渲染:CJK 对齐表格与横向条形图。"""

from __future__ import annotations

from csvq.core.util import display_width, pad, truncate

BAR_WIDTH = 32


def render_table(headers: list, rows: list, max_width: int = 32) -> str:
    """渲染对齐表格(自动适应中文双宽字符,单元格超宽截断)。"""
    headers = [str(h) for h in headers]
    rows = [[str(cell) for cell in row] for row in rows]
    widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], display_width(truncate(cell, max_width)))
    shown = [[truncate(cell, max_width) for cell in row] for row in rows]
    lines = ["  ".join(pad(h, widths[i]) for i, h in enumerate(headers)),
             "  ".join("-" * widths[i] for i in range(len(headers)))]
    for row in shown:
        lines.append("  ".join(pad(cell, widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def render_bars(items, width: int = BAR_WIDTH) -> str:
    """横向条形图:``items`` 为 ``(标签, 数值)`` 列表,长度按最大值归一化。"""
    if not items:
        return "  (无数据)"
    largest = max(value for _, value in items) or 1
    lines = []
    for label, value in items:
        blocks = max(1, round(value / largest * width)) if value else 0
        note = f"{value:g}"
        lines.append(f"  {pad(truncate(str(label), 14), 16)} {'█' * blocks} {note}")
    return "\n".join(lines)

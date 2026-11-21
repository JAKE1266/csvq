"""终端排版辅助:CJK 双宽字符对齐(与项目集其他工具同款实现)。"""

from __future__ import annotations

import unicodedata


def display_width(text: str) -> int:
    """按终端显示宽度计算(全角/宽字符占 2 列)。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, width: int, align: str = "left") -> str:
    """按显示宽度补空格,使含中文的列也能对齐。"""
    gap = max(0, width - display_width(text))
    return text + " " * gap if align == "left" else " " * gap + text


def truncate(text: str, width: int) -> str:
    """按显示宽度截断,超出部分以「…」结尾。"""
    if display_width(text) <= width:
        return text
    out, used = [], 0
    for ch in text:
        ch_width = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if used + ch_width > width - 1:
            break
        out.append(ch)
        used += ch_width
    return "".join(out) + "…"


def format_value(value) -> str:
    """查询结果单元格的终端显示格式。"""
    if value is None:
        return "∅"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)

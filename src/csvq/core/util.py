"""查询结果格式化 + 终端排版辅助。

排版原语(CJK 对齐/截断)来自随 csvq 私有分发的 cjktable,
本模块只保留 csvq 特有的单元格格式化。
"""

from __future__ import annotations

from csvq._vendor.cjktable import pad, truncate
from csvq._vendor.cjktable import width as display_width

__all__ = ["display_width", "format_value", "pad", "truncate"]


def format_value(value) -> str:
    """查询结果单元格的终端显示格式。"""
    if value is None:
        return "∅"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)

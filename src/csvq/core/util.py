"""查询结果格式化 + 终端排版辅助。

排版原语(CJK 对齐/截断)自 v1.0 起统一来自自研微库 cjktable:
https://github.com/JAKE1266/cjktable —— 本模块只保留 csvq 特有的单元格格式化。
"""

from __future__ import annotations

# 终端排版原语统一来自 cjktable(签名与原内嵌实现完全兼容)
from cjktable import pad, truncate
from cjktable import width as display_width

__all__ = ["display_width", "format_value", "pad", "truncate"]


def format_value(value) -> str:
    """查询结果单元格的终端显示格式。"""
    if value is None:
        return "∅"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)

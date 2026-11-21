"""csvq —— 用 SQL 查询 CSV 的零依赖命令行工具。

CSV 导入内存 SQLite(列类型自动推断),随后即可用任意 SQL 分析::

    from csvq import load_tables, run_query

    conn = load_tables(["sales.csv"])
    headers, rows = run_query(conn, "SELECT region, SUM(amount) FROM sales GROUP BY 1")
"""

from csvq.core.importer import load_tables, run_query, table_info
from csvq.core.render import render_bars, render_table

__version__ = "1.0.0"

__all__ = ["load_tables", "render_bars", "render_table", "run_query", "table_info", "__version__"]

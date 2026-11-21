"""csvq 命令行入口。

::

    csvq sales.csv "SELECT region, SUM(amount) AS total FROM sales GROUP BY 1 ORDER BY 2 DESC"
    csvq users=users.csv orders.csv --tables
    csvq users.csv --schema
    csvq sales.csv "SELECT region, COUNT(*) FROM sales GROUP BY 1" --chart
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from . import __version__
from .core.importer import SQL_PREFIX_RE, list_tables, load_tables, run_query, table_info
from .core.render import render_bars, render_table
from .core.util import format_value, pad


def cmd_query(args) -> int:
    started = time.perf_counter()
    conn = load_tables(args.files, delimiter=args.delimiter)
    headers, rows = run_query(conn, args.sql)
    elapsed_ms = (time.perf_counter() - started) * 1000

    if args.json:
        print(json.dumps({
            "columns": headers,
            "rows": rows,
            "count": len(rows),
        }, ensure_ascii=False, indent=2))
        return 0

    if args.chart:
        if len(headers) < 2:
            print("错误:--chart 要求结果至少两列(第 1 列为标签,第 2 列为数值)", file=sys.stderr)
            return 1
        try:
            items = [(format_value(row[0]), float(row[1])) for row in rows[:args.limit]]
        except (TypeError, ValueError):
            print("错误:--chart 要求第 2 列为数值(建议先聚合再画图)", file=sys.stderr)
            return 1
        print(render_bars(items))
        if len(rows) > args.limit:
            print(f"  …其余 {len(rows) - args.limit} 行未显示(可用 --limit 调整)", file=sys.stderr)
        print(f"\n共 {len(rows)} 行 · {elapsed_ms:.0f} ms")
        return 0

    if not headers:  # 无结果集(理论上 query_only 下不会发生)
        print("执行完成。")
        return 0
    display = [[format_value(cell) for cell in row] for row in rows]
    print(render_table(headers, display))
    print(f"\n共 {len(rows)} 行 · {elapsed_ms:.0f} ms")
    return 0


def cmd_schema(args) -> int:
    conn = load_tables(args.files, delimiter=args.delimiter)
    for table in list_tables(conn):
        info = table_info(conn, table)
        print(f"表 {info['table']}(共 {info['rows']} 行)")
        for col in info["columns"]:
            print(f"  {pad(col['name'], 22)} {col['type']}")
        print(f"  → 示例:SELECT * FROM {table} LIMIT 5")
        print()
    return 0


def cmd_tables(args) -> int:
    conn = load_tables(args.files, delimiter=args.delimiter)
    for name in list_tables(conn):
        info = table_info(conn, name)
        cols = ", ".join(f"{c['name']}:{c['type']}" for c in info["columns"])
        print(f"  {name}  ({info['rows']} 行)  {cols}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csvq",
        description="csvq —— 用 SQL 查询 CSV:零依赖,基于标准库 sqlite3,列类型自动推断",
    )
    parser.add_argument("--version", action="version", version=f"csvq {__version__}")
    parser.add_argument("args", nargs="+", metavar="参数",
                        help="CSV 文件(可用 别名=路径 重命名表)+ SQL;SQL 必须是最后一个参数")
    parser.add_argument("-d", "--delimiter", default=None,
                        help="CSV 分隔符(默认自动嗅探,回退逗号)")
    parser.add_argument("--schema", action="store_true", help="显示表结构而不是执行查询")
    parser.add_argument("--tables", action="store_true", help="列出全部表")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出查询结果")
    parser.add_argument("--chart", action="store_true",
                        help="条形图展示(第 1 列标签,第 2 列数值)")
    parser.add_argument("--limit", type=int, default=15, help="条形图最多展示行数(默认 15)")
    parser.set_defaults(func=cmd_query)

    return parser


def _split_args(raw_args: list) -> tuple:
    """拆分文件参数与 SQL:最后一个长得像 SQL 的位置参数即 SQL。"""
    if not raw_args:
        return [], None
    *files, maybe_sql = raw_args
    if maybe_sql and SQL_PREFIX_RE.match(maybe_sql):
        return files, maybe_sql
    return raw_args, None


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.schema:
        args.files = args.args
        args.func = cmd_schema
        return _dispatch(args)
    if args.tables:
        args.files = args.args
        args.func = cmd_tables
        return _dispatch(args)

    files, sql = _split_args(args.args)
    if sql is None:
        print("错误:缺少有效的 SQL 查询——最后一个参数应以 SELECT / WITH / VALUES 开头,"
              "写语句不受支持(数据只读)", file=sys.stderr)
        print('示例:csvq data.csv "SELECT * FROM data LIMIT 5"', file=sys.stderr)
        return 1
    if not files:
        print("错误:至少提供一个 CSV 文件", file=sys.stderr)
        return 1
    args.files, args.sql = files, sql
    return _dispatch(args)


def _dispatch(args) -> int:
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except BrokenPipeError:
        return 0
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"错误:{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # SQLite 等库异常统一兜底,给出可读信息
        print(f"错误:{type(exc).__name__}: {exc}", file=sys.stderr)
        print("提示:表名/列名含中文或特殊字符时,请用双引号括起,如 \"销售额\"。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

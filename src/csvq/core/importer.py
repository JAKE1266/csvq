"""CSV → 内存 SQLite 导入、类型推断与查询执行。

设计要点:

- 每个文件成为一张表,表名默认取文件名主干,可用 ``别名=路径`` 显式指定;
- 列类型按全部数据推断:全整数 → INTEGER,含小数/科学计数 → REAL,否则 TEXT;
- 空单元格导入为 NULL;行长度与表头不一致时补 NULL / 截断;
- 列名保留原样(含中文),建表与 schema 输出一律用双引号引用标识符;
- 连接开启 ``query_only``,杜绝意外写操作。
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+[eE][+-]?\d+|\d+\.\d*[eE][+-]?\d+)$")

SQL_PREFIX_RE = re.compile(r"^\s*(select|with|values)\b", re.IGNORECASE)


def _sniff_delimiter(path: Path) -> str:
    """尝试嗅探分隔符,失败则回退逗号。"""
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _sanitize_table_name(stem: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z_]", "_", stem).strip("_").lower()
    if not name:
        name = "t"
    if name[0].isdigit():
        name = f"t_{name}"
    return name


def _infer_type(values: list) -> str:
    """按非空值推断列类型(None 与空串不参与)。"""
    non_empty = [v for v in values if v not in ("", None)]
    if not non_empty:
        return "TEXT"
    if all(_INT_RE.match(v) for v in non_empty):
        return "INTEGER"
    if all(_INT_RE.match(v) or _FLOAT_RE.match(v) for v in non_empty):
        return "REAL"
    return "TEXT"


def _convert(value, column_type: str):
    """单元格按列类型转换;None 与空串一律为 NULL。"""
    if value is None or value == "":
        return None
    if column_type == "INTEGER" and _INT_RE.match(value):
        return int(value)
    if column_type == "REAL" and (_INT_RE.match(value) or _FLOAT_RE.match(value)):
        return float(value)
    return value


def _normalize_row(row: list, width: int) -> list:
    """行长度对齐表头:缺的补 None,多的截断。"""
    if len(row) < width:
        return row + [None] * (width - len(row))
    return row[:width]


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def load_tables(specs, delimiter: str | None = None) -> sqlite3.Connection:
    """把多个 CSV 装入一个内存 SQLite 连接。

    :param specs: 路径或 ``别名=路径`` 字符串列表
    :param delimiter: 显式分隔符;None 时逐文件自动嗅探
    """
    if not specs:
        raise ValueError("至少需要一个 CSV 文件")
    conn = sqlite3.connect(":memory:")
    used_names: set = set()

    for spec in specs:
        alias, _, raw_path = str(spec).partition("=")
        if not raw_path:  # 没有 "=" → 整段都是路径
            raw_path = alias
        path = Path(raw_path)
        if not path.is_file():
            conn.close()
            raise FileNotFoundError(f"文件不存在:{path}")

        stem = alias if raw_path != alias else path.stem
        base = _sanitize_table_name(stem)
        table, counter = base, 2
        while table in used_names:
            table = f"{base}_{counter}"
            counter += 1
        used_names.add(table)

        delim = delimiter or _sniff_delimiter(path)
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fp:
            rows = list(csv.reader(fp, delimiter=delim))
        if not rows:
            conn.close()
            raise ValueError(f"CSV 文件为空:{path}")

        headers = [h.strip() for h in rows[0]]
        width = len(headers)
        data = [_normalize_row(row, width) for row in rows[1:]]

        # 逐列推断类型(转置列)
        columns = [_infer_type([row[i] for row in data]) for i in range(width)]
        quoted_headers = [_quote(h) for h in headers]
        ddl = ", ".join(f"{q} {t}" for q, t in zip(quoted_headers, columns))
        conn.execute(f"CREATE TABLE {_quote(table)} ({ddl})")
        placeholders = ", ".join("?" for _ in headers)
        conn.executemany(
            f"INSERT INTO {_quote(table)} VALUES ({placeholders})",
            [[_convert(v, t) for v, t in zip(row, columns)] for row in data],
        )
    # 导入完成后锁为只读:用户的任何写语句都会被 SQLite 直接拒绝
    conn.execute("PRAGMA query_only = ON")
    return conn


def run_query(conn: sqlite3.Connection, sql: str) -> tuple:
    """执行只读 SQL,返回 ``(表头列表, 行列表)``。

    仅允许 SELECT / WITH / VALUES 开头的语句。
    """
    if not SQL_PREFIX_RE.match(sql or ""):
        raise ValueError("只支持 SELECT / WITH / VALUES 查询(数据文件是只读的)")
    cursor = conn.execute(sql)
    headers = [desc[0] for desc in cursor.description or []]
    return headers, cursor.fetchall()


def table_info(conn: sqlite3.Connection, table: str) -> dict:
    """表结构信息:列名/类型/行数。表不存在时抛 ValueError。"""
    quoted = _quote(table)
    try:
        columns = conn.execute(f"PRAGMA table_info({quoted})").fetchall()
        count = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
    except sqlite3.Error as exc:
        raise ValueError(f"表 {table!r} 不存在或不可查询:{exc}") from exc
    if not columns:
        raise ValueError(f"表 {table!r} 不存在。可用表请看 --tables")
    return {
        "table": table,
        "columns": [{"name": col[1], "type": col[2]} for col in columns],
        "rows": count,
    }


def list_tables(conn: sqlite3.Connection) -> list:
    return [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

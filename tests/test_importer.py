"""导入与查询核心层单元测试。"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from csvq.core.importer import (_convert, _infer_type, _normalize_row,
                                _sanitize_table_name, list_tables, load_tables,
                                run_query, table_info)


class TypeInferenceTest(unittest.TestCase):
    def test_infer(self):
        self.assertEqual(_infer_type(["1", "2", "-3"]), "INTEGER")
        self.assertEqual(_infer_type(["1.5", "2", "1e3"]), "REAL")
        self.assertEqual(_infer_type(["007", "42"]), "INTEGER")
        self.assertEqual(_infer_type(["abc", "1"]), "TEXT")
        self.assertEqual(_infer_type(["", "", ""]), "TEXT")
        self.assertEqual(_infer_type([]), "TEXT")
        self.assertEqual(_infer_type([None, "3", None]), "INTEGER")  # 短行补 None 不参与推断

    def test_convert(self):
        self.assertEqual(_convert("12", "INTEGER"), 12)
        self.assertIsNone(_convert("", "INTEGER"))
        self.assertIsNone(_convert(None, "REAL"))
        self.assertEqual(_convert("1.5", "REAL"), 1.5)
        self.assertEqual(_convert("1e2", "REAL"), 100.0)
        self.assertEqual(_convert("中文", "TEXT"), "中文")
        self.assertEqual(_convert("007", "TEXT"), "007")

    def test_normalize_row(self):
        self.assertEqual(_normalize_row(["a", "b"], 3), ["a", "b", None])
        self.assertEqual(_normalize_row(["a", "b", "c", "d"], 2), ["a", "b"])
        self.assertEqual(_normalize_row(["a"], 1), ["a"])

    def test_table_name(self):
        self.assertEqual(_sanitize_table_name("My Data-2024"), "my_data_2024")
        self.assertEqual(_sanitize_table_name("2024"), "t_2024")
        self.assertEqual(_sanitize_table_name("销售数据"), "t")  # 全中文 → 兜底 t
        self.assertEqual(_sanitize_table_name("sales"), "sales")


class LoadTablesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_basic_load_and_types(self):
        self.write("sales.csv",
                   "region,amount,note\n"
                   "华东,120.5,销售A\n"
                   "华北,80,销售B\n"
                   "华南,,销售C\n")
        conn = load_tables([str(self.dir / "sales.csv")])
        headers, rows = run_query(conn, "SELECT region, amount, note FROM sales ORDER BY region")
        self.assertEqual(headers, ["region", "amount", "note"])
        # SQLite 按 UTF-8 字节序排序文本:东 < 北 < 南
        self.assertEqual(rows, [("华东", 120.5, "销售A"), ("华北", 80.0, "销售B"), ("华南", None, "销售C")])

    def test_integer_column(self):
        self.write("ints.csv", "n,label\n1,a\n20,b\n300,c\n")
        conn = load_tables([str(self.dir / "ints.csv")])
        _, rows = run_query(conn, "SELECT SUM(n) FROM ints")
        self.assertEqual(rows[0][0], 321)

    def test_alias(self):
        self.write("raw_users.csv", "id,name\n1,张三\n")
        conn = load_tables([f"users={self.dir / 'raw_users.csv'}"])
        self.assertEqual(list_tables(conn), ["users"])
        _, rows = run_query(conn, "SELECT name FROM users")
        self.assertEqual(rows, [("张三",)])

    def test_multiple_files(self):
        self.write("a.csv", "x\n1\n")
        self.write("b.csv", "y\n2\n")
        conn = load_tables([str(self.dir / "a.csv"), str(self.dir / "b.csv")])
        self.assertEqual(list_tables(conn), ["a", "b"])

    def test_duplicate_stem_deduped(self):
        (self.dir / "x").mkdir()
        p1 = self.write("x.csv", "a\n1\n")
        p2 = self.dir / "x" / "x.csv"
        p2.write_text("b\n2\n", encoding="utf-8")
        conn = load_tables([str(p1), str(p2)])
        self.assertEqual(list_tables(conn), ["x", "x_2"])

    def test_semicolon_delimiter_auto(self):
        self.write("semi.csv", "a;b\n1;2\n3;4\n")
        conn = load_tables([str(self.dir / "semi.csv")])
        _, rows = run_query(conn, "SELECT b FROM semi WHERE a = 3")
        self.assertEqual(rows, [(4,)])

    def test_explicit_delimiter(self):
        self.write("pipe.csv", "a|b\n1|2\n")
        conn = load_tables([str(self.dir / "pipe.csv")], delimiter="|")
        _, rows = run_query(conn, "SELECT a + b FROM pipe")
        self.assertEqual(rows, [(3,)])

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_tables([str(self.dir / "ghost.csv")])

    def test_empty_csv(self):
        self.write("empty.csv", "")
        with self.assertRaises(ValueError):
            load_tables([str(self.dir / "empty.csv")])

    def test_query_only_and_prefix_guard(self):
        self.write("t.csv", "a\n1\n")
        conn = load_tables([str(self.dir / "t.csv")])
        with self.assertRaises(ValueError):
            run_query(conn, "DELETE FROM t")
        with self.assertRaises(ValueError):
            run_query(conn, "DROP TABLE t")
        _, rows = run_query(conn, "WITH x AS (SELECT 1 AS v) SELECT v FROM x")
        self.assertEqual(rows, [(1,)])

    def test_table_info(self):
        self.write("users.csv", "id,name\n1,张三\n2,李四\n")
        conn = load_tables([str(self.dir / "users.csv")])
        info = table_info(conn, "users")
        self.assertEqual(info["rows"], 2)
        self.assertEqual(info["columns"][0], {"name": "id", "type": "INTEGER"})
        self.assertEqual(info["columns"][1], {"name": "name", "type": "TEXT"})
        with self.assertRaises(ValueError):
            table_info(conn, "ghost")

    def test_chinese_headers_quoted(self):
        self.write("cn.csv", "城市,销售额\n北京,100\n上海,200\n")
        conn = load_tables([str(self.dir / "cn.csv")])
        _, rows = run_query(conn, 'SELECT "城市", "销售额" FROM cn WHERE "销售额" > 100')
        self.assertEqual(rows, [("上海", 200)])


if __name__ == "__main__":
    unittest.main()

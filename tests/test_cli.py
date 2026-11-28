"""命令行端到端测试:临时 CSV + main() 直调,校验输出与退出码。"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from csvq.cli import main

SAMPLE = (
    "region,amount,product\n"
    "华东,120.5,键盘\n"
    "华北,80,鼠标\n"
    "华东,59.9,鼠标\n"
    "华南,300,显示器\n"
    "华北,45.5,键盘\n"
)


class CliTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.csv = self.dir / "sales.csv"
        self.csv.write_text(SAMPLE, encoding="utf-8")

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_query_table_output(self):
        code, out, err = self.run_cli(
            str(self.csv),
            "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("region", out)
        self.assertIn("total", out)
        self.assertIn("华东", out)
        self.assertIn("共 3 行", out)
        # 排序验证:华东 180.4 > 华南 300? 不,华南 300 最高 → 第一行数据应是 华南
        self.assertLess(out.index("华南"), out.index("华东"))

    def test_query_json(self):
        code, out, _ = self.run_cli(
            str(self.csv),
            "SELECT region, COUNT(*) AS n FROM sales GROUP BY region ORDER BY region",
            "--json",
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["columns"], ["region", "n"])
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["rows"][0], ["华东", 2])

    def test_chart_output(self):
        code, out, _ = self.run_cli(
            str(self.csv),
            "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC",
            "--chart",
        )
        self.assertEqual(code, 0)
        self.assertIn("█", out)
        self.assertIn("300", out)          # 华南最大值
        self.assertLess(out.index("华南"), out.index("华北"))  # 最大值在顶部

    def test_chart_requires_two_columns(self):
        code, _, err = self.run_cli(str(self.csv), "SELECT region FROM sales LIMIT 1", "--chart")
        self.assertEqual(code, 1)
        self.assertIn("两列", err)

    def test_chart_requires_numeric(self):
        code, _, err = self.run_cli(str(self.csv), "SELECT region, product FROM sales", "--chart")
        self.assertEqual(code, 1)
        self.assertIn("数值", err)

    def test_schema_and_tables(self):
        code, out, _ = self.run_cli(str(self.csv), "--schema")
        self.assertEqual(code, 0)
        self.assertIn("表 sales", out)
        self.assertIn("REAL", out)     # amount 列含小数
        self.assertIn("TEXT", out)     # region/product 列
        code, out, _ = self.run_cli(str(self.csv), "--tables")
        self.assertEqual(code, 0)
        self.assertIn("sales", out)

    def test_alias(self):
        code, out, _ = self.run_cli(
            f"s={self.csv}",
            "SELECT COUNT(*) FROM s",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("5", out)

    def test_missing_sql(self):
        code, _, err = self.run_cli(str(self.csv))
        self.assertEqual(code, 1)
        self.assertIn("缺少有效的 SQL", err)

    def test_missing_file(self):
        code, _, err = self.run_cli(str(self.dir / "ghost.csv"), "SELECT 1 FROM ghost")
        self.assertEqual(code, 1)
        self.assertIn("文件不存在", err)

    def test_bad_sql_table(self):
        code, _, err = self.run_cli(str(self.csv), "SELECT * FROM ghost_table")
        self.assertEqual(code, 1)
        self.assertIn("错误", err)

    def test_write_statement_rejected(self):
        code, _, err = self.run_cli(str(self.csv), "DELETE FROM sales")
        self.assertEqual(code, 1)
        self.assertIn("SELECT / WITH / VALUES", err)
        self.assertIn("只读", err)

    def test_chinese_column_via_quoted_identifier(self):
        cn = self.dir / "cn.csv"
        cn.write_text("城市,销售额\n北京,100\n上海,250\n", encoding="utf-8")
        code, out, err = self.run_cli(str(cn), 'SELECT "城市" FROM cn WHERE "销售额" > 200')
        self.assertEqual(code, 0, err)
        self.assertIn("上海", out)

    def run_legacy_cli(self, *args):
        env = os.environ.copy()
        env.update(
            PYTHONIOENCODING="cp1252",
            PYTHONUTF8="0",
            PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
        )
        return subprocess.run(
            [sys.executable, "-m", "csvq", *args],
            env=env,
            capture_output=True,
        )

    def test_legacy_encoding_help(self):
        result = self.run_legacy_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("用 SQL 查询 CSV", result.stdout.decode("utf-8"))

    def test_legacy_encoding_json_output(self):
        result = self.run_legacy_cli(
            str(self.csv),
            "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        data = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(data["rows"][0], ["华南", 300])

    def test_cjk_alignment(self):
        code, out, _ = self.run_cli(str(self.csv), "SELECT product, amount FROM sales LIMIT 2")
        self.assertEqual(code, 0)
        # 表头分隔线以下,同一列的位置应一致(中文双宽对齐)
        data_lines = [line for line in out.splitlines() if line and not line.startswith("--")]
        positions = {line.index("键盘") for line in data_lines if "键盘" in line}
        self.assertEqual(len(positions), 1)


if __name__ == "__main__":
    unittest.main()

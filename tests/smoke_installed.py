"""在仓库外验证已安装的 csvq wheel,不读取源码树。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import sysconfig
import tempfile
from email.parser import Parser
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

import csvq

EXPECTED_VERSION = "1.0.1"


def run(*args: str, env=None, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(args, env=env, cwd=cwd, capture_output=True)


def main() -> None:
    dist = distribution("csvq")
    assert csvq.__version__ == EXPECTED_VERSION
    assert dist.version == EXPECTED_VERSION
    metadata = Parser().parsestr(dist.read_text("METADATA") or "")
    assert metadata["Requires-Python"] == ">=3.9"
    assert not metadata.get_all("Requires-Dist")
    assert set((dist.read_text("top_level.txt") or "").splitlines()) == {"csvq"}
    assert dist.locate_file("csvq/__init__.py").is_file()
    assert dist.locate_file("csvq/_vendor/cjktable/LICENSE").is_file()

    try:
        distribution("cjktable")
    except PackageNotFoundError:
        pass
    else:
        raise AssertionError("csvq wheel 不应安装顶级 cjktable 发行包")

    entry_points = [ep for ep in dist.entry_points if ep.group == "console_scripts"]
    assert len(entry_points) == 1
    assert entry_points[0].name == "csvq"
    assert entry_points[0].value == "csvq.cli:main"

    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sales = root / "sales.csv"
        sales.write_text("region,amount\n华东,120.5\n华南,300\n", encoding="utf-8")
        query = (
            str(sales),
            "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC",
        )

        result = run(sys.executable, "-m", "csvq", *query, "--json", env=clean_env, cwd=root)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        payload = json.loads(result.stdout.decode("utf-8"))
        assert payload["columns"] == ["region", "total"]
        assert payload["rows"] == [["华南", 300], ["华东", 120.5]]

        result = run(sys.executable, "-m", "csvq", *query, env=clean_env, cwd=root)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        assert "华东".encode("utf-8") in result.stdout

        script = Path(sysconfig.get_path("scripts")) / ("csvq.exe" if os.name == "nt" else "csvq")
        result = run(str(script), "--version", env=clean_env, cwd=root)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        assert result.stdout.decode("utf-8").strip() == f"csvq {EXPECTED_VERSION}"

        legacy_env = clean_env.copy()
        legacy_env.update(PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
        result = run(sys.executable, "-m", "csvq", "--help", env=legacy_env, cwd=root)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        assert "用 SQL 查询 CSV" in result.stdout.decode("utf-8")

        result = run(str(script), *query, "--json", env=legacy_env, cwd=root)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        assert json.loads(result.stdout.decode("utf-8"))["rows"][0] == ["华南", 300]

    print(f"csvq {EXPECTED_VERSION} installed wheel smoke test passed")


if __name__ == "__main__":
    main()

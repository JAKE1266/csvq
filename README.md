# csvq

> 用 SQL 查询 CSV:**单命令、即写即查**。基于标准库 sqlite3;唯一依赖是自研微库 [cjktable](https://github.com/JAKE1266/cjktable)(终端中文对齐排版)。

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/dependencies-cjktable%20%28self--built%29-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## ✨ 特性

- 🗃 **完整 SQL**:GROUP BY / 聚合 / JOIN / 子查询 / CTE,全部来自标准库 SQLite
- 🧠 **类型推断**:整列整数 → `INTEGER`,含小数/科学计数 → `REAL`,其余 `TEXT`;空单元格 → `NULL`
- 📊 **终端可视化**:`--chart` 直接把查询结果画成条形图(第一列标签、第二列数值)
- 📤 **可脚本化**:`--json` 输出结构化结果,管道友好
- 🈶 **中文友好**:中文列名自动加引号,表格按 CJK 双宽字符对齐
- 🍴 **分隔符自适应**:逗号 / 分号 / 制表符 / 竖线自动嗅探,也可 `-d` 指定
- 📚 **多表查询**:`users=users.csv orders.csv` 一库多表,直接 JOIN
- 🔒 **只读安全**:导入后连接锁为 query_only,写语句一律拒绝
- 🧪 **带测试**:29 个单元测试 + GitHub Actions 三系统 × 三 Python 版本 CI

## 📦 安装

```bash
git clone https://github.com/JAKE1266/csvq.git
cd csvq
python -m csvq --help           # 克隆即用

pip install .                   # 或安装为命令(获得 csvq 命令)
```

## 🚀 快速上手

```bash
# 每个区域卖了多少?
csvq sales.csv "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC"

# 直接画成条形图
csvq sales.csv "SELECT region, COUNT(*) FROM sales GROUP BY region" --chart

# 两张表 JOIN(别名语法)
csvq users=users.csv orders.csv "SELECT u.name, COUNT(*) FROM orders o JOIN users u ON o.uid = u.id GROUP BY u.name"

# JSON 输出给脚本用
csvq sales.csv "SELECT region, AVG(amount) FROM sales GROUP BY region" --json

# 看看有什么列
csvq sales.csv --schema
```

### 效果预览(500 行销售数据)

```
== 区域销售额 ==
  东北             ████████████████████████████████ 54936.2
  西南             ███████████████████████████████ 52530.2
  华南             ██████████████████████████████ 50999.2
  华北             █████████████████████████████ 50632
  华东             ██████████████████████████ 43873.9

共 5 行 · 11 ms
```

## 🧰 用法一览

```
csvq <文件[=别名]>... "SQL"      执行查询(SQL 必须是最后一个参数)
csvq <文件>... --schema          查看表结构
csvq <文件>... --tables          列出全部表
选项:
  -d, --delimiter  分隔符(默认自动嗅探:逗号/分号/制表符/竖线)
  --json           JSON 输出(保留数字类型)
  --chart          条形图(第 1 列标签,第 2 列数值)
  --limit N        条形图最多展示行数(默认 15)
```

## ❓ 常见问题

**Q: 表名从哪来?**
文件名主干(如 `sales.csv` → 表 `sales`);特殊字符会被转换为下划线。用 `别名=路径` 可自定义。

**Q: 中文列名能查吗?**
能。建表时自动为所有列名加引号;查询时请用双引号包裹:`SELECT "销售额" FROM sales`。

**Q: 类型推断规则?**
整列(忽略空值)全是整数 → `INTEGER`;混有小数或科学计数 → `REAL`;否则 `TEXT`。
推断是逐列进行的,同一列里 `007` 这类前导零值也会被当作整数;需要保留原样请整列混入一个文本值。

**Q: 会修改我的 CSV 吗?**
不会。数据导入内存 SQLite 后连接即锁定只读,原文件全程不打开写入。

**Q: 文件很大怎么办?**
全部载入内存,几十万行以内没有压力;再大的文件建议先用真正的数据库。
另有 `.import`/流式导入在路线图中。

**Q: 想发布到 PyPI?**
`csvq` 是占位名,发布前请在 `pyproject.toml` 换一个未被占用的名字。

## 📁 项目结构

```
csvq/
├── .github/workflows/ci.yml   # CI:Ubuntu / Windows / macOS × Python 3.9-3.13
├── src/csvq/
│   ├── core/
│   │   ├── importer.py        # CSV → SQLite:类型推断、NULL 处理、只读锁
│   │   ├── render.py          # CJK 对齐表格与条形图
│   │   └── util.py            # 单元格格式化(排版原语来自 cjktable)
│   └── cli.py                 # 命令行入口
├── tests/                     # 29 个单元测试(unittest 免安装可跑)
└── pyproject.toml
```

## 🧪 开发与测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
# Windows(PowerShell):$env:PYTHONPATH="src"; python -m unittest discover -s tests -v
```

## 🗺 路线图

- [ ] 大文件流式导入(分批 executemany)
- [ ] `--out out.csv` 查询结果落盘
- [ ] 多表 JOIN 时的表名补全提示

## 📄 许可证

[MIT](LICENSE) —— 可自由使用、修改与分发。

---

*同系列项目:[PyToolBox](https://github.com/JAKE1266/py-toolbox) 多功能工具箱 · [CashBook](https://github.com/JAKE1266/cashbook) 命令行记账本 · [gitdash](https://github.com/JAKE1266/gitdash) Git 终端仪表盘 · [DevBox](https://github.com/JAKE1266/devbox) 前端开发工具箱 · [cjktable](https://github.com/JAKE1266/cjktable) CJK 排版微库 · [duviz](https://github.com/JAKE1266/duviz) 磁盘占用可视化 · [httpoke](https://github.com/JAKE1266/httpoke) HTTP 调试工具 · [mdown](https://github.com/JAKE1266/mdown) Markdown→HTML · [msite](https://github.com/JAKE1266/msite) 静态文档站 · [crony](https://github.com/JAKE1266/crony) cron 表达式解析 · [pomo](https://github.com/JAKE1266/pomo) 番茄钟 · [termplot](https://github.com/JAKE1266/termplot) 终端数据图表 · [filewatch](https://github.com/JAKE1266/filewatch) 目录变更监控 · [packpeek](https://github.com/JAKE1266/packpeek) 压缩包检查与安全解压 · [statline](https://github.com/JAKE1266/statline) 统计摘要 · [difftool](https://github.com/JAKE1266/difftool) 文本差异 · [wordfreq](https://github.com/JAKE1266/wordfreq) 词频统计 · [hexview](https://github.com/JAKE1266/hexview) 十六进制查看器 · [quicktodo](https://github.com/JAKE1266/quicktodo) 待办清单 · [envcheck](https://github.com/JAKE1266/envcheck) .env 校验 · [ipcalc](https://github.com/JAKE1266/ipcalc) 子网计算器 · [quickjournal](https://github.com/JAKE1266/quickjournal) 速记日志 · [csv2md](https://github.com/JAKE1266/csv2md) CSV→Markdown*

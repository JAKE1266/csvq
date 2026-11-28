# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式,
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.1] - 2026-11-28

### 修复
- cjktable 改为 `csvq._vendor.cjktable` 私有 vendor,移除 Git 运行时依赖与顶级包冲突
- CLI 标准流固定 UTF-8,修复 cp1252 旧编码环境下中文帮助和查询输出崩溃
- sdist 补齐 CHANGELOG、测试与 vendor 许可证

### 新增
- 31 个单元测试,新增旧编码环境回归
- 已安装 wheel 仓库外冒烟测试
- GitHub Actions 真实 wheel:Ubuntu / Windows / macOS × Python 3.9–3.13

## [1.0.0] - 2026-11-21

### 变更
- 终端排版(CJK 对齐 / 截断)改用自研微库 [cjktable](https://github.com/JAKE1266/cjktable),删除内嵌实现

### 新增
- CSV 一键导入内存 SQLite:列类型自动推断(INTEGER / REAL / TEXT),空单元格转 NULL
- 完整 SQL 能力:GROUP BY / 聚合 / JOIN / CTE / 子查询(基于标准库 sqlite3)
- 分隔符自动嗅探(逗号/分号/制表符/竖线),可用 `-d` 显式指定
- `别名=路径` 表名重命名;多文件多表同库查询
- `--schema` 表结构、`--tables` 表清单
- `--json` 结构化输出;`--chart` 终端条形图(第一列标签、第二列数值)
- 中文列名/表名支持(自动引用标识符);终端表格 CJK 双宽对齐
- 只读保护:导入后连接锁为 query_only,写语句被拒绝
- 29 个单元测试;GitHub Actions 三系统 × 三 Python 版本 CI

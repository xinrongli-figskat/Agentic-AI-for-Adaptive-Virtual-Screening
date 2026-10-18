# 项目输出目录

这里保存项目 brief、方案、代码、测试和分析产物。目录整理只移动文件；既有数据、标签、阈值和结论未被改写。

- 原始 brief 仍在顶层，因为现有复核脚本按这个路径读取；`brief/` 保存项目进度对照和给导师的材料。
- `protocols/frozen/` 与 `protocols/drafts/`：存放可安全移动的协议文件。Task 1 v5 和 monthly guidance 仍在顶层，直到引用它们的脚本完成路径迁移。
- `scripts/`：可安全移动的一次性脚本按发现、整理、来源审查、验证和运维分类。路径敏感或仍被引用的脚本暂留原位，见 `deferred_moves.md`。
- 可复用 Python 包和测试继续留在 `outputs/` 顶层，保持现有导入方式。`src/README.md`、`tests/README.md` 说明后续整理条件。
- `private/` 保存本机逐化合物记录；其中数据文件被 Git 忽略。其他旧结果和历史数据也按 `.gitignore` 排除。公开控制器和报告不得直接读取私有标签。
- `_archive/` 放历史传输包，`devlog/` 放编号过程记录。
- `INDEX.md` 列出当前顶层条目；`PATH_MIGRATION_20261018.csv` 记录移动前后位置和哈希。
- `s_restructure_20261018/` 保存本次整理的盘点、隐私审计、偏离记录和最终核验。

远端工作站和项目根目录的 `.sync_audit/` 不属于本次整理范围。

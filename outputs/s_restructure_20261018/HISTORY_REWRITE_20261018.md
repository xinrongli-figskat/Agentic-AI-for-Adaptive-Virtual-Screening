# 首次推送前的历史改写（2026-10-18）

## 原因

S7 复核发现：已提交的盘点类文件逐行列出了 Git 忽略文件的路径、大小和 SHA-256，其中包括含化合物编号的文件名；0bf2031 的 `PATH_MIGRATION_20261018.csv` 还含 37 行私有目录迁移记录。私有数据文件本身从未进入 Git。仓库尚无远端，因此在首次推送前改写本地历史。

## 改写范围

用 `git filter-branch --index-filter` 只替换以下文件的 blob，作者、日期和提交说明不变：

- `inventory_before.csv`、`inventory_after.csv`、`duplicates.csv`：删除路径从未被 Git 跟踪的行。
- `hardcoded_paths.csv`、`hardcoded_paths_after.csv`、`recorded_paths.csv`：删除 `file` 列为未跟踪文件的行。
- `secrets_scan.md`、`inventory_summary.md`：删除指向未跟踪文件的表格行，并在文末加一行说明。
- 0bf2031 中的 `PATH_MIGRATION_20261018.csv`：删除 37 行 `r4_source_review_private_20261018/…`；其余行不变。
- 原 1311181 中的 `MANIFEST.json` 与 `MANIFEST.sha256`：同步更新上述文件的字节数和哈希。

逐文件删除行数与完整清单哈希见 `inventory_redaction_note.json`。完整清单和改写前历史备份保存在 Git 忽略的 `outputs/private/s_restructure_ledger/`。

## 验证

- 逐提交比较改写前后，变化只出现在上述文件。
- 改写后各提交中，上述清单文件不含化合物编号文件名，也不含未跟踪路径的行。
- 用私有完整清单重新对账：1,953 个原路径原哈希、166 个迁移后哈希一致、1 个 `.pyc` 按 S4 记录删除，无未解释缺失。
- `MANIFEST.json`、`MANIFEST.sha256` 校验通过；freeze_v1、Dyrk3 pre-freeze、ChEMBL 汇总测试通过。
- 旧引用和 reflog 清除后执行 `git gc --prune=now`。

## 提交号对照

日志与说明文件中的旧提交号按下表对应：

|旧|新|提交说明|
|---|---|---|
|a270d7d|884b8a0|Baseline snapshot before outputs reorganization; content unchanged|
|6172ac5|f15e73d|Record archive plan and privacy exclusions before moves|
|f3c86b3|5a8214a|Archive historical transfers and numbered project notes|
|2d4fffa|755a9f2|Record S4 path map and integrity verification|
|4f01409|933fb2d|Record S5 movement assessment and destination structure|
|579cd18|5616906|Add verified S5 move procedure|
|a53c6f9|fd8655e|Reorganize brief, protocol drafts, and standalone scripts|
|0374dca|1c14777|Record S5 migration map and compatibility findings|
|d7e9127|0d25704|Add S6 private data relocation procedure|
|0bf2031|8937247|Isolate local compound-level review records|
|1311181|468cb6d|Finalize S1-S7 outputs reorganization and reconciliation|

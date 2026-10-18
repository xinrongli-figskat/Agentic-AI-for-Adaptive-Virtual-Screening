# S1–S7 项目整理运行记录

本机根目录：`C:\Users\lixinrong\Documents\Codex\2026-10-09\agentic-ai-for-adaptive-virtual-screening`。远端 `/driveA/xinrong/agentic-screening` 和根目录 `.sync_audit` 本轮未触碰。

## S1：只读盘点

- 状态：完成。开始/结束 UTC：见 `s1_digest_check.json`。
- 命令：`python -B outputs\s_restructure_20261018\s1_inventory.py`。
- Python：3.13（本机运行时）；PowerShell：5.1/7 主机版本由本次终端提供。
- 脚本 SHA-256：见本目录 `MANIFEST.json`。
- 扫描文件 2,120 个；总字节 119,766,949；路径+内容序列 SHA-256 前后相同：`6c58f101564afb3bb4ff4dd9a386680e6d0f3a33dd62b6b5700ff3c02881f881`。
- 扫描排除本任务证据目录 `s_restructure_20261018`，避免自包含循环；S7 使用相同排除。

## S2：密钥与隐私扫描

- 状态：通过。扫描 outputs 文本文件 2,031 个。敏感词命中是配置名或说明文字，不等于密钥；3 个长字符串语法候选逐项核对均为 URL/路径中的字符组合，没有发现真实凭据。
- `lab-4090.ssh_config`：hostname、username、identity_file 存在；port 未设置。没有把字段值写入报告。
- `.gitignore.draft` 仅是草案；根目录 `.gitignore` 由 S3 建立，并因用户确认未来会推送 private GitHub，排除私有标签目录、已识别的非 private 标签数据路径、环境与 `.sync_audit`。

## S3：Git 基线与索引

- 开始时根目录无 `.git`。创建本地分支 `restructure-20261018`，没有配置远程。
- 版本控制前的标签筛查识别出 154 个含 compound/measurement 结构信号的文件，集中于 12 个非 private 顶层目录；这些路径已在 `.gitignore` 排除。4 个数据型归档也排除。
- 基线提交：`a270d7d`，447 个跟踪文件；未发现 >100 MB 的跟踪文件；仓库当前没有 remote。
- `INDEX.md` 覆盖整理前 outputs 顶层条目，并记录 R3、B1、monthly guidance 与 v4 summary 的版本关系。
- `git diff --cached --check` 发现 ChEMBL schema 文档有既存行尾空白；为保持基线内容不变，没有修改该文件。基线提交仍成功。

## 后续步骤

S4–S7 执行结果将按步骤追加；所有移动按原文件 SHA-256 核验，不改冻结内容、标签、门槛或结论。

## S4：低风险归档准备

- 当前阶段：移动前准备已记录；归档目录已创建，清单文件仅有表头，尚未移动文件。
- 预计移动：历史传输包及配套校验/receipt、02–39 编号开发记录（01 原始 brief 留下）、被取代的 R3 排名目录、过期的 v4 terminal summary。
- `.cache` 与 `__pycache__` 将在核实绝对路径位于 `outputs` 内后删除，并记录文件数；根目录缓存不动。
- `s1_inventory.py` 和 `s2_secrets_scan.py` 的 SHA-256 收录于最终 `MANIFEST.json`。

## S4：归档低风险内容

- 状态：完成。PowerShell 7.6.5、Python 3.13.3。移入归档/开发记录共 78 个文件：29 个 transfer 包及配套文件、38 条编号笔记、11 个 superseded 文件。每个目标文件的 SHA-256 与 `inventory_before.csv` 一致。
- 移动提交：`f3c86b3`；提交差异只有重命名，内容未改动。迁移映射记录在 `outputs\PATH_MIGRATION_20261018.csv`。
- 缓存：`outputs\__pycache__` 删除 1 个 `.pyc` 文件；`outputs\.cache` 是空目录/缓存视图，删除该目录时没有文件；项目根 `.cache` 在本步范围外，保留。
- 顶层核对：S1 摘要为 229 项；随后新建 INDEX、PATH_MIGRATION、_archive、devlog 共 4 项；本步移走 68 个原顶层条目并移除两个 cache 目录；当前 163 项。净减少与移动数不同，差异由上述新增与缓存目录解释。
- `move_s4.py`、`verify_s4.py` 哈希收录于最终 MANIFEST。

## S5：分层重组准备

- 代码包继续留在顶层；按规则分类 66 个顶层一次性脚本，27 个没有外部代码引用且不依赖变化路径的脚本将移动，39 个因为代码引用或 `__file__` 根路径假设暂缓。
- 15 个测试全部暂缓：它们导入顶层项目脚本/包，或基于 `__file__` 计算数据路径。逐项理由见 `test_movement_assessment.csv` 与 `deferred_moves.md`。
- 计划将原始 brief、brief 进度复核、冻结协议、草案指导和环境配置放入目标层级；不移动 `results/` 等审计发现含化合物级记录的目录。
- 分类与移动清单已生成；正式移动后将逐文件核对 S1 哈希，并追加路径映射。


## S5：按资料和用途分层

- 状态：完成。所有实际移动逐文件核验 SHA-256；映射表中记录 57 个文件（56 个受 Git 跟踪的重命名，另有 1 个本机 SSH 配置文件，已由 `.gitignore` 排除）。
- brief 材料归入 `brief/`；Task 1 v5 文件归入 `protocols/frozen/`；monthly guidance 草案归入 `protocols/drafts/`；27 个安全的一次性脚本归入 `scripts/` 的用途子目录。可复用代码包仍在顶层，测试仍在原位置。
- 39 个脚本因外部引用或 `__file__` 路径依赖暂缓；15 个测试因导入和路径依赖暂缓，原因见 `outputs/deferred_moves.md` 与分类表。包含化合物级数据的结果目录未移动。
- 测试：在 `outputs/` 运行 `python -B -m unittest freeze_v1.test_create_version test_summarize_chembl37_curation` 通过；在 `outputs/dyrk3_prefreeze_v0/` 运行 `python -B -m unittest test_prepare_pool` 通过。一次从 `outputs/` 根目录导入 prefreeze 测试的尝试失败，原因是该测试预期以包目录作为当前目录；改用既有预期工作目录后通过。
- 偏离：起初试移 `freeze_v1/` 与 `dyrk3_prefreeze_v0/` 后，原有模块入口/测试不能导入；已恢复这两个可执行模块到原位，未改代码。`protocols/frozen/` 只接收真正的协议文件。
- 提交：纯重命名提交 `a53c6f9`；S5 分类与迁移记录将在独立元数据提交中保存。

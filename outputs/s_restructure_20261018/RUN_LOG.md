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

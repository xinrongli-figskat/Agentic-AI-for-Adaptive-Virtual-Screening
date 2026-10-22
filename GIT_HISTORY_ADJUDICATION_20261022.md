# Git 历史路径内容裁定（2026-10-22）

本文件仅裁定指定的 7 个路径。检查包含工作区现有内容与 `git log --all` 中的历史版本；本阶段没有提交、推送、修改索引、`.gitignore`、历史或 remote，也没有刷新远端。原 `BLOCKED_GIT_HISTORY.md` 与 `PUBLISH_AUDIT_20261021.json` 原样保留。

| 路径 | 当前 SHA-256 | 裁定 | 具体证据 |
|---|---|---|---|
| `outputs/private/README.md` | `53dd6ec921eb1972d0fc1c04c67920ee74e33567d86b2a7f5d62aceea62a6dad` | `PUBLISH_OK` | Three-line notice about private label storage and public/private separation. It enumerates no per-compound label, outcome, structure–result pair, activity value, or credential. |
| `outputs/s_restructure_20261018/audit_s6_private.py` | `6cad1429ebe37f1476abfff0fe79800378e16413da01cabc29ca65cc80ee68fa` | `PUBLISH_OK` | Script classifies files and counts label-bearing files by path group; output schema contains grouped paths, booleans, and counts only. It does not write individual sample data or a matched credential value. Hard-coded absolute path contains username only. |
| `outputs/s_restructure_20261018/move_s6_private.py` | `3cea89cc990d54f10c10bc73c03ca5b7638f8f033edceba6f72e6c08616b0ee7` | `PUBLISH_OK` | Script moves private files while checking hashes and writes old/new relative paths, SHA-256, and time to an ignored mapping file. No embedded sample rows, activity values, or credential values; hard-coded absolute path contains username only. |
| `outputs/s_restructure_20261018/s2_secrets_scan.py` | `30ebca8425eca11b8103d0a09f8592ec3853f3bac02ba23d065009a36f220a3f` | `PUBLISH_OK` | Historical versions write secrets_scan.md rows with file path, line number, and matched pattern names, plus SSH-field presence; no matched string or partially masked value. Also writes a .gitignore draft. Literal regular expressions and generic placeholders are code, not credential values. Hard-coded absolute path contains username only. |
| `outputs/s_restructure_20261018/s6_private_audit.csv` | `9819f966164dcf94c7fcd2caf0c5e118a451fb61e9f9ae0973aa1f33d3f45b35` | `PUBLISH_OK` | Actual CSV header is path_group,private_named_path,reverse_scan_nonprivate,files_scanned,compound_level_label_files,archive_label_data_files,git_ignored_label_files,git_unignored_label_files,scan_errors. All 30 rows contain only path-group names, booleans, or counts; no cmp_-prefixed key and no molecular outcome, label, structure–result pair, or activity value. First 3 and last 3 rows are summarized in Markdown. |
| `outputs/s_restructure_20261018/S6_PRIVATE_AUDIT.md` | `1e658c3932918ba26ce0913557f269e1c5d4e16cb8bccf3a3f090ef19f5b83ae` | `PUBLISH_OK` | Eleven-line grouped audit summary reports numbers of directories/files and ignored private mappings. It contains no compound/activity identifier paired with an outcome, no numeric activity, and no credential value. |
| `outputs/s_restructure_20261018/secrets_scan.md` | `670f8086de1c32d403d7268883fa06b26e2b6dfe0b667c062129fc3cbbf48dff` | `PUBLISH_OK` | Historical Markdown reports use file/line/pattern tables (three cells), SSH-field presence, totals, and explanatory text. Keyword and credential-style hits are locations and pattern categories only; no matched value, masked prefix, per-molecule label, structure–result pair, or activity value. |

CSV 实际表头：`path_group, private_named_path, reverse_scan_nonprivate, files_scanned, compound_level_label_files, archive_label_data_files, git_ignored_label_files, git_unignored_label_files, scan_errors`。共 30 行；`cmp_` 开头化合物键出现行数：0。前 3 行与后 3 行（仅路径分组及计数）：

```csv
path_group,private_named_path,reverse_scan_nonprivate,files_scanned,compound_level_label_files,archive_label_data_files,git_ignored_label_files,git_unignored_label_files,scan_errors
r3_ranked_numeric_private_20261018,true,false,10,0,0,,,0
_archive,false,true,3,0,3,3,0,0
a2_llm_input_audit_private_20261017,true,false,16,0,0,,,0
task1_v1_review_20261015,false,true,2,2,0,2,0,0
task1_v2_delivery,false,true,2,2,0,2,0,0
task1_v2_validation,false,true,2,2,0,2,0,0
```

历史版本的 Git blob SHA-256 与提交号、逐项证据见同名 JSON。`secrets_scan.md` 的历史表仅有文件、行号、模式三列；扫描脚本没有把匹配值或保留前缀的打码值写入报告。

## 远端跟踪分支快照

- `origin/restructure-20261018`：`c33eb33fb01707afa1b50c4804525433aaebe5f6`；7/7 路径均已存在于该快照。仓库目前为 private（用户确认），因此这是预防性审查，不是公开泄漏结论。
- 本地领先 3 个提交；远端跟踪分支领先 0 个提交。未执行 `git fetch`，这些数字不代表实时远端状态。
- 当前 `origin` 拼写与已确定的最终仓库名不同；用户须先在 GitHub 改名，之后才能更新并核验 remote。

## 后续

七项均为 `PUBLISH_OK`，本次不需要为这七项改写历史。按发布任务卡从 A-3 继续索引检查，补齐 `.gitignore` 并跑 A-5。只在用户完成 GitHub 改名、remote 身份与分支 SHA 核验、全部发布检查通过后提交与推送。转为 public 前必须重跑 `PRE_PUBLIC_CHECKLIST.md`；private 推送通过不代表可以公开。

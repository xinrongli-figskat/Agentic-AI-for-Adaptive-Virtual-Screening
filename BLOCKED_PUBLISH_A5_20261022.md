# GitHub 发布阻塞：A-5 逐分子活性值（2026-10-22）

状态：**硬停止，未提交、未推送、未改写历史、未修改 remote**。仓库当前为 private（用户确认）。此处记录文件结构与哈希，不复制任何活性数值。

## 已完成的检查

- 7 个历史路径已在 `GIT_HISTORY_ADJUDICATION_20261022.json` / `.md` 中逐一裁为 `PUBLISH_OK`。7/7 位于本地保存的 `origin/restructure-20261018` 树；未执行 `git fetch`。
- A-3：按原任务卡将 5 个正则命中的安全路径仅从 Git 索引移出；本地文件仍在。再次运行 A-3 的索引路径正则，无命中。当前改动尚未提交。
- A-4：补充 `data/curation_private/`、任意层级 private、`oracle_labels*`、`llm_receipts/`、环境目录等忽略规则；原任务卡列出的 9 个样例及 `outputs/private/README.md` 均已由 `git check-ignore --no-index -v` 确认忽略。
- A-5 公开候选接口：本地拟发布的两份 TNAP `candidates.jsonl` 各 462 行，每行字段集**恰为** `compound_key`、`standardized_smiles`，化合物键各自唯一。
- A-5 体积：当时拟发布集合 1,039 个常规文件，共 7,579,554 字节；无文件超过 5 MB 或 50 MB。

## 阻塞证据

| 已跟踪文件 | 工作区 SHA-256 | 结构性证据 |
|---|---|---|
| `outputs/acc2_patent_us8835472_sample_values.json` | `6be6d45e704c4e4b00c0f3fd6fa771a5bafaae5a7027e40ada0ac9c9f10afc08` | `values` 为 12 条逐例号记录；每条同时含 `example` 与 `ic50_uM`。 |
| `outputs/tace_patent_us9926281_sample_values.json` | `4c1c508702a3a353d339feaf8b6c5d21110457717394af1c3ccb45d67dd2ebf2` | `source_values` 为 12 条逐记录数据；每条同时含 `activity_id`、`compound_numbers`、`relation` 与 `value_nM`。 |

两份文件均在本地保存的 `origin/restructure-20261018` 树，最早见于基线提交 `884b8a0`。当前 private 仓库中的存在不等于公开披露；但未来转 public 时历史也将一并可见。A-5 原卡明确要求“逐分子结果一律不得出现”，故这里硬停止。路径正则没有识别它们，表明只依靠文件名扫描不充分。

## 未完成与待裁决

- A-5 的凭证扫描目前只有自动候选匹配，尚未对所有命中逐项完成语义核验；不能写成“密钥检查通过”。
- 这些源文献摘录是否要从发布集合移出，以及**历史中既有副本**如何处理，需用户另行裁决。仅从当前索引移出不能清除旧 Git 历史；也不得把重写历史当成自动修复。
- GitHub 仓库尚未由用户确认已改名为最终拼写 `Agentic-AI-for-Adaptive-Virtual-Screening`；`origin` 未变更。
- 不进入骨架提交、分支推送或干净 clone 复验。`PRE_PUBLIC_CHECKLIST.md` 的仓库提交也待安全阻塞解除后进行。

建议的安全处置是：先决定这两份 12 条的源摘录是否允许随历史保留。若不允许公开，必须在转 public 前单独处理既有历史，并在 private 仓库中重新核验全部历史与远端副本；任何历史改写须另行授权，且不得 force-push 默认分支。

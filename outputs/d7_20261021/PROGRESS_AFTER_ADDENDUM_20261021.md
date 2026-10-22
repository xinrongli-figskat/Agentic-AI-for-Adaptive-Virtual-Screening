# D7 补订后的进度核查

记录时间：2026-10-21 UTC。性质：post-exposure 进度记录；不是新 benchmark、冻结声明或历史结果更正。

本轮收到的 D7 补订与已锁定文件逐字节一致，SHA-256 为 `fb5b81850f20aa7353ca564a6615f78f85f8694a05dad71af1189e5e7f36ced8`。本机已有锁定副本，未重写任务卡或历史产物。

## 已完成并核验

- **S-1 来源规则 v3 与 62 项凭证表**：规则和结果位于 `d_identity_gate_v2/revision_v3/`。62 行、25,813 个支持身份；43/62 项来自 `src_id=37`。TNAP 通过预定的 shortlist 条件，TACE 未通过。此结果是凭证计算，不等于完成原始来源审查，也不代表 campaign-ready。
- **S-2 新门槛的离线补算**：10,000 次配对 bootstrap 已完成。TNAP bit/count 下界为 3.95/3.50，且池级判别力通过；DYRK3 bit/count 下界为 1.55/0.90，且池级判别力不通过。因此新门槛仅允许既有 TNAP bit/count 格子通过；这不自动授权新代理模型格子的 GLM 运行。
- **S-3 记录修订**：已撤回“四个决策点压低固定策略跨度”的解释；记录了 `spread_nontrivial`（固定策略之间差多少）与 `adaptive_gap`（事后最佳固定策略与自适应策略之间差多少）不是同一指标。此前基于 SD=4.20 的四个“校正区间”只保留为算术复现，不作为正向收益证据。
- **D7-B 封存**：私有证据包 213 个成员哈希核验通过。33/100 组已完成，其中复用 D6 的 10 组、新增完整 23 组；新增 94 次物理请求中 93 次有效、1 次返回格式不合要求。无效决策没有触发 oracle 查询。完成预定 20×5 设计还需 267 次有效决策，而 360 次上限下只余 266 次，故按 Tier B 停止，未重试、未放宽解析规则、未改预算。B2/B3 不能按原设计完成。
- **D7-C**：C1 的规格与代码已锁定；TNAP 与 DYRK3 输入池的键和哈希在本机核验通过。C2/C3 未运行：本机缺少 RDKit、scikit-learn、SciPy 及实时 DYRK3 冻结目录/ChEMBL SQLite；因此不推断代理模型的强弱顺序，也不进入 C4 GLM。

## 尚未完成

- **D-A4：8 个未暴露候选的四阶段 GLM 案例审查**尚未运行。锁定名单哈希为 `53ed6e0ec32bae19bc984b640566154ff69dd98080f90543433c038ba7b4a6c8`；名单没有改动，执行目录尚不存在，A4 GLM 调用数为 0。若之后获准执行，仍须遵守每候选最多 4 次、总计最多 40 次，不计算 precision/recall，并保持 `campaign_ready=false`。
- **D7-C2/C3/C4**尚未运行；在 C2 两池代理顺序条件无法验证前，不得用 S-2 的旧格子结果代替门槛，也不得发 C4 GLM 请求。
- **D7-B 的精确 20×5 重复矩阵**按现有 360 次硬上限无法完整完成。恢复需新的、明确的方案决定；本记录不自行增加调用上限或改变设计。

## 远端访问边界

先前对远端项目内容进行枚举的 SSH 操作遭到自动审批系统拒绝。拒绝说明这是内容安全审查失败，未判定为不安全；给出的理由是所读取的生物相关项目内容可能被用于有益或有害用途。为遵守“不得绕过审批”的要求，本轮没有换用 scp、shell wrapper 或其他路径重试，也没有发起 A4 远端查询或 GLM 调用。需要继续远端工作时，应先由用户指明获准的执行/材料交付方式，或提供已在获准环境中生成的 A4 输入与回执供本地核验。

## 关键产物

- 本记录的哈希见同目录 `PROGRESS_AFTER_ADDENDUM_MANIFEST.json`。
- S1 结果：`d_identity_gate_v2/revision_v3/credential_62.csv`、`gate_decisions_62.csv`、`verification.json`。
- S2/S3：`a_headroom_bandit/s2_s3_addendum/s2_gate_reanalysis.json`、`adaptive_gap_descriptive.json`、`PREREGISTRATION_OUTCOMES.md`。
- B Tier B：`b_model_variance/CLOSEOUT_TIER_B.json`、`BLOCKED_response_format_budget.md`、`MANIFEST_TIER_B.json`；私有证据包在 `b_model_variance_private/partial_evidence_tier_b.zip`，SHA-256 `89be98316dcbfcc46e48298fa55013ccf12b8cc28531da6939d289c1fd4fcf7b`。
- C 阻塞记录：`c_surrogate_factor/BLOCKED_LOCAL_C2_C3.md`。

以上工作没有创建新的 benchmark，也没有把任何候选标成 campaign-ready。

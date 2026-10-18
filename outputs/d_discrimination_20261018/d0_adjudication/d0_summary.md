# D0：TNAP 来源缺口的判定记录

本卡对应 brief 中三个要求：开发期间复盘并论证标准与折中；区分 assay 定义的命中与直接结合证据；按数据能否支持回顾性评价决定适用性，而非按靶点生物学优先级选择。

我们先锁定了适用于后续候选的一般规则，再依规则将 TNAP CHEMBL1738510 的未说明蛋白表达构建体/制备方法暂归为 `limited`。已核对的 AID 1056 与 ChEMBL 记录是 485/485 对齐，固定主样本为 12/12；读出为同一方法描述下的 `IC50_Mean`。构建体缺口限制池外解释，不能把实验定义的活性声称为直接结合。

该判定**不使 TNAP 进入 campaign**。冻结前还须逐行确认 485 条记录的读出列同质，并按整理规则解释 485 条原始记录到 462 个可用化合物的 23 条差额。任一检查不能完成或失败，就按规则转为 `unverifiable` 或 `blocker`。原 [排名表](../../r3_ranked_numeric_private_20261018_v2/provisional_shortlist.csv) 未修改；[状态更新](tnap_status_update.csv) 单独保存，`campaign_ready=false`。

规则文件在 2026-10-18 14:15:43 UTC 锁定，SHA-256 `c63bdf0c28e5560db97f304ae9d346f73cdbd36e059071c72ee13f3e555212e3`；个案文件随后在 14:16:15 UTC 保存，SHA-256 `7cd0f9f620bfeb20c1af63a458795972bca4560c2b97065c76354857f5daf372`。两份文件均位于 [协议草案目录](../../protocols/drafts/README.md)。本判定属 post-exposure，不回写既有冻结协议或历史决定。

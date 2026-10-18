# Task 1：p300 整理证据与继续运行超时

来源：用户附件 e5d1ef34-3693-429f-8d0e-cffe44d4fd22 的远端只读检查及 execute 输出。
本地读取了该附件和当前程序源码，未直接访问远端 state；不修改本轮源码、提示词、协议或数据。
本记录目前仅保存在本地。

## 已核实的 p300 数据摘要

实验 CHEMBL5737918，蛋白目标 CHEMBL3784 Histone acetyltransferase p300。
完整获取 379/379 条单实验 IC50 记录；用户执行的整理证据哈希核查 PASS。
标准化身份状态：179 hit_support、189 nonhit_support、4 threshold_disagreement、3 unknown。
总计 375 个已形成的标准化身份，其中 368 个进入暂定可用池；4 个冲突和 3 个未知不作为非命中。
source_ids_quarantined=0 是来源 ID 层面的结构隔离数量，不等于没有标签冲突/未知。
从 379 条测量到 375 个标准化身份的精确归并路径需要检查 records/source_id_audit/compounds，不能仅从计数推断具体丢失或重复原因。

唯一失败的数值资格项为 usable_compounds（368<500）；其余本轮数值项均为 true。
scientific_review_complete 和 campaign_ready 仍为 false。

## 多样性通过本轮门槛，不代表类似物问题消失

- 63 个精确 Murcko 骨架，25 个 generic 骨架，0 个无环结构；64 个 Butina 簇。
- 最大 Butina 簇约 15.49%（57/368），通过本轮 <=25% 条件。
- 最大精确骨架 113/368，约 30.71%。
- 最近邻 Tanimoto 中位数 0.87222。
- 305/368，约 82.88%，至少有一个 Tanimoto>=0.85 的近邻。
- >=0.85 的高相似度配对只占所有配对约 0.382%，与很多分子各有少数近邻并不矛盾。

骨架计数、精确骨架相同和 Morgan/Butina 分组测量的是不同方面；不能用最大簇较小替代对类似物冗余的解释。
若未来采用这个池，应进一步审查系列集中、类别与系列关系、计数表示的分辨率以及结论适用范围。
未进行新 campaign，不推断性能或泛化。

## P2X2 实验

实验 CHEMBL5732233，目标 CHEMBL2531 P2X purinoceptor 2。
已完整获取 419/419 条记录，尚未结构整理。
在当前单实验、实验表征化合物范围下，即使每条记录对应一个不同可用化合物，也不足 500。
这一可计算的上界可供后续判断，不能先称该池合格；也不代表此实验没有研究价值。

## 超时定位

最新 execute 在任何新增 attempt 行之前返回 error_type=TimeoutError，message=The read operation timed out。
当前 run_steps 每次先调用 engine.client.get('status') 检查 ChEMBL release，随后才增加 llm_attempts 并请求 GLM。
当前 GLM.call 会将网络 TimeoutError 包装为 RuntimeError 并保存 transport_error 回执。
因此错误路径强烈指向开始时的 ChEMBL status 请求，而不是新的 GLM 请求；仍需检查远端 llm_attempts、requests 最后一项的 URL/error 和新回执来确认。
开始检查的失败会由原 Client 保存为一次 HTTP 尝试，已有证据、整理及决定不会因该超时被重置。
不应仅凭 timeout 宣称智谱余额、密钥或模型有问题，也不应修改已哈希锁定的代码或协议来掩盖故障。

下一步：只读检查 state 的最后请求及累计决策，再按相同配置重试同一运行一次。若反复失败，再针对实际失败的服务做网络诊断；不要无限重试或重建运行来抹除故障记录。

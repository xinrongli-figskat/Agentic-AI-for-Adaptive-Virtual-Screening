# D5 run log

- 2026-10-20：复制任务卡及用户修订，核对 DYRK3/TNAP 冻结凭证和旧 campaign 核心代码哈希；四个独立子任务 A–D 并行执行，A/B/C 不调用 GLM，D 仅审查六个参照候选。
- 第一波结束：A/B/C/D 的状态均为 `done`，D 使用 24/30 次 GLM 请求。四份 MANIFEST 共 73 个成员文件经 `verify_wave1.py` 重算哈希通过，无观察到的 D5 子目录交叉写入。主代理先写 `d5_wave1_synthesis.md`，再开始第二波。
- 11:48:53 UTC：锁定扩展菜单规格 `d5_menu_spec.md`，SHA-256 `8c88799469e193046a404a91bf8fcfb67b71313a46c777dbe983994f87f5252d`；旧三策略不变，GLM 仅 TNAP，扩展 CPU 两池。
- 随后锁定五份 campaign 核心/预检代码（`e_menu_code_lock.json`，SHA-256 `5cd4edae70c83519a75eb9e90068ad3444128cb0375239479c66d4f860625859`）。合成标签下 28 组完整 campaign、3 项扩展菜单测试通过；真实 API 的合成决策探测成功，明确 `do_sample=false`。
- 首个真实 TNAP bit 种子 0 的固定旧 greedy 回归得到 H@50=28，与 D3 保存结果一致。TNAP bit 种子 0–9 完成 40/40 个 GLM 决策，50 次查询/种子、无失败；检查点保存于 `e_menu_bit_checkpoint.json`。随后才跑剩余 GLM 种子。
- CPU 固定/均匀混合 640/640 组完成；TNAP GLM 扩展 40/40 组、160/160 次 GLM 决策完成。无越池、重复查询、pending 或失败事件。扩展 CPU 运行脚本单独锁哈希，未改变已锁 campaign 核心。
- 12:14 UTC 后：依据 GLM 实际策略选择构造事后权重（`e_menu_matched_weights.json` SHA-256 `9da154e345ea58f64ede5002e23056ef6d6462722203b413aec570544252f809`），锁定单独的 CPU 驱动并完成两池 80/80 组匹配比例对照。
- 结果分析首次输出时，事后最佳固定策略均值打平的代码用了名称字典序；发现与预先锁定的“菜单顺序打平”不一致后，只修正分析脚本并重算结果。未重跑或改写任何 campaign。最终完整结果在 `e_menu_results.json`。
- 运行后发现预检未单独执行合成标签置换的数值响应性检查。原预检保留原样，另做仅用合成标签的晚期验证并写 `DEVIATION_POSTRUN_BOUNDARY_CHECK.md`；不冒称运行前已完成。
- 最终 `verify_final.py` 首次运行时，D 的测试因相对导入需从其目录启动而未加载。只修复验证脚本的工作目录，第二次通过 D 的 6 项与 E 的 3 项测试；再核对 760 组运行、160 次 GLM 回执、无 pending/失败、初始化配对、冻结哈希。收据为 `d5_final_verification.json`。
- 12:30:59 UTC：远端 760 个含私有轨迹的 run.json 打包为 `data/curation_private/d5_backups/d5_e_menu_private_20261020.zip`，SHA-256 `2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a`。本机下载到 Git 忽略的 `.sync_audit/d5_20261020/`，逐成员重算 760 个哈希通过。公开汇总与私有逐分子结果分开。

所有摘要为 post-exposure 结果。未改阈值、冻结标签、旧策略或 D3/D4 历史结论；未产出新 campaign-ready 池。

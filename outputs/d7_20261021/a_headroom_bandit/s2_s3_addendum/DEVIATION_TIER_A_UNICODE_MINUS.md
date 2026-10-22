# Tier A 机械修复：D1 表格的 Unicode 负号

记录日期 2026-10-21。首次预锁 UTC `2026-10-21T11:26:13.614307+00:00`。第一次执行在生成任何统计结果前停止：D1 表格采用 U+2212 负号，原正则只识别 ASCII `-`，把 `−0.95` 解析成 `0.95`，与代码中的已知值断言不符。原脚本 `reanalyze.py` 与 `execution_lock.json` 保留。

新增 `reanalyze_v2.py` 只做两项机械变更：解析前把 U+2212 转成 ASCII `-`；另存 `execution_lock_v2.json`，避免覆盖初锁。bootstrap、输入、阈值、公式和预期断言均不改。v2 重新锁定后执行成功。

独立的 `verify_repair.py` 验证两版源码除上述字符串替换外逐字一致；重现错误解析与正确解析；重新核对 D5 存档哈希、760 个成员、TNAP bit 七固定臂均值及全部 20 个 GLM H@50 值。结果保存 `mechanical_repair_regression.json`，UTC `2026-10-21T11:29:45.688403+00:00`。该回归在新统计结果之后单独执行，不声称早于复算。

没有调用 API、没有生成标签、没有新 campaign，没有覆盖历史断言。

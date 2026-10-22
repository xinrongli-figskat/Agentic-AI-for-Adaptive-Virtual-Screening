# D5-C 运行记录

2026-10-20 UTC。范围为方法可行性、原始来源核查和远端只读环境检查。未调用 GLM；未查询 campaign oracle；未读取隐藏标签；未修改冻结文件或旧运行。

1. 阅读 D5 任务卡和用户对两个槽位的修订；核查项目 `structure_prior` 定义和 TNAP pool card。`AGENTS.md` 已检查，无本子任务附加规则。
2. 查阅方法作者的 [Protenix-Dock 代码/README](https://github.com/bytedance/Protenix-Dock)、[PSICHIC 代码/README](https://github.com/huankoh/PSICHIC)、[PSICHIC 数据说明](https://github.com/huankoh/PSICHIC/tree/main/dataset)及 [PSICHIC 权重配置](https://github.com/huankoh/PSICHIC/blob/main/trained_weights/multitask_PSICHIC/config.json)。查 [5Y86](https://www.rcsb.org/structure/5Y86)、[7YIV](https://www.rcsb.org/structure/7YIV)、[9SH5](https://www.rcsb.org/structure/9SH5) 的靶点和结构信息。
3. 只读 SSH 检查 `lab-4090`：`nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader` 返回 `NVIDIA GeForce RTX 4090, 24564 MiB, 580.178.04`；用远端项目 `.venv/bin/python` 的 `importlib.util.find_spec` 检查 `rdkit=True, pxdock=False, torch=False, Bio=False`。未执行 `pip install` 或模型下载。
4. 尝试以 `git ls-remote` 固定上游 commit，网络请求未成功；已终止，未记为版本证据。正式进入实验前必须另行固定 commit 与 checkpoint 哈希。
5. 三化合物 smoke：**未运行**。原因是方法依赖/权重尚未安装，且受体预处理与训练污染核验未完成；不把未经审计的打分写进 campaign。耗时与显存：**未测量**。

输出仅为本目录的可行性报告、日志、状态与哈希清单。

2026-10-20 状态格式修正：按 D5 回报格式将 STATUS 改为单行 done。done 仅表示本可行性评估与交付完成；两个方法仍建议暂缓，三化合物 smoke 未运行，见报告。

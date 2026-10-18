# 远程项目保存核对与补传记录

核对日期：2026-10-14。证据为用户在已登录的远程 Ubuntu 终端执行文件清单检查后贴出的输出。未读取私钥、密码或 API 密钥。此次 Codex 自动 SSH 连接没有通过公钥认证，因此不能声称已经自动完成上传。

## 已确认远程存在

项目根目录为 `/driveA/xinrong/agentic-screening`。

- `requirements.lock.txt`：存在；内容尚未读取，不能据文件名断定依赖清单完整。
- `inspect_chembl_sample.py`：存在，用户此前已成功运行。
- `data/exploration/chembl_sample_20261013T154424Z_bf4ac0ff/summary.json`。
- 同一运行目录的 `raw_status.json`。
- 同一运行目录的 `raw_activities.json`。
- 同一运行目录的 `activity_preview.csv`。
- 同一运行目录的 `run_metadata.json`。

该检查排除了虚拟环境、缓存与 Python 字节码目录；这些环境内容已由此前的安装和运行输出确认，不在本次待补传列表中。

## 待补传内容

说明文档和离线测试不在用户提供的远程文件清单中。补传包使用以下布局，保留现有根目录脚本及样本文件：

```text
/driveA/xinrong/agentic-screening/
  docs/
    01_original_brief_from_chat.md
    02_project_requirements_and_current_status.md
    03_first_data_check.md
    04_chembl_sample_explained.md
    05_remote_sync_inventory.md
  tests/
    test_inspect_chembl_sample.py
```

01 是用户最初 brief 的对话归档，不是后来找到的独立原始附件；02 是要求与实施建议；03 是读取说明与首次结果审查；04 整理了之前仅存在于聊天中的详细解释；05 是本次核对记录。

测试已兼容读取远程项目根目录的现有脚本，使用模拟数据，不查询真实 ChEMBL，不安装依赖。临时测试文件放在项目 `.cache/inspection-tests/`。测试通过不能代替实际样本的科学审查。

2026-10-14 本地验证：现有目录布局下六项检查通过；另在临时目录模拟“项目根目录的读取脚本 + tests/ 下的测试脚本”，六项检查也通过。这是本地的目录兼容性验证，尚未在远程电脑上执行这些测试。

## 上传后核对

在远程项目目录中运行：

```bash
find docs tests -maxdepth 1 -type f -print
python tests/test_inspect_chembl_sample.py
```

应看到五份 Markdown 文档和一个测试脚本；测试成功时报告六项检查通过。以上是待执行的验收步骤，不是已完成的远程结果。收到上传与检查输出后再更新同步状态。

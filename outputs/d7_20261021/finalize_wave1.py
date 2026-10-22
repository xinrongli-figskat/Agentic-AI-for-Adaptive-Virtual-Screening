"""Write an honest partial D7 closeout; never authorize later waves."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    return json.loads((BASE/name).read_text(encoding='utf-8-sig'))

def write(name, content):
    p = BASE/name
    p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists(), str(p)
    p.write_text(content,encoding='utf-8')

def dump(name, obj):
    write(name,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def main():
    utc = datetime.now(timezone.utc).isoformat()
    mv = read('wave1_manifest_verification.json')
    reg = read('root_regression_and_frozen_checks.json')
    d = read('d_identity_gate_v2/credential_summary_final_partial.json')
    assert all(x['all_members_match'] for x in mv['manifest_checks'])
    assert not mv['public_forbidden_field_findings']
    assert reg['all_hashes_match'] and reg['fixed_means_exact'] and reg['glm_array_exact']
    pre = sorted(BASE.glob('preflight_*.json'))
    assert len(pre)>=2 and all(json.loads(p.read_text())['passed'] for p in pre)
    verification = dict(utc=utc,post_exposure=True,status='TIER_B_WAVE1_NOT_PASSED',
        all_three_member_manifests_verified=True, member_count=sum(x['member_count'] for x in mv['manifest_checks']),
        root_independent_known_good_regression_passed=True,
        locked_preconditions_pass_before_and_after=True, frozen_data_code_and_snapshot_hash_checks=len(reg['frozen_data_and_code_checks']),
        public_json_forbidden_field_findings=[],
        write_scope_review='Agent manifests contain only own-directory paths; delivery logs reviewed. No cross-directory write observed; not an OS-level write audit.',
        bandit_determinism='NOT_RUN_SPEC_CONFLICT', bandit_information_field_equality=False,
        credential_three_fractions_sum_pass_rows=d['ratio_sum_pass_rows'], credential_required_rows=62,
        multi_molregno_count=d['multi_molregno_total'], all_multi_de_minimis_pass=d['all_multi_fractions_de_minimis'],
        second_wave_authorized=False, new_glm_calls=0,new_campaigns=0,
        blockers=['D5 eleven-field interface differs from required legacy fourteen-field interface',
                  'Three source-support fractions do not cover 2526 identities',
                  'Source-tier scope unspecified and src_id 37 missing from fixed tier map'])
    dump('d7_wave1_verification.json',verification)
    for folder in ('b_model_variance','c_surrogate_factor'):
        write(folder+'/STATUS','NOT_STARTED_WAVE1_GATE_BLOCKED\n')
        write(folder+'/RUN_LOG.md',f'# D7 deferred work\n\nWritten UTC: {utc}. Post-exposure.\n\nNo experiment or GLM call started. The task card forbids wave 2 before all wave 1 gates pass. See ../d7_wave1_verification.json.\n')
        dump(folder+'/MANIFEST.json',dict(utc=utc,status='NOT_STARTED',files=[dict(path=p.name,sha256=sha(p)) for p in sorted((BASE/folder).iterdir()) if p.is_file()]))
    write('STATUS','PARTIAL_TIER_B_SPECIFICATION_DECISION_REQUIRED\n')
    write('RUN_LOG.md',f'''# D7 主代理执行记录

本记录实际写入 UTC：{utc}。性质：post-exposure。

- 任务卡原件保存并锁 SHA-256：99944546647d5602a4a80c09b389e91526295d7a3b4e4119248c7728704d2e89。
- 运行前、收口后两次核验 11 项前提，均通过；具体时间以 preflight 回执为准。
- 按任务卡授权并行执行 A、D、E，分别限制写入自身目录。A1 完成；D 部分测量完成；E 完成。
- A2/A3 因实际 D5 接口与旧接口矛盾按 Tier B 停止。D 因分类与来源定义缺口按 Tier B 停止。未自行应用修订。
- 主代理逐成员重算 3 份 manifest，共 45 个成员通过。独立从 D5 ZIP 重算两项已知良好回归，精确通过；另验证 25 项归档、冻结数据、旧代码及快照哈希。
- 第一波科学验收不通过，B/C 均未开始；D 后续门槛应用与 GLM 审查未开始。保存提案 DECISIONS_REQUIRED.md，等待用户的规格决定。
- 本轮新 campaign 0，GLM 0，GPU 0。CPU 用于只读计数、归档复核与 bootstrap。无新 campaign-ready 池。
- 历史报告、旧规则、冻结池和冻结标签保留；未提交或推送 Git。
''')
    write('d7_report.md',f'''# D7 第一波执行报告：部分完成，规格问题待决定

写入 UTC：{utc}。全部分析为 post-exposure。本报告不是整张 D7 已完成的声明。

## 完成情况

| 任务 | 状态 | 已交付内容 |
|---|---|---|
| A1 策略余量 | 完成 | D5 两池、两表示再分析；零新增 campaign |
| A2 bandit / A3 粒度扫描 | Tier B 停止 | 已捕获真实接口冲突，未运行 bandit |
| D1 单位规则 / D2 来源测量 | 规则锁定，测量部分完成 | 62 行、25,813 支持身份；三分法与来源映射缺口已定位 |
| D3 资格候选标准登记 | 完成 | 明确冻结前与冻结后可用时点 |
| E 记录修订 | 完成 | 正确基线重算、历史回执与时间戳附录 |
| B 模型方差 / C 代理模型因子 | 未开始 | 第一波验收未通过，任务卡禁止进入第二波 |
| D 门槛应用与新候选 GLM 审查 | 未开始 | 不能用不完整的测量表判定资格 |

## 已得到的科学结果

“策略余量”在这里是不同固定策略的结果差距，不是智能体的已实现收益。

| 池 / 表示 | 非随机臂均值极差 | 每个种子先算极差、再平均 | 该均值的 95% bootstrap 区间 |
|---|---:|---:|---|
| TNAP bit | 7.35 | 10.55 | [6.75,14.60] |
| TNAP count | 6.15 | 11.05 | [7.15,15.15] |
| DYRK3 bit | 2.85 | 5.55 | [4.55,6.55] |
| DYRK3 count | 2.10 | 4.50 | [3.60,5.45125] |

Bootstrap 10,000 次，种子 20261018。与 D5 的 20261020 区分记录，不覆盖 D5 区间。七臂中排除 uniform 后为六个非平凡臂，依任务卡明确枚举。

TNAP bit 的七臂极差为 19.80，count 为 18.95；DYRK3 bit/count 为 5.80/6.05。TNAP 同初始化 oracle 上界均值 41.05，距最优固定臂还有 15.25（bit）/16.10（count）；DYRK3 上界 44.65，差 14.05/13.80。这是知道剩余答案时的理论上界，不能当作可实现的性能承诺。

TNAP 随机实测均值 6.00、解析期望 5.7359；DYRK3 随机实测 24.80、期望 25.1082，两表示各自相同。这里使用 D5 的 20 种子，不是早期 DYRK3 v1 的 5 种子。

TNAP 的固定策略差距更大，值得进一步测 bandit。但逐种子事后挑最好/最差包含选择效应，不能据此推断一个事前可用的自适应控制器能获得这些差距。

## 为什么不能继续运行

第一，卡中要求 bandit 与 D5 GLM 信息完全相同，又要求字段集合等于旧 llm_controller.py。合成状态捕获显示前者 11 字段、后者 14 字段。不能用“字段差不多”代替验收。

第二，来源三分法漏掉 2,526 个“只有同来源替代完整键”的身份，62 行只有 8 行比例和为 1。五个多 molregno 身份全部低于 1%，已正确通过本次新规则；新的缺口与这五个无关。

第三，43 个 assay 的支持活动来源是 BindingDB 专利 src_id=37，原来源分支未覆盖。来源层级到底取本 assay 活动出处，还是全库化合物出处，也需要明确。两种读法分别保存，没有强加二者相等的新条件。

具体可选修订见 DECISIONS_REQUIRED.md。全部尚未批准、尚未执行。任务卡 Tier B 要求只提方案；第一波验收条款要求“未通过不得进入第二波”。这是本次停止依据。

## D6 记录更正

正确 D5 七菜单基线对 D6 重放：初始化相同 10/10；首轮保存的 11 字段摘要与 information_available 相同 10/10；首轮策略相同 4/10；完整四轮序列相同 1/10（seed 5）。原来的“十条序列全部不同”引用了 D4 三菜单数据，应为九条不同。不可复现的停止结论仍成立，但原引用证据有误。

这里只核实保存状态及其 canonical JSON，不把它夸大成已独立保存并核验原始 HTTP 请求字节。时间戳修订使用文件写入时间，并明确实际修复事件时间未知；未倒填。原 D6 报告未改写。

## 六项报告义务中尚不能回答的部分

1. 所有已完成再分析、凭据测量与拟议修订都是 post-exposure。
2. 未执行 C，无法报告策略余量随代理强度变化，更不能声称强代理压缩了余量。
3. 未执行 bandit，无法比较其与 GLM/最优固定臂。卡中“四次决策、七臂、先验主导”的解释保留为待检验设计限制。
4. 未执行粒度扫描，不能断言四个决策点压制自适应。
5. 未完成 B，不能给出并入模型方差的新置信区间，不作新增 GLM 收益主张。
6. 未产生任何新 campaign-ready 池；策略余量仅登记为资格标准候选，不回改冻结池资格。

## 核验、成本与保存

三份子任务 manifest 的 45 个成员在本机独立复算通过；主代理另从锁定 ZIP 重算固定臂均值及 GLM 逐种子向量，精确通过。11 项前提运行前后均通过；冻结池与标签文件、10 个旧源码及对应快照均通过。公开 JSON 禁止字段检查未发现 outcome/label/is_hit。检查路径与执行日志未见跨目录写入；这不是操作系统级写入审计。

新增 GLM 调用 0/1000，新增 GLM token 0，新增 campaign 0；没有到达 600 调用检查点。GPU 未使用，符合本轮 CPU 优先要求。R3 逐身份细节留在 Git 忽略的 identity_private 目录。根目录 MANIFEST 记录所有交付文件哈希；本机与远端保存位置对应 outputs/d7_20261021。
''')
    files = [dict(path=p.relative_to(BASE).as_posix(),sha256=sha(p)) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='MANIFEST.json']
    for p in sorted(BASE.glob('*/MANIFEST.json')):
        files.append(dict(path=p.relative_to(BASE).as_posix(),sha256=sha(p)))
    dump('MANIFEST.json',dict(utc=utc,status='PARTIAL_TIER_B',post_exposure=True,files=files))
    print(json.dumps(dict(status='PARTIAL_TIER_B',members=len(files),manifest_sha256=sha(BASE/'MANIFEST.json'))))

if __name__=='__main__':
    main()

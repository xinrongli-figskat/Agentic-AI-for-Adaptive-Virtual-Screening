"""Reconstruct a cited post-exposure criteria table without modifying source files."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cite(path: str, needle: str) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    matches = [i for i, line in enumerate(lines, 1) if needle in line]
    if not matches:
        raise AssertionError(f"Missing citation: {path} {needle}")
    return f"{path}:{matches[0]}"


def write_csv(path: Path, rows: list[dict], header: list[str], comment: str | None = None) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        if comment:
            handle.write(f"# {comment}\n")
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def seal(folder: Path, inputs: list[Path], start: str, details: str) -> None:
    (folder / "STATUS").write_text("done\n", encoding="utf-8")
    end = datetime.now(timezone.utc).isoformat()
    (folder / "RUN_LOG.md").write_text(
        "post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。\n\n"
        f"Start UTC: {start}\nEnd UTC: {end}\nCommand: python -B outputs/r1_criteria_reconstruction_20261018/build_r1.py\n"
        f"Python: {platform.python_version()}\nNumPy/SciPy/RDKit: not used (source citation and saved metrics only)\n"
        "Random seed: none\nGLM calls: 0\n"
        f"Code SHA-256: {digest(Path(__file__))}\n{details}\n\nInputs:\n"
        + "\n".join(f"- {p.relative_to(ROOT)} SHA-256 {digest(p)}" for p in inputs)
        + "\n", encoding="utf-8")
    files = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            files.append({"path": p.relative_to(folder).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)})
    (folder / "MANIFEST.json").write_text(json.dumps({"note": "Self-excluding manifest", "files": files}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    start = datetime.now(timezone.utc).isoformat()
    sources = [
        "outputs/candidate_discovery_v0/criteria_v0.json",
        "outputs/assay_audit_v0/audit_policy_v0.json",
        "outputs/curation_agent_v1/protocol.json",
        "outputs/curation_agent_v2/protocol.json",
        "outputs/curation_agent_v2/CRITERIA_REVIEW.md",
        "outputs/curation_agent_v3/protocol.json",
        "outputs/31_task1_v2_implementation_and_criteria.md",
        "outputs/monthly_prototype_guidance_v0_2_20261017.md",
        "outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv",
        "outputs/b3_pending_assay_private_20261017/qualification_addendum.json",
        "outputs/p5_init_gate_private_20261018/init_gate_definition.md",
        "outputs/p5_init_gate_private_20261018/init_gate_provenance.md",
        "outputs/p1_negcoverage_private_20261018/p1_aggregate_totals.json",
        "outputs/a2_llm_input_audit_private_20261017/llm_input_audit.md",
        "outputs/a3_dyrk3_supplement_private_20261017/group_H50.csv",
        "outputs/brief_gap_audit_private_20261018/dyrk3_ceiling.json",
        "config/task_params_20261018.json",
    ]
    for p in sources:
        if not (ROOT / p).is_file():
            raise FileNotFoundError(p)
    inputs = [ROOT / p for p in sources]
    with (ROOT / "outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv").open(encoding="utf-8", newline="") as handle:
        dyrk = next(r for r in csv.DictReader(handle) if r["assay_id"] == "CHEMBL5363961")
    assert (int(dyrk["N"]), int(dyrk["K"]), int(dyrk["measured_nonhit_support"])) == (231, 116, 115)
    assert (int(dyrk["largest_cluster_count"]), int(dyrk["scaffold_bucket_count_including_acyclic"])) == (72, 101)
    c0 = "outputs/candidate_discovery_v0/criteria_v0.json"
    a0 = "outputs/assay_audit_v0/audit_policy_v0.json"
    v1 = "outputs/curation_agent_v1/protocol.json"
    v2 = "outputs/curation_agent_v2/protocol.json"
    cr = "outputs/curation_agent_v2/CRITERIA_REVIEW.md"
    p5 = "outputs/p5_init_gate_private_20261018/init_gate_definition.md"
    p5prov = "outputs/p5_init_gate_private_20261018/init_gate_provenance.md"
    b2 = "outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv"
    rows = []

    def add(cid, name, value, direction, kind, first, changed, refs, rationale, dyvalue, status, notes=""):
        rows.append(dict(criterion_id=cid, criterion=name, value=value, direction=direction,
                         kind=kind, first_seen_version=first, changed_in_versions=changed,
                         **{"source_file:line": "; ".join(cite(*ref) for ref in refs)},
                         rationale_recorded=rationale, dyrk3_value=dyvalue, dyrk3_status=status, notes=notes))

    add("endpoint", "IC50, assay-defined inhibition", "IC50", "equals", "pipeline_rule", "candidate_scope_v0.1", "none",
        [(c0, '"standard_type"'), (cr, "单一 assay")], "未记录", "IC50", "pass", "不证明直接结合")
    add("threshold", "Hit threshold", "1000 nM", "IC50 ≤", "operational", "candidate_scope_v0.1", "none",
        [(c0, '"hit_threshold_nM"'), (cr, "IC50 ≤1000")], "未记录", "1000 nM", "pass")
    add("pool_min", "Usable standardized compounds", "≥250", "≥", "operational", "task1_agent_v1.0 (500)", "v2: 500→250",
        [(v1, '"minimum_usable_compounds"'), (v2, '"minimum_usable_compounds"'), (cr, "250–499")],
        "50 次查询不超过池的 20%", "231", "exception", "500 在 v2 起为优先审查规模")
    add("pool_preferred", "Preferred usable compounds", "≥500", "≥", "operational", "task1_agent_v1.0 (minimum)", "v2: preferred",
        [(v1, '"minimum_usable_compounds"'), (v2, '"preferred_usable_compounds"'), (cr, "优先审查候选")],
        "50 次查询占池 ≤10%", "231", "below_preferred_not_hard_failure")
    add("hits", "Measured hit support", "≥30", "≥", "operational", "candidate_scope_v0.1", "none",
        [(c0, '"hit_support_molecule_ids"'), (cr, "至少 30 个命中")], "两类覆盖；独立统计功效论证未记录", "116", "pass")
    add("nonhits", "Measured nonhit support", "≥100", "≥", "operational", "candidate_scope_v0.1", "none",
        [(c0, '"nonhit_support_molecule_ids"'), (cr, "100 个非命中")], "两类覆盖；独立统计功效论证未记录", "115", "pass")
    add("target_mapping", "Single protein, mapping confidence", "SINGLE PROTEIN; confidence ≥9", "≥", "operational", "task1_agent_v1.0", "none",
        [(v1, '"scope"'), (v1, '"minimum_confidence_score"'), (cr, "单一 assay、SINGLE PROTEIN")], "未记录", "single protein; confidence 9", "pass")
    add("assay_type", "ChEMBL assay type", "B", "equals", "operational", "candidate_scope_v0.1", "none",
        [(c0, '"assay_type_for_record_signals"'), (cr, "ChEMBL B 类型")], "未记录", "B", "pass")
    add("full_scope", "Complete single-assay IC50 fetch", "complete", "equals", "pipeline_rule", "task1_agent_v1.0", "none",
        [(v1, '"scope"'), (cr, "完整获取该 assay")], "未记录", "complete", "pass")
    add("cluster", "Largest Butina cluster", "≤0.25", "≤", "operational", "task1_agent_v1.0", "none",
        [(v1, '"maximum_largest_cluster_fraction"'), (a0, '"fingerprint"'), (a0, '"radius"'), (a0, '"bits"'), (a0, '"include_chirality"'), (a0, '"butina_tanimoto_similarity_threshold"'), (b2, "CHEMBL5363961")],
        "更广化学覆盖；不证明泛化", "72/231=0.3116883117", "exception", "Morgan r2, 2048-bit, chirality; Tanimoto ≥0.7 (Butina distance ≤0.3)")
    add("scaffolds", "Murcko scaffold buckets including acyclic", "≥10", "≥", "operational", "task1_agent_v1.0", "none",
        [(v1, '"minimum_scaffold_buckets"'), (cr, "非环分子共用一个桶"), (b2, "CHEMBL5363961")],
        "更广化学覆盖；不证明泛化", "101", "pass")
    add("query_fraction", "Query budget / pool", "50/N ≤0.20", "≤", "operational", "task1_agent_v1.0 (500→10%)", "v2: ≤20%",
        [(v1, '"query_budget"'), (v2, '"maximum_query_fraction"'), (cr, "50/池大小 ≤20%")],
        "给顺序搜索留未查询空间", "50/231=0.2164502165", "exception")
    add("init_single_class", "Uniform initialization all one class", "P(no hit)+P(all hit) ≤0.5; n_init=10", "≤", "operational", "task1_agent_v1.0", "none",
        [(v1, '"maximum_initial_single_class_probability"'), (p5, "公式"), (cr, "仅获得单一类别的概率"), (p5prov, "来源未记录"), (b2, "CHEMBL5363961")],
        "来源未记录", "0.0015953978844140675", "pass", "双侧；渐近命中率窗口约 6.7%–93.3%；含等号")
    add("quality", "Unknown/conflict/censor/duplicate quarantine", "preserve unknown; do not assign nonhit", "required", "pipeline_rule", "candidate_scope_v0.1", "audit_v0+v2 clarified",
        [(c0, '"exclude_flagged_potential_duplicates_from_signals"'), (a0, '"cross_threshold_disagreement"'), (a0, '"bounds"'), (cr, "不能补成阴性")],
        "未记录", "1 excluded unknown in v1", "pass", "重复、冲突、删失、potential_duplicate 均需逐条保留来源")
    header = ["criterion_id", "criterion", "value", "direction", "kind", "first_seen_version", "changed_in_versions", "source_file:line", "rationale_recorded", "dyrk3_value", "dyrk3_status", "notes"]
    write_csv(OUT / "qualification_criteria_table_reconstructed.csv", rows, header,
              "重建文件，不是 A1 原件；依据以上源文件。post-exposure，不是新 benchmark、盲验证或新 campaign。")
    (OUT / "dyrk3_vs_criteria_reconstructed.md").write_text(
        "post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。\n\n"
        "# DYRK3 v1 对现行 v2+ 门槛（重建）\n\n"
        f"B2 已保存的独立指标 {cite(b2, 'CHEMBL5363961')} 与原审查设置 {cite(a0, '"radius"')}、{cite(a0, '"bits"')}、{cite(a0, '"include_chirality"')}、{cite(a0, '"butina_tanimoto_similarity_threshold"')} 一致：Morgan r2、2048 bit、手性、Tanimoto 0.7 / Butina 距离 0.3。"
        "此处复核 B2 的同设置再计算结果，而非本次从 SMILES 新运行聚类。最大簇 72/231=31.17%；Murcko 桶 101。先前报告的约 31% 与之吻合。\n\n"
        "三项例外：231<250；72/231=31.17%>25%；50/231=21.65%>20%。"
        "其余计数：116 hit≥30、115 measured nonhit≥100、单类别初始化概率 0.0015954≤0.5、骨架桶101≥10。"
        "原 v1 冻结原型不因 v2+ 门槛而撤销；它不是通用 benchmark。\n", encoding="utf-8")
    (OUT / "criteria_change_log.md").write_text(
        "post-exposure 的证据整理，不是新 benchmark、盲验证或新 campaign。\n\n"
        "# 标准演变（仅据可见文件）\n\n"
        f"- candidate_scope_v0.1：1000 nM IC50、B 型、单蛋白、潜在重复剔除信号；500 来源分子 ID、30/100 支持 ID 为预筛优先条件。见 {cite(c0, '"review_priority_gates"')}。\n"
        f"- audit_v0：引入结构与删失/冲突核查及 Morgan/Butina 设置；尚未自动判资格。见 {cite(a0, '"qualification"')}。\n"
        f"- task1_agent_v1：整理后最低 500、30/100、置信度9、簇≤25%、骨架桶≥10、双侧初始化概率≤0.5、50次查询。见 {cite(v1, '"minimum_usable_compounds"')}–{cite(v1, '"initialization_queries"')}。双侧门槛的 0.5 数值来源未记录。\n"
        f"- task1_agent_v2：最低改为250，500改为优先层，增加 50/N≤20%；理由仅记录为控制查询占比并扩大有限可行性审查。见 {cite(cr, '为什么调整 500')}、{cite(cr, '250–499')}。其余保留。\n"
        "- task1_agent_v3：在现有 protocol 中未见这些资格数值进一步改变；接口/工具反馈修订不算科学门槛变更。\n", encoding="utf-8")
    old = (ROOT / "outputs/monthly_prototype_guidance_v0_2_20261017.md").read_text(encoding="utf-8")
    old = old.replace('# 本月原型推进记录 v0.2', '# 本月原型推进记录 v0.3（由 v0.2 复制并更正）', 1)
    old = old.replace('日期：2026-10-17。', '日期：2026-10-18。', 1)
    old = old.replace('文件哈希及 UTC 保存时间另见同目录的 `monthly_prototype_guidance_v0_2_20261017.receipt.json`。',
                      '本版文件哈希与 UTC 生成时间见本目录 `MANIFEST.json` 和 `RUN_LOG.md`；v0.2 原件保留。', 1)
    old = old.replace('81/81 完成 RDKit 整理，62 个通过当前数值/结构检查、18 个未过、1 个多样性精确计算待补。',
                      '81/81 完成 RDKit 整理；B3 补算后 62 个通过、19 个未过、0 个待补。', 1)
    old = old.replace('## 后续顺序与尚未决定的参数',
                      '## v0.2 当时的后续顺序与尚未决定的参数（历史草案，现以 v0.3 补记为准）', 1)
    appendix = "\n\n## v0.3 补记：已核实 A2–A3、B1–B3、P1、P5（post-exposure）\n\n"
    refs = {
        "A2": "outputs/a2_llm_input_audit_private_20261017/llm_input_audit.md",
        "A3": "outputs/a3_dyrk3_supplement_private_20261017/group_H50.csv",
        "B1": "outputs/p1_negcoverage_private_20261018/p1_input_check.json",
        "B2": "outputs/b2_candidate_metrics_private_20261017/candidate_metrics.csv",
        "B3": "outputs/b3_pending_assay_private_20261017/qualification_addendum.json",
        "P1": "outputs/p1_negcoverage_private_20261018/p1_aggregate_totals.json",
        "P5": "outputs/p5_init_gate_private_20261018/init_gate_definition.md",
    }
    for label, rel in refs.items():
        p = ROOT / rel
        appendix += f"- {label}{'（通过 P1 输入复核）' if label=='B1' else ''}: {rel}；SHA-256 {digest(p) if p.is_file() else '本机未找到，待核验'}。\n"
    appendix += ("\nA2：GLM 仅见聚合状态与已揭示结果，未见候选结构/隐藏标签。A3：bit 的 5 种子固定贪心 H@50 均值 29.8；"
                 "保留实际初始化后的算术上限均值 44.4（见 `outputs/brief_gap_audit_private_20261018/dyrk3_ceiling.json`）。"
                 "不得写‘贪心已近上限’。B1：81 个预筛；B2：62 个数值通过；B3：1,765 池的初始化风险未过。"
                 "P1：226 个非命中不足分支经整理为 A66/B94/C66；P5：门槛是双侧单类别概率≤0.5，数值 0.5 的来源未记录。"
                 "这些均不构成来源审查通过。\n")
    (OUT / "monthly_prototype_guidance_v0_3_20261018.md").write_text(old + appendix, encoding="utf-8")
    seal(OUT, inputs, start, "DYRK3 cluster figure verified from B2 saved recomputation under same policy; no new RDKit run in this step.")
    print(json.dumps({"status": "done", "rows": len(rows), "manifest_sha256": digest(OUT / "MANIFEST.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

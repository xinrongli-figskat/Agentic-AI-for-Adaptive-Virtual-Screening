import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
AUDIT = OUT / "s_restructure_20261018"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def index_category(path):
    name = path.name
    if name == "01_original_brief_from_chat.md":
        return "Brief（兼容路径）", "被现有 brief 复核脚本按旧路径读取，暂留顶层"
    if name.startswith("task1_v5_"):
        return "协议（兼容路径）", "被进度快照脚本按旧路径读取，暂留顶层"
    if name.startswith("monthly_prototype_guidance_v0_2_20261017"):
        return "草案（兼容路径）", "被现有复核和标准重建脚本按旧路径读取，暂留顶层"
    if name in {"README.md", "INDEX.md"}:
        return "导航", "outputs 目录导航"
    if name in {"brief", "protocols", "scripts", "src", "tests", "env", "private", "devlog", "_archive"}:
        notes = {
            "brief": "原始 brief 与进度对照",
            "protocols": "冻结协议和草案分层存放",
            "scripts": "一次性脚本按用途归类",
            "src": "代码包说明；可复用包仍在 outputs 顶层",
            "tests": "测试整理说明；测试本体暂留原位",
            "env": "本地环境配置；敏感文件被 Git 忽略",
            "private": "本机私有逐化合物数据；数据文件不进入 Git",
            "devlog": "历史开发记录",
            "_archive": "历史传输包和被取代文件",
        }
        return "分层目录", notes[name]
    if path.is_dir() and name in {"freeze_v1", "dyrk3_prefreeze_v0", "campaign_v0", "oracle_boundary_v0", "curation_agent_v1", "curation_agent_v2", "curation_agent_v2_1", "curation_agent_v3", "curation_agent_v4", "assay_audit_v0", "candidate_discovery_v0", "assay_edge_inspection_v0", "reporting_v1", "source_alignment_v1"}:
        return "代码包", "保留顶层以维持现有模块入口"
    if path.is_dir() and "private" in name.lower():
        return "本机私有数据/分析", "未纳入 Git；文件级状态见 S6 审计"
    if path.is_dir() and name in {"results", "candidate_discovery_runs", "candidate_assay_reviews", "first_sample_row_review", "source_alignment_20261015", "task1_v1_review_20261015", "task1_v2_delivery", "task1_v2_validation", "source_review_20261014T101612Z_a227b5e7"}:
        return "历史数据/证据", "本机保留；标签数据由 Git 忽略"
    if path.is_dir() and name.startswith("s_restructure_"):
        return "整理审计", "本次 S1–S7 清单、报告和核验脚本"
    if path.is_dir() and name.startswith("task1") or path.is_dir() and name.startswith(("r", "p", "b", "a")):
        return "研究产物", "状态和用途见目录内说明；检查 Git 忽略规则"
    if path.is_dir():
        return "研究产物", "目录内的运行状态和文件说明其用途"
    if name.startswith("test_") and path.suffix.lower() == ".py":
        return "测试", "测试仍在原位置以维持导入路径"
    if path.suffix.lower() in {".py", ".sh", ".ps1", ".sql"}:
        return "单次脚本", "未移动脚本；原因见 deferred_moves.md 或 S5 分类表"
    if path.suffix.lower() == ".zip" or "transfer" in name.lower():
        return "历史归档", "历史传输包或校验文件"
    if name.endswith(".ssh_config"):
        return "本地环境配置", "由 Git 忽略"
    return "文件", "具体用途见文件内容"


def main():
    # README is an orientation document, not a protocol or data file.
    (OUT / "README.md").write_text(
        "# 项目输出目录\n\n"
        "这里保存项目 brief、方案、代码、测试和分析产物。目录整理只移动文件；既有数据、标签、阈值和结论未被改写。\n\n"
        "- 原始 brief 仍在顶层，因为现有复核脚本按这个路径读取；`brief/` 保存项目进度对照和给导师的材料。\n"
        "- `protocols/frozen/` 与 `protocols/drafts/`：存放可安全移动的协议文件。Task 1 v5 和 monthly guidance 仍在顶层，直到引用它们的脚本完成路径迁移。\n"
        "- `scripts/`：可安全移动的一次性脚本按发现、整理、来源审查、验证和运维分类。路径敏感或仍被引用的脚本暂留原位，见 `deferred_moves.md`。\n"
        "- 可复用 Python 包和测试继续留在 `outputs/` 顶层，保持现有导入方式。`src/README.md`、`tests/README.md` 说明后续整理条件。\n"
        "- `private/` 保存本机逐化合物记录；其中数据文件被 Git 忽略。其他旧结果和历史数据也按 `.gitignore` 排除。公开控制器和报告不得直接读取私有标签。\n"
        "- `_archive/` 放历史传输包，`devlog/` 放编号过程记录。\n"
        "- `INDEX.md` 列出当前顶层条目；`PATH_MIGRATION_20261018.csv` 记录移动前后位置和哈希。\n"
        "- `s_restructure_20261018/` 保存本次整理的盘点、隐私审计、偏离记录和最终核验。\n\n"
        "远端工作站和项目根目录的 `.sync_audit/` 不属于本次整理范围。\n",
        encoding="utf-8",
    )

    top = sorted(OUT.iterdir(), key=lambda p: p.name.casefold())
    lines = [
        "# INDEX：当前 outputs 顶层文件与目录",
        "",
        "本表依据当前目录自动生成，逐项列出顶层内容。历史路径与文件哈希见 `PATH_MIGRATION_20261018.csv`；本次整理的审计材料见 `s_restructure_20261018/`。",
        "",
        "私有逐化合物标签不会提交到 Git。可复用代码包和测试保留在顶层，避免改变现有模块导入路径。",
        "",
        "|条目|当前路径|类别|说明|",
        "|---|---|---|---|",
    ]
    for path in top:
        category, note = index_category(path)
        rel = path.relative_to(ROOT).as_posix()
        note = note.replace("|", "/").replace("\n", " ")
        lines.append(f"|`{path.name}`|`{rel}`|{category}|{note}|")
    (OUT / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    current = sorted((p for p in OUT.rglob("*") if p.is_file() and AUDIT not in p.parents), key=lambda p: p.relative_to(OUT).as_posix())
    after_rows = [{"relative_path": p.relative_to(OUT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha(p)} for p in current]
    write_csv(AUDIT / "inventory_after.csv", ["relative_path", "size_bytes", "sha256"], after_rows)
    after = {r["relative_path"]: r["sha256"] for r in after_rows}

    with (AUDIT / "inventory_before.csv").open(encoding="utf-8-sig", newline="") as f:
        before_rows = list(csv.DictReader(f))
    with (OUT / "PATH_MIGRATION_20261018.csv").open(encoding="utf-8-sig", newline="") as f:
        public_map_rows = list(csv.DictReader(f))
    private_map_path = OUT / "private" / "r4_source_review_private_20261018" / "S6_PATH_MIGRATION.csv"
    with private_map_path.open(encoding="utf-8", newline="") as f:
        private_map_rows = list(csv.DictReader(f))
    map_rows = public_map_rows + private_map_rows
    mappings = {r["old_relative_path"]: r["new_relative_path"] for r in map_rows}
    missing = []
    unchanged = 0
    moved = 0
    for row in before_rows:
        old, expected = row["relative_path"], row["sha256"]
        if after.get(old) == expected:
            unchanged += 1
            continue
        new = mappings.get(old)
        if new and after.get(new) == expected:
            moved += 1
            continue
        missing.append(old)
    cache_missing = [p for p in missing if "__pycache__/" in p or "/__pycache__/" in p]
    unexplained = [p for p in missing if p not in cache_missing]
    mapping_failures = []
    for row in map_rows:
        new = row["new_relative_path"]
        if after.get(new) != row["sha256"]:
            mapping_failures.append(new)
    new_files = [p for p in after if p not in {r["relative_path"] for r in before_rows} and p not in set(mappings.values())]
    reconciliation = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_files": len(before_rows),
        "current_files_excluding_audit_directory": len(after_rows),
        "original_files_unchanged_at_same_path": unchanged,
        "original_files_moved_and_hash_verified": moved,
        "expected_cache_files_removed": cache_missing,
        "unexplained_missing_original_files": unexplained,
        "migration_rows": len(map_rows),
        "public_migration_rows": len(public_map_rows),
        "private_ignored_migration_rows": len(private_map_rows),
        "migration_targets_hash_verified": len(map_rows) - len(mapping_failures),
        "migration_target_failures": mapping_failures,
        "new_non_migration_files": new_files,
        "all_original_files_accounted_for": not unexplained and unchanged + moved + len(cache_missing) == len(before_rows),
        "all_migration_targets_verified": not mapping_failures,
    }
    (AUDIT / "s7_reconciliation.json").write_text(json.dumps(reconciliation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if unexplained or mapping_failures or not reconciliation["all_original_files_accounted_for"]:
        raise SystemExit(json.dumps(reconciliation, ensure_ascii=False, indent=2))

    hard_rows = []
    needles = ("outputs/", "outputs\\", "C:\\Users", "/driveA", ".sync_audit")
    for p in current:
        if p.suffix.lower() not in {".py", ".sh", ".ps1"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            matches = [n for n in needles if n.lower() in line.lower()]
            if matches:
                hard_rows.append({"file": p.relative_to(OUT).as_posix(), "line": number, "matches": ";".join(matches), "excerpt": line.strip()[:240]})
    write_csv(AUDIT / "hardcoded_paths_after.csv", ["file", "line", "matches", "excerpt"], hard_rows)
    print(json.dumps(reconciliation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

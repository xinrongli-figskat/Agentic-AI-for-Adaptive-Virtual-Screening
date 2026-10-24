"""Read-only publication audit of the Git index or a clean checkout.

The report contains counts and classifications only; matched strings are never saved.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path


PATENTS = (
    "outputs/acc2_patent_us8835472_sample_values.json",
    "outputs/tace_patent_us9926281_sample_values.json",
)
FORBIDDEN_PATENT_KEYS = {
    "compound_key", "standardized_smiles", "smiles", "inchi", "inchikey",
    "molregno", "molecule_chembl_id", "outcome", "is_hit", "label",
}
PATENT_ASSAYS = {"CHEMBL3705476", "CHEMBL5733557"}
TOKEN_PATTERNS = {
    "api_key": re.compile(rb"api_key", re.I),
    "Authorization": re.compile(rb"Authorization", re.I),
    "Bearer": re.compile(rb"Bearer\s", re.I),
    "sk-prefix": re.compile(rb"sk-", re.I),
    "ZHIPU": re.compile(rb"ZHIPU", re.I),
    "GLM_": re.compile(rb"GLM_", re.I),
    "hex_run_ge32": re.compile(rb"(?<![A-Fa-f0-9])[A-Fa-f0-9]{32,}(?![A-Fa-f0-9])"),
    "base64_run_ge32": re.compile(rb"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])"),
}
SECRET_SHAPES = {
    "sk_value": re.compile(rb"sk-[A-Za-z0-9_-]{8,}"),
    "bearer_value": re.compile(rb"(?i:Bearer)\s+[A-Za-z0-9._~+/-]{8,}"),
    "literal_api_key": re.compile(
        rb"(?i:api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9._~+/-]{8,}['\"]"
    ),
}


def git_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    )
    return sorted(p.decode("utf-8") for p in result.stdout.split(b"\0") if p)


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan(root: Path) -> dict:
    paths = git_files(root)
    sizes = {name: (root / name).stat().st_size for name in paths}
    absent = [name for name in paths if not (root / name).is_file()]
    if absent:
        raise RuntimeError(f"Index contains missing worktree files: {len(absent)}")

    pattern_counts = collections.Counter()
    shape_locations = []
    synthetic_credential_literals = collections.Counter()
    known_key_locations = []
    key_file = Path.home() / ".config" / "agentic-screening" / "zhipu_api_key"
    known_key = key_file.read_bytes().strip() if key_file.is_file() else b""
    for name in paths:
        data = (root / name).read_bytes()
        parts = [(name, data)]
        if name.lower().endswith(".zip"):
            with zipfile.ZipFile(root / name) as archive:
                parts.extend((f"{name}!{member.filename}", archive.read(member))
                             for member in archive.infolist() if not member.is_dir())
        for part_name, content in parts:
            for category, pattern in TOKEN_PATTERNS.items():
                pattern_counts[category] += len(pattern.findall(content))
            for category, pattern in SECRET_SHAPES.items():
                for match in pattern.finditer(content):
                    line = content.count(b"\n", 0, match.start()) + 1
                    if category == "literal_api_key" and (
                        b"test" in match.group(0).lower() or b"synthetic" in match.group(0).lower()
                    ) and ("test_" in part_name or "probe_" in part_name or "run_c4.py" in part_name):
                        synthetic_credential_literals[part_name] += 1
                        continue
                    shape_locations.append({"file": part_name, "line": line, "category": category})
            if len(known_key) >= 16:
                for category, needle in (("known_key_full", known_key),
                                         ("known_key_prefix12", known_key[:12]),
                                         ("known_key_suffix12", known_key[-12:])):
                    if needle in content:
                        known_key_locations.append({"file": part_name, "category": category})

    patent_results = []
    for name in PATENTS:
        obj = json.loads((root / name).read_text(encoding="utf-8"))
        observed = set(walk_keys(obj))
        patent_results.append({
            "path": name,
            "sha256": sha256((root / name).read_bytes()),
            "forbidden_keys_present": sorted(observed & FORBIDDEN_PATENT_KEYS),
            "patent_assay_ids": sorted({x for x in PATENT_ASSAYS if x.encode() in (root / name).read_bytes()}),
        })

    tnap_manifest_path = "data/benchmarks/tnap_chembl1738510_v1/manifest.json"
    tnap_bytes = (root / tnap_manifest_path).read_bytes()
    tnap_manifest = json.loads(tnap_bytes)
    tnap_card = (root / "outputs/d3_tnap_20261019/freeze_tnap_v1/pool_card.md").read_bytes()
    assert sha256(tnap_card) == tnap_manifest["pool_card_sha256"]
    card_match = re.search(rb"^# TNAP (CHEMBL[0-9]+) pool card v1", tnap_card)
    assert card_match is not None
    tnap_id = card_match.group(1).decode("ascii")
    provenance = (root / "PATENT_EXCERPTS_PROVENANCE.md").read_bytes()
    assert all(assay.encode("ascii") in provenance for assay in PATENT_ASSAYS)
    # The historical negative-control manifest is kept only in the verified backup.
    backup = root / ".sync_audit/backup_20261015_bbea8ee9/remote_snapshot.zip"
    dyrk3_manifest = None
    dyrk3_sha = None
    if backup.is_file():
        with zipfile.ZipFile(backup) as archive:
            raw = archive.read("data/curation_private/frozen_dyrk3_v1/manifest.json")
        dyrk3_sha = sha256(raw)
        dyrk3_manifest = json.loads(raw)
    # A clean clone cannot contain the private backup. The pinned verified digest
    # and assay ID are public metadata and can still be checked there.
    if dyrk3_manifest is None:
        dyrk3_sha = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"
        dyrk3_id = "CHEMBL5363961"
        backup_available = False
    else:
        dyrk3_id = dyrk3_manifest["assay_chembl_id"]
        backup_available = True
    assert dyrk3_sha == "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"

    candidate_files = [name for name in paths if name.endswith("/public/candidates.jsonl")]
    candidate_results = []
    for name in candidate_files:
        rows = [json.loads(line) for line in (root / name).read_text(encoding="utf-8").splitlines() if line]
        keys = [set(row) for row in rows]
        candidate_results.append({
            "path": name,
            "rows": len(rows),
            "field_sets": sorted({",".join(sorted(s)) for s in keys}),
            "required_fields_all_rows": all({"compound_key", "standardized_smiles"} <= s for s in keys),
            "exact_public_fields_all_rows": all(s == {"compound_key", "standardized_smiles"} for s in keys),
            "forbidden_result_fields_present": sorted({"outcome", "is_hit", "label", "standard_value", "activity"} & set().union(*keys)),
            "sha256": sha256((root / name).read_bytes()),
        })

    expected_candidate_rows = {
        "data/benchmarks/tnap_chembl1738510_v1/public/candidates.jsonl": 462,
        "outputs/d3_tnap_20261019/freeze_tnap_v1/public/candidates.jsonl": 462,
        "data/benchmarks/dyrk3_chembl5363961_v1/public/candidates.jsonl": 231,
    }
    candidate_coverage_ok = {
        item["path"]: item["rows"] for item in candidate_results
    } == expected_candidate_rows
    dyrk3_public_path = root / "data/benchmarks/dyrk3_chembl5363961_v1/public/candidates.jsonl"
    dyrk3_freeze_path = root / "data/benchmarks/dyrk3_chembl5363961_v1/freeze_manifest.json"
    dyrk3_receipt_path = root / "data/benchmarks/dyrk3_chembl5363961_v1/public/public_receipt.json"
    published_dyrk3_manifest = json.loads(dyrk3_freeze_path.read_bytes())
    published_dyrk3_receipt = json.loads(dyrk3_receipt_path.read_bytes())
    dyrk3_lock_ok = (
        sha256(dyrk3_freeze_path.read_bytes()) == dyrk3_sha
        and published_dyrk3_manifest["data_sha256"]["public_candidates"] == sha256(dyrk3_public_path.read_bytes())
        and published_dyrk3_receipt["candidates_sha256"] == sha256(dyrk3_public_path.read_bytes())
        and published_dyrk3_manifest["status"] == "frozen_dyrk3_v1"
    )

    forbidden_paths = [name for name in paths if any(part.lower() in
        {"curation_private", "config", "work", "github_snapshot_20261018", ".sync_audit"}
        or "private" in part.lower() for part in Path(name).parts[:-1])]
    over5 = [{"path": name, "bytes": size} for name, size in sizes.items() if size > 5_000_000]
    over50 = [{"path": name, "bytes": size} for name, size in sizes.items() if size > 50_000_000]
    return {
        "commands": {
            "indexed_paths": "git ls-files -z",
            "credential_search": "binary regex over every indexed file and ZIP member; categories api_key, Authorization, Bearer, sk-, ZHIPU, GLM_, hex/base64 runs >=32",
            "patent_fields": "recursive JSON key inspection on both patent excerpts",
            "candidate_interface": "parse every indexed */public/candidates.jsonl row and inspect keys",
            "sizes": "git ls-files -z | xargs -0 du -h | sort -h | tail -30 (equivalent per-file byte scan on Windows)",
        },
        "indexed_file_count": len(paths),
        "indexed_total_bytes": sum(sizes.values()),
        "credential_pattern_hits": dict(pattern_counts),
        "credential_value_shape_hits": shape_locations,
        "synthetic_credential_literal_hits": dict(synthetic_credential_literals),
        "known_local_key_matches": known_key_locations,
        "known_local_key_file_present": bool(known_key),
        "patent_excerpts": patent_results,
        "pool_membership": {
            "tnap_manifest_sha256": sha256(tnap_bytes), "tnap_assay_id": tnap_id,
            "tnap_pool_card_sha256": sha256(tnap_card),
            "dyrk3_manifest_sha256": dyrk3_sha, "dyrk3_assay_id": dyrk3_id,
            "dyrk3_backup_available": backup_available,
            "patent_provenance_sha256": sha256(provenance),
            "patent_assays_outside_both_frozen_pools": not (PATENT_ASSAYS & {tnap_id, dyrk3_id}),
        },
        "candidate_interfaces": candidate_results,
        "candidate_coverage_ok": candidate_coverage_ok,
        "published_dyrk3_lock_ok": dyrk3_lock_ok,
        "indexed_private_paths": forbidden_paths,
        "files_over_5mb": over5,
        "files_over_50mb": over50,
        "largest_files": [{"path": name, "bytes": sizes[name]}
                          for name in sorted(paths, key=lambda p: sizes[p], reverse=True)[:30]],
        "pass_structural": (
            not shape_locations and not known_key_locations and not forbidden_paths and not over50
            and all(not x["forbidden_keys_present"] for x in patent_results)
            and not (PATENT_ASSAYS & {tnap_id, dyrk3_id})
            and candidate_coverage_ok and dyrk3_lock_ok
            and all(x["exact_public_fields_all_rows"] and not x["forbidden_result_fields_present"]
                    for x in candidate_results)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = scan(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "indexed_file_count", "indexed_total_bytes", "credential_value_shape_hits",
        "known_local_key_matches", "indexed_private_paths", "files_over_5mb", "files_over_50mb",
        "pass_structural")}, ensure_ascii=False))
    if not result["pass_structural"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

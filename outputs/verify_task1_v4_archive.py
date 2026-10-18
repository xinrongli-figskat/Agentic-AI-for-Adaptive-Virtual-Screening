"""Verify a downloaded Task 1 v4 evidence archive without extracting private data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def verify(path: Path, expected_sha256: str | None = None) -> dict:
    archive = Path(path).resolve(strict=True)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected_sha256 and actual != expected_sha256.lower():
        raise ValueError("Whole-archive SHA-256 differs from remote receipt")
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.namelist()
        if len(members) != len(set(members)):
            raise ValueError("Duplicate archive member")
        if "EXPORT_MANIFEST.json" not in members:
            raise ValueError("Missing export manifest")
        manifest = json.loads(bundle.read("EXPORT_MANIFEST.json"))
        if manifest.get("format") != "task1_v4_closeout_v1":
            raise ValueError("Unexpected archive format")
        files = manifest.get("files") or {}
        if set(members) != set(files) | {"EXPORT_MANIFEST.json"}:
            raise ValueError("Member list differs from manifest")
        for name, wanted in files.items():
            if name.startswith("/") or ".." in Path(name).parts or not name.startswith(("run/", "review/")):
                raise ValueError("Unsafe member name: " + name)
            if hashlib.sha256(bundle.read(name)).hexdigest() != wanted:
                raise ValueError("Member SHA-256 mismatch: " + name)
        summary = json.loads(bundle.read("review/summary.json"))
        state = json.loads(bundle.read("run/state.json"))
        if summary["stored_status"] != state["status"] or summary["lifetime_llm_attempts"] != state["llm_attempts"]:
            raise ValueError("Summary differs from archived state")
        if summary["effective_closure_reason"] != "llm_budget_exhausted":
            raise ValueError("Expected v4 LLM budget closeout")
        if state["llm_attempts"] != state["protocol"]["maximum_llm_attempts"]:
            raise ValueError("Archived state is not at LLM budget")
        if (state["assays"].get("CHEMBL5734042") or {}).get("decision") is not None:
            raise ValueError("S1PR1 was no longer undecided in the archived state")
        return {"verified": True, "archive": str(archive), "sha256": actual,
                "member_count": len(files), "stored_status": state["status"],
                "effective_closure_reason": summary["effective_closure_reason"],
                "new_v4_llm_attempts": summary["new_v4_llm_attempts"],
                "s1pr1_decision": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.expected_sha256), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

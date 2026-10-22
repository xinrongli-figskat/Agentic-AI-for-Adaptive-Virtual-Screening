"""Hash all saved D3 artifacts after the D3-1 hard stop; excludes itself."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if (ROOT / "STATUS").read_text().strip() != "blocked":
        raise ValueError("This manifest is only for the D3-1 blocked state")
    files = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                          "sha256": sha(path), "private": "_private_" in path.as_posix()})
    result = {"schema": "d3_tnap_blocked_manifest_v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "status": "blocked", "blocker": "d3_1_homogeneity_assertion", "self_excluded": True,
              "database_sha256": "4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142",
              "locked_coldstart_spec_sha256": "9fd66ccb5606276349623c10fa60a5fe7bad3082293f04ccad349c2621a6f552",
              "d3_2_to_d3_6_not_run": True, "glm_calls": 0, "files": files}
    (ROOT / "MANIFEST.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(sha(ROOT / "MANIFEST.json"))


if __name__ == "__main__":
    main()

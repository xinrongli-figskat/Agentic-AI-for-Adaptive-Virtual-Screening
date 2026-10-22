"""Lock authorized identity rule and exact D6 gate text before measurement."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D6 = Path(r"C:\Users\lixinrong\.codex\attachments\93840082-71cd-4b4c-a4b5-1c21195014a4\已粘贴的文本.txt")
raw = D6.read_bytes()
start = raw.index("## A-2：预锁判定表".encode())
end = raw.index("## A-3：规则验证".encode(), start)
part = raw[start:end]
gate = ROOT / "d6_a2_gate_rule_unchanged.md"
lock = ROOT / "gate_rule_lock.json"
if gate.exists() or lock.exists():
    raise SystemExit("Existing rule lock; do not overwrite")
gate.write_bytes(part)
files = [ROOT / "identity_unit_rule_v2.md", gate]
lock.write_text(json.dumps({
    "locked_utc": datetime.now(timezone.utc).isoformat(),
    "post_exposure": True,
    "source_d6_sha256": hashlib.sha256(raw).hexdigest(),
    "gate_extract_is_exact_source_bytes": True,
    "files": [{"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
    "glm_calls": 0,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(lock.read_text(encoding="utf-8"))

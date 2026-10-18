"""Budgeted batch-label oracle with a deliberately narrow campaign-facing tool.

The LLM may receive only ``public_state`` and ``query_batch_tool`` outputs. It
must not receive a Python/file/shell/network tool or a reference to this object.
"""

import hashlib
import json
from pathlib import Path


class QueryRejected(ValueError):
    """A failed request reveals no outcomes and uses no query budget."""


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def deterministic_order(keys, seed, namespace):
    """Stable, label-blind ordering used for initialization or tie-breaking."""
    return sorted(keys, key=lambda key: (hashlib.sha256(
        (namespace + "|" + str(seed) + "|" + key).encode("utf-8")).digest(), key))


def verify_prepared(public_dir, private_dir):
    """Verify pre-freeze export without returning any outcomes or label paths."""
    public_dir, private_dir = Path(public_dir), Path(private_dir)
    public_receipt = read_json(public_dir / "public_receipt.json")
    private_receipt = read_json(private_dir / "private_receipt.json")
    if public_receipt.get("status") != "pre_freeze_export_not_campaign_ready" or \
       private_receipt.get("status") != "pre_freeze_export_not_campaign_ready":
        raise ValueError("Unexpected preparation status")
    if public_receipt.get("pool_id") != private_receipt.get("pool_id"):
        raise ValueError("Public/private pool ID mismatch")
    if sha256_file(public_dir / "candidates.jsonl") != public_receipt["candidates_sha256"] or \
       public_receipt["candidates_sha256"] != private_receipt["public_candidates_sha256"]:
        raise ValueError("Public candidate checksum mismatch")
    if sha256_file(private_dir / "oracle_labels.jsonl") != private_receipt["private_labels_sha256"]:
        raise ValueError("Private label checksum mismatch")
    candidates = read_jsonl(public_dir / "candidates.jsonl")
    labels = read_jsonl(private_dir / "oracle_labels.jsonl")
    if len(candidates) != 231 or len(labels) != 231:
        raise ValueError("Prepared pool count changed")
    if any(set(row) != {"compound_key", "standardized_smiles"} for row in candidates):
        raise ValueError("Public candidate contains an unapproved field")
    public_ids = [row["compound_key"] for row in candidates]
    private_ids = [row["compound_key"] for row in labels]
    if len(set(public_ids)) != 231 or len(set(private_ids)) != 231 or set(public_ids) != set(private_ids):
        raise ValueError("Candidate and label IDs do not match uniquely")
    if any(row.get("outcome") not in (0, 1) for row in labels):
        raise ValueError("Private label is not binary")
    return {"verified": True, "status": public_receipt["status"],
            "pool_id": public_receipt["pool_id"], "candidate_count": len(candidates),
            "public_sha256": public_receipt["candidates_sha256"]}


class BatchOracle:
    def __init__(self, candidates, private_labels, *, seed, total_budget, initialization_queries, batch_size):
        if total_budget <= 0 or initialization_queries <= 0 or batch_size <= 0 or \
           (total_budget - initialization_queries) % batch_size:
            raise ValueError("Invalid budget or feedback schedule")
        if len(candidates) < total_budget:
            raise ValueError("Pool smaller than query budget")
        self._public = {}
        for row in candidates:
            if set(row) != {"compound_key", "standardized_smiles"}:
                raise ValueError("Campaign candidate has an unapproved field")
            key = row["compound_key"]
            if not isinstance(key, str) or key in self._public:
                raise ValueError("Invalid or duplicated candidate key")
            self._public[key] = dict(row)
        self._private = dict(private_labels)
        if set(self._private) != set(self._public) or any(v not in (0, 1) for v in self._private.values()):
            raise ValueError("Private outcomes do not match the public pool")
        self._seed, self._total, self._initial, self._batch = seed, total_budget, initialization_queries, batch_size
        self._queried = set()
        self._history = []
        self._round = 0
        self._rejected = 0
        self._closed = False

    def proposed_initial_ids(self):
        return deterministic_order(self._public, self._seed, "init")[:self._initial]

    def public_state(self):
        return {
            "candidate_pool": [self._public[k] for k in sorted(self._public)],
            "revealed": [dict(r) for r in self._history],
            "queried_count": len(self._queried),
            "remaining_budget": self._total - len(self._queried),
            "next_round": self._round,
            "next_batch_size": 0 if self._closed or len(self._queried) == self._total else
                               self._initial if self._round == 0 else self._batch,
            "closed": self._closed,
        }

    def _reject(self, reason):
        self._rejected += 1
        if self._rejected >= 5:
            self._closed = True
        raise QueryRejected(reason)

    def query_batch_tool(self, arguments):
        """Only tool entry point: accepts {compound_keys: [IDs]}, no path or score."""
        if self._closed or len(self._queried) == self._total:
            self._reject("Campaign session is closed")
        if not isinstance(arguments, dict) or set(arguments) != {"compound_keys"}:
            self._reject("Only compound_keys is an allowed argument")
        keys = arguments["compound_keys"]
        expected = self._initial if self._round == 0 else self._batch
        if not isinstance(keys, list) or len(keys) != expected or not all(isinstance(k, str) for k in keys):
            self._reject("Wrong batch size or ID type")
        if len(set(keys)) != len(keys):
            self._reject("Repeated ID within the batch")
        if any(k not in self._public for k in keys):
            self._reject("ID outside the public pool")
        if any(k in self._queried for k in keys):
            self._reject("Already queried ID")
        if len(self._queried) + len(keys) > self._total:
            self._reject("Query budget exceeded")
        if self._round == 0 and keys != self.proposed_initial_ids():
            self._reject("Initialization IDs do not match the frozen label-blind rule")
        # Validate the entire batch before revealing any outcome.
        result = [{"compound_key": key, "outcome": self._private[key]} for key in keys]
        self._queried.update(keys)
        self._history.extend(result)
        round_number = self._round
        self._round += 1
        if len(self._queried) == self._total:
            self._closed = True
        return {"round": round_number, "observations": result,
                "queried_count": len(self._queried), "remaining_budget": self._total - len(self._queried)}

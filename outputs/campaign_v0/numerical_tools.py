"""Label-blind RDKit features and feedback-dependent numerical acquisition."""

import hashlib
import time

from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator


POLICIES = ("knn_greedy", "knn_diverse", "uniform_random")


def seeded_key(namespace, seed, round_number, compound_key):
    message = f"{namespace}|{seed}|{round_number}|{compound_key}"
    return hashlib.sha256(message.encode("utf-8")).digest(), compound_key


class NumericalTools:
    def __init__(self, candidates, radius=2, bits=2048, include_chirality=True,
                 representation="bit"):
        if representation not in ("bit", "count"):
            raise ValueError("Representation must be bit or count")
        started = time.perf_counter()
        self.representation = representation
        self.smiles = {}
        self.fingerprints = {}
        generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=radius, fpSize=bits, includeChirality=include_chirality
        )
        for row in candidates:
            if set(row) != {"compound_key", "standardized_smiles"}:
                raise ValueError("Numerical tool received unapproved candidate fields")
            key, smiles = row["compound_key"], row["standardized_smiles"]
            if key in self.smiles:
                raise ValueError("Duplicate compound key")
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError("Unparseable public candidate structure: " + key)
            self.smiles[key] = smiles
            self.fingerprints[key] = (generator.GetFingerprint(mol) if representation == "bit"
                                      else generator.GetSparseCountFingerprint(mol))
        self.feature_build_seconds = time.perf_counter() - started

    def score_knn(self, state, k=5, prior_weight=2.0):
        """Observed-label-only weighted kNN; no global prevalence or private data."""
        revealed = state["revealed"]
        observed_ids = {row["compound_key"] for row in revealed}
        if len(observed_ids) != len(revealed) or not observed_ids.issubset(self.fingerprints):
            raise ValueError("Invalid revealed observations")
        if any(row["outcome"] not in (0, 1) for row in revealed):
            raise ValueError("Invalid revealed outcome")
        base = (1 + sum(row["outcome"] for row in revealed)) / (2 + len(revealed))
        scores = {}
        for compound_key in self.fingerprints:
            if compound_key in observed_ids:
                continue
            neighbors = sorted(
                ((DataStructs.TanimotoSimilarity(self.fingerprints[compound_key],
                                                self.fingerprints[row["compound_key"]]), row["outcome"])
                 for row in revealed),
                key=lambda item: -item[0],
            )[:k]
            weights = [(similarity ** 2, outcome) for similarity, outcome in neighbors]
            scores[compound_key] = (prior_weight * base + sum(w * outcome for w, outcome in weights)) / \
                                   (prior_weight + sum(w for w, _ in weights))
        return scores

    def describe_state(self, state):
        """Compact, revealed-label-only model diagnostics for policy choice."""
        scores = self.score_knn(state)
        values = sorted(scores.values())
        top = sorted(scores, key=lambda key: -scores[key])[:10]
        observed_ids = [row["compound_key"] for row in state["revealed"]]
        similarities = [max((DataStructs.TanimotoSimilarity(self.fingerprints[key],
                                                             self.fingerprints[ref])
                             for ref in observed_ids), default=0.0) for key in top]
        return {"unqueried_count": len(scores),
                "predicted_hit_score_min": values[0] if values else None,
                "predicted_hit_score_median": values[len(values) // 2] if values else None,
                "predicted_hit_score_max": values[-1] if values else None,
                "top_10_mean_score": sum(scores[key] for key in top) / len(top) if top else None,
                "top_10_mean_max_similarity_to_observed":
                    sum(similarities) / len(similarities) if similarities else None}

    def select_batch(self, state, *, policy, seed, round_number, diversity_weight=0.2):
        if policy not in POLICIES:
            raise ValueError("Unknown acquisition policy")
        wanted = state["next_batch_size"]
        if wanted <= 0 or wanted > state["remaining_budget"]:
            raise ValueError("No valid next batch")
        queried = {r["compound_key"] for r in state["revealed"]}
        available = set(self.fingerprints) - queried
        if len(available) < wanted:
            raise ValueError("Insufficient candidates")
        if policy == "uniform_random":
            return sorted(available, key=lambda key: seeded_key("random", seed, round_number, key))[:wanted]
        scores = self.score_knn(state)
        if policy == "knn_greedy":
            return sorted(available, key=lambda key: (-scores[key], *seeded_key("tie", seed, round_number, key)))[:wanted]
        selected = []
        reference = set(queried)
        while len(selected) < wanted:
            def acquisition(key):
                penalty = max((DataStructs.TanimotoSimilarity(self.fingerprints[key], self.fingerprints[ref])
                               for ref in reference), default=0.0)
                return scores[key] - diversity_weight * penalty
            chosen = min(available, key=lambda key: (-acquisition(key), *seeded_key("tie", seed, round_number, key)))
            selected.append(chosen)
            available.remove(chosen)
            reference.add(chosen)
        return selected

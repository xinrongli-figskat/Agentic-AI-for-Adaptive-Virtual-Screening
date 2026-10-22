"""D5 numerical menu. Frozen v1 acquisition functions are called, never edited."""

from __future__ import annotations

import numpy as np
from rdkit import DataStructs
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression

from campaign_v0.numerical_tools import NumericalTools, seeded_key


MENU = (
    "knn_greedy", "knn_diverse", "uniform_random",
    "persistent_random_until_first_hit", "diverse_random_coldstart",
    "logreg_greedy", "ens_one_step_proxy",
)
OLD = MENU[:3]


class ExpandedTools:
    def __init__(self, candidates, representation):
        self.legacy = NumericalTools(candidates, representation=representation)
        self.representation = representation
        self.keys = sorted(self.legacy.fingerprints)
        self.index = {key: i for i, key in enumerate(self.keys)}
        fps = [self.legacy.fingerprints[key] for key in self.keys]
        self.sim = np.asarray(
            [DataStructs.BulkTanimotoSimilarity(fp, fps) for fp in fps], dtype=np.float64
        )
        self.features = None

    @staticmethod
    def hits(state):
        return sum(int(row["outcome"]) for row in state["revealed"])

    def _feature_matrix(self):
        if self.features is not None:
            return self.features
        fingerprints = [self.legacy.fingerprints[key] for key in self.keys]
        maps = []
        for fp in fingerprints:
            if self.representation == "bit":
                maps.append({int(bit): 1 for bit in fp.GetOnBits()})
            else:
                maps.append({int(bit): int(count) for bit, count in fp.GetNonzeroElements().items()})
        columns = {bit: i for i, bit in enumerate(sorted({bit for row in maps for bit in row}))}
        row_ids, col_ids, values = [], [], []
        for row_id, row in enumerate(maps):
            for bit, value in row.items():
                row_ids.append(row_id)
                col_ids.append(columns[bit])
                values.append(value)
        self.features = csr_matrix((values, (row_ids, col_ids)),
                                   shape=(len(self.keys), len(columns)), dtype=np.float64)
        return self.features

    def _knn_probabilities(self, observed_indices, observed_outcomes, remaining_indices):
        """Vectorized equivalent of the frozen weighted kNN for fantasy updates."""
        n = len(observed_indices)
        base = (1 + sum(observed_outcomes)) / (2 + n)
        matrix = self.sim[np.ix_(remaining_indices, observed_indices)]
        order = np.argsort(-matrix, axis=1, kind="stable")[:, : min(5, n)]
        selected = np.take_along_axis(matrix, order, axis=1)
        weights = selected * selected
        outcomes = np.asarray(observed_outcomes, dtype=np.float64)
        selected_outcomes = outcomes[order]
        return (2 * base + (weights * selected_outcomes).sum(axis=1)) / (2 + weights.sum(axis=1))

    def _ens_proxy(self, state, seed, round_number):
        observed = state["revealed"]
        observed_indices = [self.index[row["compound_key"]] for row in observed]
        observed_outcomes = [int(row["outcome"]) for row in observed]
        observed_set = set(observed_indices)
        available = [i for i in range(len(self.keys)) if i not in observed_set]
        exact = self.legacy.score_knn(state)
        p = {self.index[key]: float(value) for key, value in exact.items()}

        def key_for(i, score):
            return (-score, *seeded_key("tie", seed, round_number, self.keys[i]))

        top_p = sorted(available, key=lambda i: key_for(i, p[i]))[:64]
        influence = {i: p[i] * (1 - p[i]) * float(self.sim[i, available].mean())
                     for i in available}
        top_info = sorted(available, key=lambda i: key_for(i, influence[i]))[:64]
        shortlist = sorted(set(top_p) | set(top_info))
        scores = {}
        for i in shortlist:
            future = [j for j in available if j != i]
            current_utility = sum(sorted((p[j] for j in future), reverse=True)[:10])
            fantasy_utilities = []
            for outcome in (0, 1):
                updated = self._knn_probabilities(observed_indices + [i],
                                                  observed_outcomes + [outcome], future)
                fantasy_utilities.append(float(np.sort(updated)[-10:].sum()))
            expected_future = (1 - p[i]) * fantasy_utilities[0] + p[i] * fantasy_utilities[1]
            scores[i] = p[i] + 0.25 * (expected_future - current_utility)
        wanted = state["next_batch_size"]
        assert len(scores) >= wanted
        return [self.keys[i] for i in sorted(scores, key=lambda i: key_for(i, scores[i]))[:wanted]]

    def _logreg(self, state, seed, round_number):
        labels = [int(row["outcome"]) for row in state["revealed"]]
        if len(set(labels)) < 2:
            return self.legacy.select_batch(state, policy="uniform_random", seed=seed,
                                            round_number=round_number)
        observed = [self.index[row["compound_key"]] for row in state["revealed"]]
        observed_set = set(observed)
        available = [i for i in range(len(self.keys)) if i not in observed_set]
        features = self._feature_matrix()
        model = LogisticRegression(C=1.0, solver="liblinear", random_state=0, max_iter=200)
        model.fit(features[observed], labels)
        column = list(model.classes_).index(1)
        probabilities = model.predict_proba(features[available])[:, column]
        ranked = sorted(zip(available, probabilities),
                        key=lambda pair: (-float(pair[1]),
                                          *seeded_key("tie", seed, round_number,
                                                      self.keys[pair[0]])))
        return [self.keys[i] for i, _ in ranked[: state["next_batch_size"]]]

    def select(self, state, policy, seed, round_number):
        if policy not in MENU:
            raise ValueError("Unknown D5 menu item")
        if policy in OLD:
            return self.legacy.select_batch(state, policy=policy, seed=seed,
                                            round_number=round_number)
        if policy == "persistent_random_until_first_hit":
            effective = "uniform_random" if self.hits(state) == 0 else "knn_greedy"
            return self.legacy.select_batch(state, policy=effective, seed=seed,
                                            round_number=round_number)
        if policy == "diverse_random_coldstart":
            effective = "uniform_random" if self.hits(state) == 0 else "knn_diverse"
            return self.legacy.select_batch(state, policy=effective, seed=seed,
                                            round_number=round_number)
        if policy == "logreg_greedy":
            return self._logreg(state, seed, round_number)
        return self._ens_proxy(state, seed, round_number)

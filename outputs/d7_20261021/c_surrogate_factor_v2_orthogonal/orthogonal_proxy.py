"""Label-blind six-proxy interface for the D7-C3 orthogonal experiment.

Only public structures enter the constructor. ``score`` accepts revealed
compound/outcome pairs and returns probabilities for unqueried compounds.
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from outputs.d7_20261021.c_surrogate_factor.c1_surrogates import SurrogateBank

NAMES = ("S_weak", "S_maccs", "S_incumbent", "S_strong",
         "S_morgan_logreg", "S_morgan_gbdt")


class OrthogonalProxy:
    def __init__(self, candidates):
        self.bank = SurrogateBank(candidates)
        self.keys = self.bank.keys
        self.index = self.bank.index
        self._morgan_sparse = None
        self._morgan_dense = None

    def morgan_sparse(self):
        """The exact D5 bit feature construction, including active-column order."""
        if self._morgan_sparse is None:
            fingerprints = [self.bank.incumbent.fingerprints[key] for key in self.keys]
            maps = [{int(bit): 1 for bit in fp.GetOnBits()} for fp in fingerprints]
            columns = {bit: i for i, bit in enumerate(sorted({bit for row in maps for bit in row}))}
            row_ids, col_ids, values = [], [], []
            for row_id, row in enumerate(maps):
                for bit, value in row.items():
                    row_ids.append(row_id)
                    col_ids.append(columns[bit])
                    values.append(value)
            self._morgan_sparse = csr_matrix((values, (row_ids, col_ids)),
                                             shape=(len(self.keys), len(columns)), dtype=np.float64)
        return self._morgan_sparse

    def morgan_dense(self):
        if self._morgan_dense is None:
            dense = np.zeros((len(self.keys), 2048), dtype=np.uint8)
            for i, key in enumerate(self.keys):
                for bit in self.bank.incumbent.fingerprints[key].GetOnBits():
                    dense[i, bit] = 1
            self._morgan_dense = dense
        return self._morgan_dense

    def score(self, name, revealed):
        if name not in NAMES:
            raise ValueError(name)
        observations = list(revealed)
        observed_keys = [row["compound_key"] for row in observations]
        if len(observed_keys) != len(set(observed_keys)) or any(key not in self.index for key in observed_keys):
            raise ValueError("Duplicate or out-of-pool observation")
        if any(set(row) != {"compound_key", "outcome"} or row["outcome"] not in (0, 1)
               for row in observations):
            raise ValueError("Unapproved observation schema")
        outcomes = [int(row["outcome"]) for row in observations]
        if len(set(outcomes)) < 2:
            return None
        if name in ("S_weak", "S_maccs", "S_incumbent", "S_strong"):
            return self.bank.score(name, observations)
        observed = [self.index[key] for key in observed_keys]
        observed_set = set(observed)
        available = [i for i in range(len(self.keys)) if i not in observed_set]
        if name == "S_morgan_logreg":
            # D5 expanded_tools.py:_logreg uses these explicit hyperparameters.
            features = self.morgan_sparse()
            model = LogisticRegression(C=1.0, solver="liblinear", random_state=0, max_iter=200)
        else:
            features = self.morgan_dense()
            model = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                               learning_rate=0.1, random_state=0)
        model.fit(features[observed], outcomes)
        positive = list(model.classes_).index(1)
        probabilities = model.predict_proba(features[available])[:, positive]
        return {self.keys[i]: float(p) for i, p in zip(available, probabilities)}

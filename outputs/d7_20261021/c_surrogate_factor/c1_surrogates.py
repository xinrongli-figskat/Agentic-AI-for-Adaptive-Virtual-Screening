"""D7-C1 label-blind surrogate definitions. No oracle or private-file access.

This module is locked before C2. Its dependency versions and descriptor name list
must be recorded when executed. C2/C3 must not proceed unless the 11-item D7
preflight passes in the execution environment.
"""

from __future__ import annotations

import math

import numpy as np
from rdkit import Chem, rdBase
from rdkit.Chem import Crippen, Descriptors, MACCSkeys, rdMolDescriptors
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

try:
    from campaign_v0.numerical_tools import NumericalTools
except ModuleNotFoundError as exc:
    if exc.name != "campaign_v0":
        raise
    from outputs.campaign_v0.numerical_tools import NumericalTools


SURROGATES = ("S_weak", "S_maccs", "S_incumbent", "S_strong")
WEAK_NAMES = ("MolWt", "MolLogP", "TPSA", "HBD", "HBA", "RotBonds", "Rings", "AromaticRings")


def _weak(mol):
    return (
        Descriptors.MolWt(mol), Crippen.MolLogP(mol), rdMolDescriptors.CalcTPSA(mol),
        rdMolDescriptors.CalcNumHBD(mol), rdMolDescriptors.CalcNumHBA(mol),
        rdMolDescriptors.CalcNumRotatableBonds(mol), rdMolDescriptors.CalcNumRings(mol),
        rdMolDescriptors.CalcNumAromaticRings(mol),
    )


def _numeric(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def _descriptor(function, mol):
    try:
        return _numeric(function(mol))
    except (ValueError, ArithmeticError, RuntimeError):
        return float("nan")


def _fill_from_training(train, test):
    """Median imputation, using revealed/training observations only."""
    train = np.asarray(train, dtype=float).copy()
    test = np.asarray(test, dtype=float).copy()
    medians = []
    for column in range(train.shape[1]):
        finite = train[np.isfinite(train[:, column]), column]
        median = float(np.median(finite)) if finite.size else 0.0
        medians.append(median)
        train[~np.isfinite(train[:, column]), column] = median
        test[~np.isfinite(test[:, column]), column] = median
    return train, test, medians


class SurrogateBank:
    """Construct public structural features; scores may use only supplied observations."""

    def __init__(self, candidates):
        if rdBase.rdkitVersion != "2026.09.1":
            raise RuntimeError("D7-C1 requires RDKit 2026.09.1; do not change descriptors after C1 lock")
        rows = list(candidates)
        if any(set(row) != {"compound_key", "standardized_smiles"} for row in rows):
            raise ValueError("Candidates must contain only public key and structure")
        self.keys = sorted(row["compound_key"] for row in rows)
        if len(set(self.keys)) != len(rows):
            raise ValueError("Duplicate compound key")
        smiles = {row["compound_key"]: row["standardized_smiles"] for row in rows}
        mols = []
        for key in self.keys:
            mol = Chem.MolFromSmiles(smiles[key])
            if mol is None:
                raise ValueError("Invalid public structure for " + key)
            mols.append(mol)
        self.index = {key: i for i, key in enumerate(self.keys)}
        self.descriptor_functions = tuple(sorted(Descriptors._descList, key=lambda pair: pair[0]))
        if len({name for name, _ in self.descriptor_functions}) != len(self.descriptor_functions):
            raise ValueError("RDKit descriptor names are not unique")
        self.descriptor_names = tuple(name for name, _ in self.descriptor_functions)
        self.features = {
            "S_weak": np.asarray([[_numeric(value) for value in _weak(mol)] for mol in mols]),
            "S_maccs": np.asarray(
                [[float(fp.GetBit(bit)) for bit in range(1, 167)]
                 for fp in (MACCSkeys.GenMACCSKeys(mol) for mol in mols)]
            ),
            "S_strong": np.asarray(
                [[_descriptor(func, mol) for _, func in self.descriptor_functions] for mol in mols]
            ),
        }
        self.incumbent = NumericalTools(rows, representation="bit")

    def score(self, surrogate, revealed):
        """Return scores for unqueried keys; None means one-class/random fallback.

        `revealed` is the only label-bearing argument. The caller must use the
        original uniform_random policy for a None return, preserving the budget.
        """
        if surrogate not in SURROGATES:
            raise ValueError("Unknown surrogate")
        observations = list(revealed)
        observed_keys = [row["compound_key"] for row in observations]
        if len(set(observed_keys)) != len(observed_keys):
            raise ValueError("Repeated observation")
        if any(key not in self.index for key in observed_keys):
            raise ValueError("Observation outside public pool")
        if any(set(row) != {"compound_key", "outcome"} or row["outcome"] not in (0, 1)
               for row in observations):
            raise ValueError("Observations must contain only key and revealed binary outcome")
        outcomes = [int(row["outcome"]) for row in observations]
        if len(set(outcomes)) < 2:
            return None
        if surrogate == "S_incumbent":
            return self.incumbent.score_knn({"revealed": observations})
        observed = set(observed_keys)
        remaining_keys = [key for key in self.keys if key not in observed]
        train_index = [self.index[key] for key in observed_keys]
        test_index = [self.index[key] for key in remaining_keys]
        matrix = self.features[surrogate]
        x_train, x_test, _ = _fill_from_training(matrix[train_index], matrix[test_index])
        if surrogate == "S_weak":
            mean = x_train.mean(axis=0)
            scale = x_train.std(axis=0)
            scale[scale == 0] = 1.0
            x_train = (x_train - mean) / scale
            x_test = (x_test - mean) / scale
        if surrogate in ("S_weak", "S_maccs"):
            model = LogisticRegression(C=1, solver="liblinear", random_state=0, max_iter=200)
        else:
            model = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                               learning_rate=0.1, random_state=0)
        model.fit(x_train, outcomes)
        positive = list(model.classes_).index(1)
        probabilities = model.predict_proba(x_test)[:, positive]
        return {key: float(probability) for key, probability in zip(remaining_keys, probabilities)}

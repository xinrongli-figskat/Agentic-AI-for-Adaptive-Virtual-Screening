"""Orthogonal acquisition functions; no private input or oracle reader."""
from __future__ import annotations

import numpy as np
from rdkit import DataStructs

from outputs.campaign_v0.numerical_tools import seeded_key
from outputs.d5_20261020.e_menu.expanded_tools import ExpandedTools
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.orthogonal_proxy import OrthogonalProxy

POLICIES = ("greedy", "diverse", "random", "persistent_random_until_first_hit",
            "diverse_random_coldstart", "ens_one_step_proxy")


class OrthogonalSelector:
    def __init__(self, candidates):
        self.proxy = OrthogonalProxy(candidates)
        self.legacy = ExpandedTools(candidates, "bit")
        self.keys = self.proxy.keys
        self.index = self.proxy.index

    def select(self, state, surrogate, policy, seed):
        if policy not in POLICIES:
            raise ValueError(policy)
        round_number = state["next_round"]
        wanted = state["next_batch_size"]
        if policy == "random":
            return self.legacy.legacy.select_batch(state, policy="uniform_random", seed=seed,
                                                   round_number=round_number), "policy_random"
        hits = sum(int(row["outcome"]) for row in state["revealed"])
        if policy == "persistent_random_until_first_hit":
            policy = "random" if hits == 0 else "greedy"
        elif policy == "diverse_random_coldstart":
            policy = "random" if hits == 0 else "diverse"
        if policy == "random":
            return self.legacy.legacy.select_batch(state, policy="uniform_random", seed=seed,
                                                   round_number=round_number), "policy_coldstart_random"
        scores = self.proxy.score(surrogate, state["revealed"])
        if scores is None:
            return self.legacy.legacy.select_batch(state, policy="uniform_random", seed=seed,
                                                   round_number=round_number), "one_class_random_fallback"
        available = set(scores)
        if policy == "greedy":
            ordered = sorted(available, key=lambda key: (-scores[key], *seeded_key("tie", seed, round_number, key)))
            return ordered[:wanted], "scored_greedy"
        if policy == "diverse":
            selected = []
            reference = {row["compound_key"] for row in state["revealed"]}
            fps = self.legacy.legacy.fingerprints
            while len(selected) < wanted:
                def acquisition(key):
                    penalty = max((DataStructs.TanimotoSimilarity(fps[key], fps[ref])
                                   for ref in reference), default=0.0)
                    return scores[key] - 0.2 * penalty
                chosen = min(available, key=lambda key: (-acquisition(key), *seeded_key("tie", seed, round_number, key)))
                selected.append(chosen)
                available.remove(chosen)
                reference.add(chosen)
            return selected, "scored_diverse"
        if surrogate == "S_incumbent":
            return self.legacy._ens_proxy(state, seed, round_number), "ens_frozen_incumbent"
        # The same 64+64 candidate construction as D5; fantasies refit the
        # current surrogate with the hypothetical observation only.
        available_i = [self.index[key] for key in self.keys if key in available]
        p = {self.index[key]: scores[key] for key in scores}
        def key_for(i, score):
            return (-score, *seeded_key("tie", seed, round_number, self.keys[i]))
        top_p = sorted(available_i, key=lambda i: key_for(i, p[i]))[:64]
        influence = {i: p[i] * (1-p[i]) * float(self.legacy.sim[i, available_i].mean())
                     for i in available_i}
        top_info = sorted(available_i, key=lambda i: key_for(i, influence[i]))[:64]
        shortlist = sorted(set(top_p) | set(top_info))
        ensemble_scores = {}
        for i in shortlist:
            future = [j for j in available_i if j != i]
            current = sum(sorted((p[j] for j in future), reverse=True)[:10])
            fantasy = []
            for outcome in (0, 1):
                updated = self.proxy.score(surrogate,
                    state["revealed"] + [{"compound_key": self.keys[i], "outcome": outcome}])
                if updated is None:
                    raise RuntimeError("Fantasy update unexpectedly has one class")
                fantasy.append(sum(sorted((updated[self.keys[j]] for j in future), reverse=True)[:10]))
            expected = (1-p[i])*fantasy[0] + p[i]*fantasy[1]
            ensemble_scores[i] = p[i] + .25*(expected-current)
        chosen_i = sorted(ensemble_scores, key=lambda i: key_for(i, ensemble_scores[i]))[:wanted]
        return [self.keys[i] for i in chosen_i], "ens_equal_64_plus_64"

"""Exact initialization risk for a fixed, finite compound pool.

This module has no access to campaign outcomes. It describes saved curation
counts after exposure and is never used as a new campaign decision rule.
"""
from __future__ import annotations

from scipy.stats import hypergeom


def p_single_class(N: int, K: int, n_init: int = 10) -> dict[str, float]:
    """Return hypergeometric probabilities for a uniform draw without replacement.

    N is the number of usable compounds; K is the number of measured hit
    supports. Exactly n_init distinct compounds are drawn. SciPy's survival
    and mass functions evaluate the probabilities without a binomial
    replacement approximation.
    """
    if any(type(x) is not int for x in (N, K, n_init)):
        raise TypeError("N, K, n_init must be integers")
    if N < 1 or not 0 <= K <= N or not 1 <= n_init <= N:
        raise ValueError("Require N>=1, 0<=K<=N, and 1<=n_init<=N")
    p_no_hit = float(hypergeom.pmf(0, N, K, n_init))
    p_all_hit = float(hypergeom.pmf(n_init, N, K, n_init))
    return {"p_no_hit": p_no_hit, "p_all_hit": p_all_hit,
            "p_single_class": p_no_hit + p_all_hit}

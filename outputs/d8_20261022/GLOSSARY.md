# Glossary for project reports

| Project shorthand | Conventional wording |
|---|---|
| `H@50` | actives retrieved within a 50-compound selection budget |
| `campaign` | active-search run |
| `oracle` / reveal | the held-out measured outcome, disclosed when a compound is selected |
| `structure_prior` | unsupervised structural baseline (ranks compounds from structure alone, using no measured labels) |
| `label_shuffle`; `fixed − label_shuffle` | label-permutation control; performance above a label-permuted null |
| `spread_nontrivial` | between-rule performance range, excluding random selection |
| `adaptive_gap` | shortfall of the best adaptive controller relative to the best single fixed rule |
| `knn_greedy` | nearest-neighbour similarity ranking, pure exploitation |
| `knn_diverse` | nearest-neighbour ranking with a batch-diversity penalty |
| `persistent_random_until_first_hit` | random selection until the first active is found, then exploitation |
| `diverse_random_coldstart` | random selection while no active has been found, otherwise diversity-penalised ranking |
| `ens_one_step_proxy` | one-step lookahead approximation (explicitly not exact expected-information) |
| `measurement depth` | per-compound measurement effort: the number of independent concentration–response determinations recorded for that compound in the source deposition |
| qualification / frozen pool | benchmark admission criteria / fixed evaluation set |

Tier A/B/C and CP-1/CP-2 are internal workflow labels. Do not use them in external writing.

# C3 GBDT menu inconsistency — recorded after the locked CPU matrix

Date: 2026-10-21. The 1,880 locked, post-exposure CPU campaigns completed
without GLM calls. The full-size public synthetic timing probe had found
`S_strong` ENS at 31.04 s and `S_morgan_gbdt` ENS at 37.84 s per decision,
above the declared 5 s limit. The fixed ENS arm was therefore omitted for
both GBDT proxies.

The meta-controller implementation nevertheless retained the six-action
menu and selected ENS inside GBDT runs. The private trajectory audit counted
**116 such decisions across 240 GBDT meta-controller runs**, all with the
full 64+64 shortlist. This is not reduced-compute ENS, but it conflicts with
the declared “do not run ENS in the two GBDT columns” rule and leaves GBDT
fixed and adaptive arms with different available actions. The cause is an
unresolved interaction between the task card's six-policy meta menu and its
partial-crossing ENS exception. The locked runner did not screen ENS out of
GBDT meta actions.

The original run files, lock, and public summary remain unchanged. Its four
common fixed-policy H@50 values, `spread_nontrivial_common`, paired bootstrap
intervals, random floors, six AUC values, and all non-GBDT cells are valid
under their recorded definitions. GBDT `adaptive_gap` and the six-point
AUC-versus-adaptive-gap trend are **provisional, not primary conclusions**.
The six-point AUC-versus-fixed-spread trend remains descriptive and valid.

No C4 GLM arm starts from this inconsistent menu. A versioned resolution
must specify one common meta-controller menu, or explicitly accept a partial
crossing and its comparison limits, before interpreting adaptive gaps or
authorizing the eligible `S_strong` C4 cell. The aggregate count evidence is
`C3_GBDT_META_ENS_AUDIT.json`.

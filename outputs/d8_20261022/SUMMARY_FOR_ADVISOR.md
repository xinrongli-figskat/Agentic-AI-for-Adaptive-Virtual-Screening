# Progress summary

## Data suitable for retrospective evaluation remain scarce

The project has screened ChEMBL 37 activity data and numerically evaluated 81 assay candidates. Sixty-two passed the initial numerical screen. Six have completed focused source review, and one currently supports a usable, source-limited evaluation set: the human TNAP assay. Its molecular structures and measured results can be reconstructed from the cited public sources, so this is a reproducible evaluation set rather than a blinded one. The outcome is not evidence that the other assays are absent; most remain unresolved because the source records do not yet establish compound identity or experimental meaning well enough.

This funnel—62 numerically promising assays, six source reviews, and one source-limited set—quantifies the shortage of suitable public assay data. It also shows why increasing the number of candidate molecules alone cannot solve the problem.

## Active-search comparisons

On the current fixed evaluation set, five repeated language-model runs did not differ clearly from the best single fixed selection rule chosen after observing the results: the mean difference was −0.48 actives within 50 selections, with a 95% interval from −2.47 to 1.51. The interval includes zero. The language-model controller had higher point estimates than uniform policy mixing, a mixture matched to the language model’s observed policy frequencies, and the Thompson-sampling and UCB1 adaptive baselines. Those comparisons are exploratory and do not establish a general advantage: the language model’s action choices vary between runs, and the adaptive-baseline comparisons do not share the same repeat design.

Reproducibility is a material limitation. When the request settings and prompt inputs were byte-for-byte identical, the model selected different rules in 38.5% of 200 paired requests. Across repeated runs with the same random seed, the standard deviation in the number of actives found within 50 selections was 2.19. One malformed structured response was observed in the initial request series, approximately 1% of that segment; the response was retained and handled under a bounded retry rule. A single run is therefore one sample from a variable process, and comparisons require repeated runs.

## Prediction methods and policy switching

Six prediction methods had cross-validated ROC-AUC values from 0.771 to 0.897 on TNAP. Greater model complexity did not imply greater predictive strength. With the same Morgan molecular fingerprints, nearest-neighbour similarity ranking reached 0.897, logistic regression 0.844, and gradient boosting 0.803. Across the six methods, the difference between the best and worst fixed selection rules showed no systematic monotonic relation to prediction AUC.

A further pattern concerned switching between rules. In four of six prediction-method settings, the best adaptive controller did worse than every fixed rule in that setting; in one it tied the fixed rules, and in one it did better than some fixed rules. Thus, in those four settings, the loss was not only from choosing a suboptimal rule: switching among rules itself failed to recover the performance of any fixed choice. The language-model controller was the only adaptive method tested that came close to the best fixed rule in the original seven-policy comparison (a shortfall of 0.48 actives, compared with 5.25 for Thompson sampling). A later single TNAP experiment with a different prediction method and policy menu did not reproduce that near-tie, so the two experiments should not be combined as if they were the same comparison.

## Measurement effort and remaining limitations

“Measurement effort” here means the number of separate concentration–response determinations recorded for a compound in the source deposition. It does not mean the number of members in a chemical series. On TNAP, the median was one and the maximum was 21. This measure predicted the measured active/inactive class with ROC-AUC 0.879, compared with 0.598 for the strongest individual structural descriptor. The source’s dose-response records indicate selective follow-up of compounds that appeared promising. The association is therefore a data-collection bias, not a usable chemical feature. The available record does not establish that series membership alone caused the association.

The project remains a pedagogical prototype using a small number of retrospective public assay sets. TNAP source identity is only partially resolved, DYRK3 is small and has a high active fraction, and the LLM’s current role is mainly to choose among predefined policies. A new synthetic probe has confirmed that the LLM can receive the full preset library while unselected measured outcomes remain hidden; this checks the information boundary, not search performance. A negative result for agentic active search at month end is acceptable and will be reported as such.

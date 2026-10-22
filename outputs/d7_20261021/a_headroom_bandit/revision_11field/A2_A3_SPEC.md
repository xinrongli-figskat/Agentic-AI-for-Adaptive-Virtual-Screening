# D7 A2/A3 specification after explicit user approval

Post-exposure; CPU only; GLM/API requests 0. Prior A1 outputs, blocker, code and manifest remain historical snapshots. The parent saved explicit approval in outputs/d7_20261021/bandit_approval_20261021.md, SHA-256 ae6dfd39b6f1e2f8e38b3bea56216890ec7315137b7965a384aafcee2043fc9a. Approval changes only the information-interface comparator to D5's actual seven-policy controller (11 fields).

## Information interface

Build the summary by invoking the unchanged D5 Controller with a no-network capturing stub. At g4 use its emitted summary verbatim. At g2/g8 change only the task and commitment-note text from a batch of 10 to the actual batch size; preserve all 11 fields and all numerical values, including recent_revealed_hits meaning last ten observations. Bandits receive only this summary. They never receive candidate structures, unrevealed measurements, oracle objects or file paths. Completed-batch reward is obtained at the next summary from changes in cumulative revealed_hits and queried_count. The terminal summary has the same fields and permits the final posterior update. Actual query observations go only to the private runner/oracle and the unchanged numerical tool interface.

Assert exact field-set equality with a dynamically captured D5 production summary. For every g4 decision, assert full summary equality with D5. Synthetic tests mutate unrevealed oracle measurements and require unchanged pre-query summary and controller decision. Only revealed feedback may change subsequent decisions.

## Thompson controller

Seven Beta(1,1) priors, reset at the start of each campaign; no shared posteriors across seeds, pools or representations. Each completed batch with h hits among b actual queries yields r=h/b and adds r to alpha and (1-r) to beta for the executed policy. Fractional updating treats one batch as one bounded reward observation, rather than b independent arm pulls.

At each uncommitted choice, for each menu policy draw using Python random.Random(integer SHA256 of UTF-8 `d7_thompson|seed|round|policy`).betavariate(alpha,beta), choose the maximum, break exact ties in D5 menu order. The algorithm/runtime is recorded. This uses a SHA-256 seeded per-policy/per-round pseudorandom stream independent of global Python or NumPy random state. Pool and representation are omitted from the namespace to pair streams across configurations. Replicate runs repeat the same namespace. No inference based on Python hash().

## UCB1 controller

c=1; empirical mean is the mean of batch fractions r. A policy with n_i=0 has +infinity. For all sampled policies UCB=mean+sqrt(2 ln(t)/n_i), t=1+total completed feedback batches. Maximize score, breaking ties in fixed D5 menu order. Initialization contributes no arm reward. Counts include automatic commitment batches. At g4 it normally explores the first four menu items; the seven-item menu is longer than its four choices, as already declared by D7.

## Persistent-policy semantics and budget

Preserve D5 persistent_random_until_first_hit commitment: when selected with zero known hits, all subsequent still-zero-hit batches remain on that policy until a hit appears; these are automatic commitment steps, not fresh Thompson/UCB draws. Each such batch consumes its normal query budget and credits its reward to the persistent arm. After the first hit, release commitment and resume posterior/UCB choices. Posterior parameters are updated once per delivered batch, including the final batch; the transcript records chosen arm, automatic flag, pre/post feedback values, posterior summaries and number of actual policy choices. This preserves the actual seven-menu action semantics.

All campaigns use frozen pool, 50 total queries, 10 unchanged SHA initialization IDs, no replacement. A2 covers both pools, bit/count, seeds 0-19, two bandits at batch10. A3 covers both pools, bit, seeds0-19, the seven fixed policies and two bandits at batches20/10/5 (g2/g4/g8). Duplicate requested g4-bandit configurations are evaluated once and referenced in both A2 and A3. All 320 unique bandit configurations are actually executed twice, with independent fresh oracle/controller state, and their full timing-free trajectories plus terminal controller state must match. There are 1160 unique configurations: 840 fixed + 320 bandit; 1480 physical runs including repeated bandits. Existing D5 fixed g4 results are regression references, not substitutes for execution.

## Numerical policy invariance

Import unchanged D5 ExpandedTools, unchanged frozen NumericalTools and BatchOracle. next_batch_size adjusts selections only. ENS retains its fixed top-10 future-utility horizon and fixed shortlist/0.25 coefficient even at g2/g8. Logistic model and diversity penalty unchanged. Do not adapt model fit or initialization based on results. Same initialization IDs checked against D5 for each seed. Every g4 fixed trajectory must match D5 exactly in selections, observations and cumulative hits. Both D7 known-good archive regressions are rerun before jobs and recorded.

## Metrics and interpretation locked before outcomes

For each pool/representation/granularity report H50 per arm and paired comparisons versus the best fixed arm selected by the D5/g4 mean (post-exposure reference), and D5 GLM where that actual same-pool/same-representation comparator exists (TNAP only). For A3 best fixed arm is additionally reported within each granularity as a descriptive hindsight comparator. Paired 10,000-bootstrap confidence intervals use NumPy default_rng(20261018), common seed indices, 2.5/97.5 percentiles. Report paired changes g8-g4 and g2-g4 in within-seed nontrivial range; exclude uniform from nontrivial metrics.

Four decision points versus seven arms makes all adaptive controllers prior-dominated. Bandit not beating best fixed supports a limitation of this decision budget, not LLM-specific weakness. Bandit matching/beating GLM provides no extra-value evidence for GLM relative to this conventional comparator. GLM beating bandit is provisional and cannot be cited as benefit before D7-B model variance. A larger retrospective fixed-arm spread is not proof that an adaptive algorithm can exploit it. No new scientific efficacy or benefit claim is made from these CPU results.

## Execution and artifacts

Lock this file and implementation SHA-256 with live UTC before any new campaign. Eight CPU workers maximum, BLAS/OpenMP one thread per worker. Frozen data remain private; individual complete transcripts are saved only in revision_11field/runs_private/ (gitignored). Public result tables contain per-seed H50/aggregate controller stats, no per-compound results. Failures stop evaluation; preserve partial artifacts and record actual timestamps. Final manifest covers only this revision's members.

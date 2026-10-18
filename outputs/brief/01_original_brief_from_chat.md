# Original project brief — conversation archive

Source: the complete English brief supplied in the first user message of this conversation.
Archived on: 2026-10-13 (Asia/Shanghai).

No separate original PDF, Word document, or text file was located in the searched local project and document folders. This file preserves the user-supplied brief; it is not a newly issued assignment or an independently retrieved original attachment. The brief begins below.

---

# Agentic AI for adaptive virtual screening: create a one-month research prototype

Develop and implement two connected, tool-using LLM workflows: one that constructs retrospective screening benchmarks from public bioactivity evidence, and one that manages feedback-driven active-search campaigns on those benchmarks. Prioritize a functioning prototype with inspectable scientific decisions. The methods, software architecture and extent of target coverage are open design choices to develop. Both workflows should use intermediate evidence to choose subsequent tool calls and actions.

# Task 1 Discover and construct suitable benchmarks

Build an agent that searches sources such as PubChem BioAssay, ChEMBL and BindingDB, identifies candidate protein targets, and curates compound-level benchmarks. Define the endpoint and hit criteria; standardize structures and measurements; reconcile duplicates, conflicting records and censored values; retain source and assay provenance. Distinguish assay-defined hits from evidence of direct target binding. Establish qualification criteria using usable compound and class counts, chemical diversity and analogue redundancy, assay compatibility, and feasibility of feedback-driven search under a proposed initialization and query budget.

Prefer experimentally characterized positives and nonactives. Pooling assays is permitted with a justified interpretation. Where negative coverage is inadequate, propose a clearly identified decoy-augmented benchmark or reject the target. Distinguish measured outcomes, unknown activity and assigned decoy labels; examine construction biases [[1]](https://pmc.ncbi.nlm.nih.gov/articles/PMC6701836/). Rank qualifying datasets and select a tractable shortlist. Review and justify the initial criteria and consequential compromises during development and before campaign evaluation; reassess them in light of the results. Keep the compound pool and labels fixed within each campaign; document subsequent curation changes as a new benchmark version. Data availability determines suitability for retrospective evaluation, rather than biological target priority.

# Task 2 Implement agent managed active search

For each selected benchmark, develop an agent that uses computational screening tools and sequentially revealed outcomes to identify hits within a declared query budget. Each query reveals a stored compound-level benchmark outcome. Maximize distinct hits recovered, specify how initialization is budgeted, and account for computational costs separately. Campaigns may begin with zero-shot scoring from suitable target-general methods; subsequently revealed outcomes may support score calibration or combination, model updates and compound selection. Candidate policies include greedy predicted-hit selection, diversity-aware selection and nonmyopic Bayesian active search, such as efficient nonmyopic search [[2]](https://proceedings.mlr.press/v70/jiang17d.html). Justify the initialization, budget and feedback schedule.

Give the LLM consequential decision authority during the campaign: for example, choosing analyses or models, interpreting feedback, or revising the selection strategy. Use numerical tools for scoring, fitting and acquisition calculations. Record the information available, actions taken and rationale for decisions. Separate curation and campaign contexts, keeping unrevealed outcomes outside the campaign agent's accessible state and tools; provide feedback through a controlled query interface. A shared architecture may be used across targets, with decisions responsive to each campaign's evidence.

# Scope and evaluation

Evaluate hit recovery across queries, computational cost and failure modes. Include simple reference strategies and a focused comparison with a prescribed controller using the same tools, initial information and query budget to examine the contribution of agentic control. Interpret measured-outcome and decoy-based results according to their evidential limits. Use inspection and targeted experiments to demonstrate understanding of consequential data and modeling choices. Prioritize a working connection between the two tasks; justify limitations and incomplete features within the month.

# Deviation — C2 v2 runner hash

The pre-score lock `C2V2_ENV_LOCK.json` was written before the fifth proxy was fitted and locks the environment, public inputs, incumbent implementation, reference C2 v1 summary, and canonical feature/model/CV parameter specification. It does not contain a hash of `run_c2v2.py` itself. The public-output projection in that script was edited after the lock but before the first new score was computed; the feature extraction, model fitting, folds, metrics, and tier checks were not changed by that edit.

This is a provenance limitation. The runner's final SHA-256 is recorded in the C v2 manifest, but it must not be described as a pre-result code hash. The analysis remains post-exposure, and the exact code is available for review and rerun. No C3 campaign has been run; its configuration and runner will be locked before any C3 outcomes are generated.

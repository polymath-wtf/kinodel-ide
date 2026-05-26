# Render retry note

Observed workflow note for Kinodel renders:

- `render.py` may report a partial failure on the first pass when one job inside a batch fails, even after several jobs have already completed successfully.
- Do **not** treat that as a final failure or manually promote partial output early.
- Let the worker finish its built-in retry pass; it can resume from the worker result file and complete the remaining job(s).
- After the worker exits cleanly, run `copy_worker_result.py` to promote the final worker result into `render_results/*.json`.
- Then validate the promoted manifest before advancing or showing the next gate.

Practical implication: long image batches can appear stalled or noisy for minutes while still making progress. Prefer polling/waiting on the background process over guessing from intermediate stdout.
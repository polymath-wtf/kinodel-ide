# Upstream Edit-Fix Invalidation Notes

Session takeaway:
- After a user edits the main-frame brief or gives p4 edit-fix notes, do not trust the previous `render_results/main_frame_result.json` as a live source of truth.
- Re-run the affected render stage and promote the new worker result before showing the gate again.
- Likewise, after p7 edit-fix notes, re-render `story_frames` before any downstream video planning.

Observed behavior:
- `producer_step.py` can still surface a gate based on an older manifest if the upstream request file changed but the result manifest still parses as valid.
- The safe recovery path is: update the owned request artifact, rerun the stage, copy the worker result, then validate the new durable result manifest.

Practical rule:
- Upstream edit-fix => invalidate the affected downstream render result manually and rerender.
- Do not rely on the existence of an old manifest to mean it still matches the latest request.
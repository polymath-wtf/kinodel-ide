# Worker contract index

Architecture-only index. The executable contract for each worker lives in the owning skill. `pipeline-kinodel` does not duplicate specialist contracts because duplicated copies drift.

## Delegation base

Producer delegates creative/design stages using the static contract in:

- `producer-kinodel/references/delegated-design-stages.md`

That base contract defines the common subagent rules: load `handoff.stage.owner_skill`, read only `handoff.artifacts.read`, write exactly `handoff.artifacts.write`, preserve `project.id`, set `status=complete`, avoid provider runtime fields, and return only status.

## Owner contract map

| Goal | Owner skill | Owned artifact | Contract location |
| --- | --- | --- | --- |
| `p1_story` | `storytell-kinodel` | `story.json` | `storytell-kinodel/SKILL.md` |
| `p2_main_frame_plan` | `wardrobe-kinodel` | `wardrobe_request.json` | `wardrobe-kinodel/SKILL.md` |
| `p5_storyboard_plan` | `storyboard-kinodel` | `storyboard_requests.json` | `storyboard-kinodel/SKILL.md` |
| `p8_video_plan` | `filmmaker-kinodel` | `video_requests.json` | `filmmaker-kinodel/SKILL.md` |
| ReviewGate QC | `critic-kinodel` | optional `qc/*.json` | `critic-kinodel/SKILL.md` |
| `p10_montage` | `montage-kinodel` | `outputs/final.mp4` | `montage-kinodel/SKILL.md` |

## Synchronization rule

When a worker contract changes, update the owning `SKILL.md` first. Update this index only if the owner/artifact/goal mapping changes. Do not reintroduce long copied contracts here.

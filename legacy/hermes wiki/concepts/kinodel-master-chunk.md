---
title: Kinodel Master Chunk
author: null
created: 2026-05-10
updated: 2026-05-10
type: concept
tags: [kinodel, agent-architecture, context-engineering, workflow, render-queue, deprecated]
sources:
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/producer-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py
  - ~/.hermes/skills/kinodel/render-kinodel/scripts/fal.py
confidence: low deprecated
contested: true
contradictions:
  - Устарел, хз что с ним делать. либо обновлять либо придумать применение, ато сейчас это старый контекст.
---

# Kinodel Master Chunk

> Deprecated: use [[kinodel-final-chunk]] for new Kinodel productions.

`master_chunk.json` is the compact production ledger for new [[project-kinodel]] productions. 

## Core rule

> One production = one compact `master_chunk.json`; media binaries live in `outputs/`; embedding input is a derived summary.

This is a simplification cascade: the active pipeline needs one ledger with IDs, statuses, short shot cards, render job metadata, output refs, and sparse checkpoints. Heavy artifacts remain external and are referenced by path/URL.

## Canonical layout

```text
projects/<project_id>/v1/
  master_chunk.json
  outputs/
```

## Sections

```json
{
  "schema": "kinodel.master_chunk.v2",
  "project_id": "mem_sasha_01",
  "status": "draft|rendering|editing|released|blocked",
  "mode": {"autonomy": "auto", "manual_review": false},
  "brief": {},
  "pipeline": {},
  "story": {"logline": "", "shots": []},
  "qc": {"notes": []},
  "visual": {"style_anchor": "", "hero_in_location": {}},
  "render": {"jobs": [], "last_summary": null},
  "edit": {"timeline": [], "final_mp4": null},
  "embedding": {"summary": "", "updated_at": null},
  "history": []
}
```

## Size budget

The master chunk should stay small enough for cheap inspection and summarization. For a cinematic with 10 images and 10 video prompts, store 10 compact shot cards plus render job records and asset refs, not a pile of full prompt drafts and logs.

Store:

- **Stage ledger:** project ID, mode, current stage, completed stages, blocked reason.
- **Creative cards:** brief summary, logline, shot beat, duration, camera/motion summary, compact prompt digest.
- **Execution refs:** render job IDs, status URLs, output paths/URLs, final edit path.
- **Sparse checkpoints:** stage-boundary decisions and compact QC notes.

Do not store:

- **Full logs:** worker stdout, stack traces, full provider JSON responses.
- **Media payloads:** base64 images/video, verbose metadata dumps.
- **Every draft:** repeated prompt iterations, chat transcript, scratch reasoning.
- **Project-local tools:** ad-hoc scripts or glue code.

## Embedding view

The Gemini embedding target is not the raw master chunk. It is a compact derived view written into `embedding.summary` or generated from the ledger at archive/release time. Keep it within the useful 8k-token budget by including only intent, final shot cards, important asset refs, final result, and lessons learned.

## Agent ownership

- **Producer** owns orchestration, validation, pipeline progression, and compact ledger hygiene.
- **Storytell** writes `story` only.
- **Critic** writes compact `qc.notes[]` diffs only.
- **Wardrobe** writes `visual` and anchor render job.
- **Storyboard** writes shot image fields and i2i jobs.
- **Filmmaker** writes shot motion fields and i2v jobs.
- **Render** updates `render.jobs[]` and output refs.
- **Montage** writes `edit.timeline[]` and `edit.final_mp4`.

## Autonomy policy

Autonomy is not a ReviewGate timeout. If `mode.manual_review` is false, [[agent-producer-kinodel]] continues through the route and records compact checkpoints. Manual review is used only when requested, when ambiguity blocks safe progress, or when an error/provider/budget risk occurs.

## Render contract

Render jobs live inside `master_chunk.render.jobs[]`. `render-kinodel/scripts/fal.py --master-chunk ...` reads pending jobs, calls providers, downloads outputs to `outputs/`, then writes `output_path`, `output_url`, and `render.last_summary` back into the master chunk.

Legacy `render_queue.jsonl` remains compatibility-only for old projects.

## See also

- [[pipeline-kinodel]] — live skill framework route.
- [[cinematic-pipeline]] — broader production stage map.
- [[agent-render-kinodel]] — render worker entity.
- [[kinodel-render-requests]] — provider payload templates.

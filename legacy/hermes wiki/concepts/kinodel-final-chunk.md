---
title: Kinodel Final Chunk
created: 2026-05-10
updated: 2026-05-11
type: concept
tags: [kinodel, context-engineering, workflow, patch]
sources:
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/producer-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/kinodel-project-layout/SKILL.md
  - ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py
confidence: high
contested: false
contradictions: []
---

# Kinodel Final Chunk

`final_chunk.json` is the durable final memory artifact for new [[project-kinodel]] productions. It describes the final cinematic, not the process that produced it. Generation intent lives separately in [[kinodel-brief]].

## Core rule

> Save the finished cinematic, not the pipeline.

This replaces the over-engineered [[kinodel-master-chunk]] ledger idea. Runtime prompts, render requests, logs, provider responses, QC notes, and intermediate alternatives are disposable scratch.

## Schema

```json
{
  "schema": "kinodel.final_chunk.v1",
  "project_id": "mem_sasha_01",
  "story": "Short final story text.",
  "hook": "Why this cinematic is worth watching.",
  "main_frame": "outputs/main_frame.png",
  "story_images": [
    "outputs/shot_01.png",
    "outputs/shot_02.png"
  ],
  "conclusion": "What the final cinematic means / why it works."
}
```

## What belongs here

- **story:** final story summary only.
- **hook:** final hook only.
- **main_frame:** one canonical main frame reference.
- **story_images:** 1-5 final image references.
- **conclusion:** compact final interpretation/result/lesson.

## What does not belong here

- **Process state:** stage, completed stages, blocked reason.
- **Execution metadata:** job IDs, provider status URLs, request IDs.
- **Drafts:** prompt iterations, QC notes, failed alternatives.
- **Logs:** worker stdout, stack traces, provider JSON responses.
- **Media payloads:** base64 images/video or verbose metadata.

## Runtime render handoff

Render work uses temporary request/result files, not durable project state. [[agent-render-kinodel]] may receive a short-lived request file and write a result file with `output_path` / `output_url`. Producer then selects only the final `main_frame`, story images, optional video clips/final video, and conclusion for `final_chunk.json`.

Legacy `master_chunk.json`, `render_queue.jsonl`, and provider status fields are compatibility only and must not be used as the new memory model.

## Embedding use

For Gemini embedding, embed `brief.json` + `final_chunk.json` plus selected referenced media, not a process ledger. This keeps the useful content within the 8k-token budget and avoids preserving production noise.

## See also

- [[pipeline-kinodel]] — pipeline that produces the final chunk.
- [[kinodel-brief]] — production intent separated from final memory.
- [[kinodel-master-chunk]] — deprecated ledger concept superseded by this page.
- [[kinodel-render-requests]] — provider payload templates used only as runtime scratch.

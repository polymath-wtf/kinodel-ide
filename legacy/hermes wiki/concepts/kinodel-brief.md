---
title: Kinodel Brief Contract
created: 2026-05-11
updated: 2026-05-25
type: concept
tags: [kinodel, workflow, context-engineering, agent-architecture]
sources:
  - ~/.hermes/skills/kinodel/pipeline-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/producer-kinodel/SKILL.md
  - ~/.hermes/skills/kinodel/producer-kinodel/references/brief-start.md
  - ~/.hermes/skills/kinodel/producer-kinodel/references/brief-gate-defaults.md
  - ~/.hermes/skills/kinodel/pipeline-kinodel/templates/brief.json
  - ~/.hermes/skills/kinodel/kinodel-project-layout/SKILL.md
  - ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py
confidence: high
contested: false
contradictions: []
---

# Kinodel Brief Contract

`brief.json` is the durable production-intent artifact for new [[project-kinodel]] productions. It is created only after a pre-production BriefGate where [[agent-producer-kinodel]] confirms the user's creative vibe and production format. It stores the user's raw creative vibe plus extracted technical generation parameters, carries the project identity, and is created before rendering starts. It stays separate from [[kinodel-final-chunk]], which describes the finished cinematic only.

## Core rule

> Confirm vibe + format first; then store `user_vibe` and generation parameters in `brief.json`; store final memory in `final_chunk.json`.

This fixes the goose-meme test failure mode where the agent interpreted “3 shots” as image-only because duration, shot count, and audio policy were not written into a durable contract. Video is a normal Kinodel stage after story images, not a separate `enabled` flag.

## Start brief

`producer-kinodel/references/brief-start.md` is the canonical user-facing intake card for the first BriefGate. It prevents [[agent-producer-kinodel]] from hallucinating a new brief shape each run.

The start card captures:

- **Vibe:** raw user idea, preserved as `user_vibe`.
- **Story seed:** protagonist, situation, desire, obstacle, and emotional turn.
- **Hook:** first-second visual question.
- **Intrigue:** unresolved tension that keeps the viewer watching.
- **Characters:** 1–3 role/trait/visual anchors.
- **World/style:** location, era, mood, genre, and references.
- **Ending:** final beat, reveal, punchline, or open loop.
- **Format:** platform, aspect ratio, shot count, image/video defaults, workflow/provider, and audio policy.

This card is not a durable artifact. After approval, Producer folds the approved creative notes into `user_vibe` and writes only the canonical `brief.json` fields. Story expansion remains owned by [[agent-storytell-kinodel]], and render/provider payloads remain owned by [[agent-render-kinodel]].

## Schema

```json
{
  "schema": "kinodel.brief.v1",
  "project_id": "goose-meme",
  "status": "complete",
  "user_vibe": "Meme about a goose stealing bread from a cyberpunk monk.",
  "platform": "reels",
  "aspect_ratio": "9:16",
  "shot_count": 3,
  "image": {
    "resolution": "1K",
    "format": "png",
    "width": 1024,
    "height": 1792
  },
  "video": {
    "workflow": "i2v",
    "flow": "i2v",
    "seconds_per_shot": "4s",
    "resolution": "480p",
    "enable_audio": false,
    "width": 480,
    "height": 854
  },
  "provider": "comfyui",
  "provider_image": "local-comfyui:img2img_klein",
  "provider_edit": "local-comfyui:img2img_klein",
  "provider_video": "local-comfyui:img2vid_wan_lora",
  "provider_flf2v": "fal:veo31_lite_flf2v",
  "defaults": {
    "provider": "comfyui",
    "provider_image": "local-comfyui:img2img_klein",
    "provider_edit": "local-comfyui:img2img_klein",
    "provider_video": "local-comfyui:img2vid_wan_lora",
    "provider_flf2v": "fal:veo31_lite_flf2v"
  }
}
```

## Behavior

- **BriefGate first:** [[agent-producer-kinodel]] must ask/confirm vibe + format, end the turn, and wait for the user's answer before project initialization.
- **Project identity:** `project_id` is mandatory and every downstream durable JSON artifact must match it.
- **User vibe:** `user_vibe` is written by Producer from the user's original creative request. Keep technical parameters out of it.
- **No brief drift:** do not add ad-hoc top-level fields such as `concept`, `output_mode`, `inferred`, or `video.enabled`.
- **Video stage:** [[agent-filmmaker-kinodel]] runs after story images as part of the canonical Kinodel route.
- **Edits:** if the user changes aspect ratio, frame count, duration, or audio, Producer updates `brief.json` first and invalidates only downstream media affected by that field.
- **Defaults:** Producer may offer default values for missing technical parameters, but defaults are suggested BriefGate choices, not permission to skip asking.

## What does not belong here

- Provider `request_id`, `status_url`, `response_url`, worker logs, retries, cost, or debug payloads.
- Story drafts, critic notes, prompt alternatives, or generated media metadata.
- The start-card slots as separate durable JSON fields; they belong inside approved `user_vibe` until specialist artifacts expand them.
- Final interpretation/conclusion; that belongs to [[kinodel-final-chunk]].

## See also

- [[pipeline-kinodel]] — route that consumes `brief.json`.
- [[kinodel-render-requests]] — render request contract using brief defaults.
- [[agent-producer-kinodel]] — owner of intake and brief edits.

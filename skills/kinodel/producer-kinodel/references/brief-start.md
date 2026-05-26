# Brief start contract

Use this reference when starting a new Kinodel project or normalizing a fragmented user idea into the first BriefGate.

## Purpose

Producer must not invent a different brief shape on every run. Build one compact start brief, show it to the user, then persist only the canonical `brief.json` fields after approval.

## Intake card

Ask for or infer these fields in this exact order. The user-facing brief question should show all 9 slots, but it may invite the user to answer partially; missing fields become explicit assumptions in the final preview.

1. `user_vibe` — the user's raw creative idea in one compact paragraph.
2. `story_seed` — protagonist, situation, desire, obstacle, and emotional turn.
3. `hook` — the first-second attention grabber or visual question.
4. `intrigue` — what stays unresolved until the last shot.
5. `characters` — names/roles, key traits, visual anchors, and relationships.
6. `world` — location, era, mood, genre, and style references.
7. `ending` — final beat, punchline, reveal, or open loop.
8. `format` — platform, aspect ratio, shot count, duration, quality. Show the default plus alternatives inline: `square/1:1, 3 frames, 1K images, 480p video, 4s per shot` (other options: `reels/9:16`, `widescreen/16:9`, custom shot count, `720p/1080p` when supported).
9. `workflow` — provider, image flow, video flow, audio policy. Show the default plus alternatives inline: `provider=comfyui`, `image flow=img2img`, `video flow=i2v`, `audio=off` (other video flows: `t2v`, `flf2v`; other providers: `fal.ai`, `openrouter` when the selected pipeline/provider profile supports it).

If the user gives only a vibe line, do not interrogate them for every creative field. Fill missing creative slots as lightweight assumptions inside the BriefGate preview and ask for approval or edits.

Treat terse style-only prompts in any language the same way (e.g. `Meme in comics style`): map them to `user_vibe`, infer a coherent `story_seed`/`hook`/`characters`/`world`/`ending`, and show the full 9-field preview before initialization.

If the user answers only some fields, do not create the project yet. Merge the answers into the draft, infer the rest, then show the final BriefGate preview for approval.

## First brief prompt shape

For a new project, use a compact user-facing prompt like this instead of a weak one-line workflow/provider question:

```text
Дай brief по 9 пунктам — можно отвечать частично, я додумаю пустое и покажу финальную карточку на approve:
1. Vibe / идея:
2. Story seed: герой, ситуация, желание, препятствие, эмоциональный поворот:
3. Hook: первый кадр / вопрос:
4. Intrigue: что держит до конца:
5. Characters: роли, черты, визуальные якоря:
6. World/style: место, эпоха, жанр, референсы:
7. Ending: финальный бит / панчлайн:
8. Format: default square 1:1, 3 frames, 1K images, 480p video, 4s/shot (варианты: reels 9:16, widescreen 16:9, custom shots, 720p/1080p)
9. Workflow: default provider=comfyui, image=img2img, video=i2v, audio off (варианты flow: t2v/flf2v; provider: fal.ai/openrouter)
```

For very terse user input already present (e.g. `мем про кота`), Producer may skip re-asking the whole form and directly show a filled final BriefGate preview with assumptions, but still must include all 9 fields and wait for approval before initialization.

## BriefGate preview shape

Always show the user this compact card before project initialization. This is mandatory even when the user answered only part of the intake and Producer inferred the rest.

```text
Brief start — final approval
- Vibe: <raw user idea>
- Story seed: <protagonist wants X, faces Y, turns into Z>
- Hook: <opening visual/question>
- Intrigue: <what keeps the viewer watching>
- Characters: <1-3 compact character anchors>
- World/style: <location + genre + visual language>
- Ending: <final beat>
- Format: <platform>, <aspect_ratio>, <shot_count> frames, <image quality/dimensions>, <video quality/dimensions>, <seconds per shot> (default shown; alternatives if relevant)
- Workflow: provider=<comfyui default>, image flow=<img2img default>, video flow=<i2v default>, audio=<off default> (options: t2v/flf2v; providers: fal.ai/openrouter when supported)
- Assumptions: <only list fields Producer inferred from missing user answers>

Reply:
A — approve, create project, and continue to the first hard ReviewGate
B — auto-tighten the brief
C — edit with your notes
D — stop
```

The card is a user-facing planning aid, not a separate durable artifact. `A`, `approve`, `go`, `го`, `дальше`, or an equivalent continuation after this card counts as approval to create the project and continue deterministic pipeline execution to the first hard stop. Before this card is shown, those words only authorize default filling and must not initialize the project.

## Persisted `brief.json`

After approval, write only the canonical production fields. The approved 9-field creative intake must be persisted as first-class `brief.json` fields, not collapsed into `user_vibe`:

```json
{
  "schema": "kinodel.brief.v1",
  "project_id": "project_id",
  "status": "complete",
  "user_vibe": "Raw user creative idea in one compact paragraph.",
  "story_seed": "Protagonist, situation, desire, obstacle, and emotional turn approved in BriefGate.",
  "hook": "First-second attention grabber or visual question.",
  "intrigue": "What stays unresolved until the last shot.",
  "characters": [
    {
      "name": "Character name or role",
      "role": "story role",
      "traits": "key traits",
      "visual_anchor": "visual identity anchor",
      "relationship": "relationship to other characters if relevant"
    }
  ],
  "world": "Location, era, mood, genre, and style references.",
  "ending": "Final beat, punchline, reveal, or open loop.",
  "brief_assumptions": [
    "Visible assumptions Producer inferred for missing user answers before approval."
  ],
  "platform": "square",
  "aspect_ratio": "1:1",
  "shot_count": 3,
  "image": {
    "resolution": "1K",
    "format": "png",
    "width": 1024,
    "height": 1024
  },
  "video": {
    "workflow": "i2v",
    "flow": "i2v",
    "seconds_per_shot": "4s",
    "resolution": "480p",
    "enable_audio": false,
    "width": 480,
    "height": 480
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

Use `pipeline-kinodel/templates/brief.json` and `references/brief-gate-defaults.md` as the source of truth for current default values.

## Defaulting rules

- Default platform/aspect to square `1:1` unless the user asks for reels, shorts, TikTok, YouTube, widescreen, story, loop, or another format.
- Default `shot_count=3` for short cinematic/social clips unless the user specifies another count.
- Default image/video dimensions from the current Kinodel resolution guide and brief template; do not invent unsupported sizes.
- Default video flow/provider according to `references/brief-gate-defaults.md` unless the user chooses another supported workflow.
- Treat “на твоё усмотрение”, “без разницы”, “остальное хз”, or equivalent before the final BriefGate as permission to fill defaults, not permission to initialize; after the final BriefGate it may count as approval of the displayed card.

## Forbidden brief drift

Do not add ad-hoc top-level fields such as `concept`, `output_mode`, `inferred`, `video.enabled`, provider job IDs, queue state, prompt drafts, critic notes, render logs, or final-memory fields.

Do not create the project directory until the user approves the final BriefGate card or gives an equivalent continuation such as `go` after seeing that card. After approval, continue deterministic pipeline execution; do not add a soft stop after layout creation.

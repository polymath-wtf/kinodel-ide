# Brief start contract

Use this reference when starting a new Kinodel project or normalizing a fragmented user idea into the first BriefGate.

## Purpose

Producer must not write the story. Producer only captures the user's intent and technical production choices, shows a minimal approval card, then initializes the project so `storytell-kinodel` can author the hook, intrigue, world, style, ending, and shot beats.

## Simplification cascade

Old shape:

```text
Producer asks/invents 9 creative fields → Producer effectively writes a story → Storytell receives already-shaped mediocre story
```

New shape:

```text
Producer captures 4 things → brief.json → storytell owns narrative creation
```

The single principle: **BriefGate captures constraints; Storytell creates story.**

## Minimal intake card

Ask for or infer only these fields:

1. `user_vibe` — the user's raw creative vibe/idea in their own words. Keep it compact; do not polish it into a plot.
2. `characters` — user-specified characters/subjects/roles/visual anchors. If absent, write a visible assumption such as `inferred by storytell from user_vibe` instead of inventing a cast.
3. `feature` — the must-keep core feature/gimmick/object/action/style constraint the user cares about most. Examples: `neon cat ambulance`, `VHS kung fu cat`, `digital anomaly, not literal insect`, `one-shot chase`, `sad robot nanny`.
4. `workflow` — production format and render workflow: platform/aspect ratio, shot count, image/video quality, seconds per shot, provider, image flow, video flow, audio policy.

Do not ask for or invent `story_seed`, `hook`, `intrigue`, `world`, `ending`, or detailed `style` in BriefGate. Those are `storytell-kinodel` responsibilities after project init.

## First brief prompt shape

For a new project, use a compact prompt like this:

```text
Дай короткий Kinodel brief — можно одной строкой:
1. Vibe / идея: что должно ощущаться?
2. Characters / subjects: кто или что в кадре?
3. Feature / must-keep: главная фишка, объект, действие или стиль, который нельзя потерять?
4. Workflow / format: default square 1:1, 3 frames, 1K images, 480p video, 4s/shot, comfyui, image=i2i, video=i2v, audio off
   варианты: reels 9:16, widescreen 16:9, custom shots, 720p/1080p, fal.ai, flf2v, audio on

Если дашь только идею, я НЕ буду придумывать историю в BriefGate — зафиксирую минимальный brief и передам историю в storytell.
```

For terse input already present (e.g. `неоновый кот-скорая`), Producer may skip re-asking the form and show the minimal BriefGate preview with visible defaults. Do not expand it into a plot.

## BriefGate preview shape

Always show this compact card before project initialization:

```text
BriefGate — minimal production brief
- Project: <project_id candidate>
- Vibe: <raw user idea / vibe, minimally normalized>
- Characters / subjects: <user-provided anchors or "storytell will infer from vibe">
- Feature / must-keep: <core gimmick/object/action/style constraint>
- Format: <platform>, <aspect_ratio>, <shot_count> frames, <image quality/dimensions>, <video quality/dimensions>, <seconds per shot>
- Workflow: provider=<comfyui default>, image flow=<i2i/img2img default>, video flow=<i2v default>, audio=<off default>
- Story ownership: storytell-kinodel will create hook, intrigue, world/style, ending, and shot beats after approval.
- Assumptions: <only technical/default assumptions and missing minimal fields; no plot inventions>

Reply:
A — approve, create project, and continue to the first hard ReviewGate
C — edit brief/format/workflow
D — stop
```

`A`, `approve`, `go`, `го`, `дальше`, or equivalent continuation after this card counts as approval. Before this card is shown, those words only authorize default filling and must not initialize the project.

## Persisted `brief.json`

After approval, write only the minimal production intent plus technical defaults:

```json
{
  "schema": "kinodel.brief.v1",
  "project_id": "project_id",
  "status": "complete",
  "user_vibe": "Raw user creative idea/vibe, minimally normalized.",
  "characters": [
    {
      "name": "User-provided character/subject or role",
      "description": "Only user-provided traits/anchors; do not invent full backstory."
    }
  ],
  "feature": "The must-keep core gimmick/object/action/style constraint.",
  "brief_assumptions": [
    "Technical/default assumptions Producer inferred before approval; no plot inventions."
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

Legacy briefs may still contain `story_seed`, `hook`, `intrigue`, `world`, or `ending`; specialists may read them as optional hints. New BriefGate must not generate them.

Use `pipeline-kinodel/templates/brief.json` and `references/brief-gate-defaults.md` as the source of truth for current default values.

## Defaulting rules

- Default platform/aspect to square `1:1` unless the user asks for reels, shorts, TikTok, YouTube, widescreen, story, loop, or another format.
- Default `shot_count=3` for short cinematic/social clips unless the user specifies another count.
- Default image/video dimensions from the current Kinodel resolution guide and brief template; do not invent unsupported sizes.
- Default video flow/provider according to `references/brief-gate-defaults.md` unless the user chooses another supported workflow.
- Treat “на твоё усмотрение”, “без разницы”, “остальное хз”, or equivalent before the final BriefGate as permission to fill technical defaults, not permission to initialize; after the final BriefGate it may count as approval of the displayed minimal card.

## Forbidden brief drift

Do not add ad-hoc top-level fields such as `concept`, `output_mode`, `inferred`, `video.enabled`, provider job IDs, queue state, prompt drafts, critic notes, render logs, or final-memory fields.

Do not create the project directory until the user approves the minimal BriefGate card or gives an equivalent continuation such as `go` after seeing that card. After approval, continue deterministic pipeline execution; do not add a soft stop after layout creation.

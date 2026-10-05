# Agent Prompts

Application system instructions live here; the build loads each enabled agent's system prompt from `.agents/<agent>/system.md`. Implementation contracts live in [docs/agents](../docs/agents/README.md). These are application prompts, not an OpenCode agent registry.

| Agent | Instructions | Scope |
|---|---|---|
| Storytell | [system.md](storytell/system.md) | MVP: simple story and ordered shot actions |
| Wardrobe | [system.md](wardrobe/system.md) | MVP: reusable visual anchors and image prompts |
| Storyboard | [system.md](storyboard/system.md) | MVP: one start-frame image prompt per shot |
| Filmmaker | [System prompt](filmmaker/system.md) | Authored: silent exact-start img2vid or ordered-reference ref2vid; not runtime-integrated |
| Critic | [system.md](critic/system.md) | Post-MVP micro-context; not enabled |
| Episode | [system.md](episode/system.md) | Future micro-context; not enabled |
| Season | [system.md](season/system.md) | Future micro-context; not enabled |
| Muse | [system.md](muse/system.md) | Future micro-context; not enabled |

Load only the selected agent's system prompt plus its response schema and prepared task content. This index and domain/backend docs are not model context. Supply usable text/images and labelled reference aliases, not bare storage IDs. Revision input includes the previous complete result and relevant feedback.

Runtime activation, 3 October: **Storytell only** is integrated into the bounded live text graph `kinodel.live-story` v1. Its exact system text/digest, response schemas and model profile are frozen on start; the prepared operation pins direct inputs and relevant discussion before HTTP. The deterministic `kinodel.internal-story` never loads these instructions. Wardrobe/Storyboard/Filmmaker prompts remain authored but unintegrated; approval in either current Story graph ends that text execution. Evidence and remaining activation acceptance: [Local MVP step 3](../docs/roadmap-mvp.md#remaining-steps).

Preparation, 5 October: Wardrobe's example binds both portrait and background parents before the sheet. Filmmaker's single `system.md` matches MotionPlanV2/FilmmakerInputV2. Future activation must freeze prompt/schema/input projection and graph identity together under the [ComfyUI roadmap](../docs/roadmap-comfyui.md#3-production-settings-и-профильные-ограничения). No Filmmaker execution or video capability is claimed.

Image prompts include compact Krea-derived guidance; Filmmaker includes the applicable H3 motion principles. Source/adaptation notes live in their domain docs. Pin these instruction versions with a compatible generation profile; do not append the full source guides or treat these drafts as proof of provider support. Future profiles may supply their own bounded guidance.

Render, montage and result saving are tools/services, not personas. Schema implementation, runtime registration and representative model/provider checks remain part of [Local MVP](../docs/roadmap-mvp.md).

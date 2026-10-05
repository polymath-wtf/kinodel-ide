# Agent Prompts

Application system instructions live here; the build loads each enabled agent's system prompt from `.agents/<agent>/system.md`. Implementation contracts live in [docs/agents](../docs/agents/README.md). These are application prompts, not an OpenCode agent registry.

| Agent | Instructions | Scope |
|---|---|---|
| Storytell | [system.md](storytell/system.md) | MVP: simple story and ordered shot actions |
| Wardrobe | [system.md](wardrobe/system.md) | Typed anchor plan, frozen OpenRouter adapter and durable operation/storage implemented; graph activation pending |
| Storyboard | [system.md](storyboard/system.md) | MVP: one start-frame image prompt per shot |
| Filmmaker | [System prompt](filmmaker/system.md) | Authored: silent exact-start img2vid or ordered-reference ref2vid; not runtime-integrated |
| Critic | [system.md](critic/system.md) | Post-MVP micro-context; not enabled |
| Episode | [system.md](episode/system.md) | Future micro-context; not enabled |
| Season | [system.md](season/system.md) | Future micro-context; not enabled |
| Muse | [system.md](muse/system.md) | Future micro-context; not enabled |

Load only the selected agent's system prompt plus its response schema and prepared task content. This index and domain/backend docs are not model context. Supply usable text/images and labelled reference aliases, not bare storage IDs. Revision input includes the previous complete result and relevant feedback.

Runtime activation: **Storytell only** is integrated into the bounded live text graphs `kinodel.live-story` v1/v2. Its exact system text/digest, response schemas and model profile are frozen on start; the prepared operation pins direct inputs and relevant discussion before HTTP. The deterministic `kinodel.internal-story` never loads these instructions. Wardrobe's adapter and durable operation/storage exist; graph activation is pending for Wardrobe/Storyboard/Filmmaker. Approval in current Story graphs ends that text execution. Evidence and remaining activation acceptance: [Local MVP step 3](../docs/roadmap-mvp.md#remaining-steps).

Preparation, 6 October: Wardrobe uses `WardrobeInputV1`/StoryV1/V2 and returns a creative draft; the adapter supplies exact refs in `VisualAnchorPlanV1`. The first capability binds portrait and background parents before the sheet. Frozen requests, image evidence validation and durable attempts/repair/immutable commit/replay are implemented. New scoped graph identity/handoff activation and live verification remain next. Filmmaker's single `system.md` matches MotionPlanV2/FilmmakerInputV2; no Filmmaker execution or video capability is claimed. [Wardrobe contract](../docs/agents/wardrobe.md).

Image prompts include compact Krea-derived guidance; Filmmaker includes the applicable H3 motion principles. Source/adaptation notes live in their domain docs. Pin these instruction versions with a compatible generation profile; do not append the full source guides or treat these drafts as proof of provider support. Future profiles may supply their own bounded guidance.

Render, montage and result saving are tools/services, not personas. Schema implementation, runtime registration and representative model/provider checks remain part of [Local MVP](../docs/roadmap-mvp.md).

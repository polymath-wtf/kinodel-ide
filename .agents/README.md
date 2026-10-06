# Agent Prompts

Application system instructions live here; the build loads each enabled agent's system prompt from `.agents/<agent>/system.md`. Implementation contracts live in [docs/agents](../docs/agents/README.md). These are application prompts, not an OpenCode agent registry.

| Agent | Instructions | Scope |
|---|---|---|
| Storytell | [system.md](storytell/system.md) | MVP: simple story and ordered shot actions |
| Wardrobe | [system.md](wardrobe/system.md) | W1–W7 complete: typed anchor plan, frozen OpenRouter adapter, durable scoped runtime/API, W6 live acceptance and W7 explicit UI start/exact inputs/config/copyable saved plan/offline reopen with mocked HTTP; anchor rendering/review pending |
| Storyboard | [system.md](storyboard/system.md) | MVP: one start-frame image prompt per shot |
| Filmmaker | [System prompt](filmmaker/system.md) | Authored: silent exact-start img2vid or ordered-reference ref2vid; not runtime-integrated |
| Critic | [system.md](critic/system.md) | Post-MVP micro-context; not enabled |
| Episode | [system.md](episode/system.md) | Future micro-context; not enabled |
| Season | [system.md](season/system.md) | Future micro-context; not enabled |
| Muse | [system.md](muse/system.md) | Future micro-context; not enabled |

Load only the selected agent's system prompt plus its response schema and prepared task content. This index and domain/backend docs are not model context. Supply usable text/images and labelled reference aliases, not bare storage IDs. Revision input includes the previous complete result and relevant feedback.

Runtime activation: **Storytell** is integrated into `kinodel.live-story` v1/v2 and the new scoped `kinodel.story-wardrobe` v1, which runs **Wardrobe** after exact nonterminal Story approval and completes with a valid saved plan. System text/digests, schemas and model profiles are frozen; operations pin inputs before HTTP. The deterministic `kinodel.internal-story` never loads these instructions. Historical internal/live Story routes retain approve → END. «Новая история» explicitly starts Story → Wardrobe; live mode uses configured OpenRouter. W5 technical, W6 live/offline and W7 UI acceptance are complete; W7 used mocked HTTP, not new paid browser generation. Step 3 is closed; next is ComfyUI saved-plan handoff. Storyboard/Filmmaker activation and anchor rendering/review remain pending: [Local MVP step 3](../docs/roadmap-mvp.md#wardrobe-backend), [W7 evidence](../test-results/README.md#wardrobe-w7-ui-integration--6-october-2026).

Preparation, 6 October: Wardrobe uses `WardrobeInputV1`/StoryV1/V2 and returns a creative draft; the adapter supplies exact refs in `VisualAnchorPlanV1`. The first capability binds portrait and background parents before the sheet. W1–W7 are complete: frozen requests, image evidence validation, durable attempts/repair/immutable commit/replay, scoped graph handoff/settlement/blocked controls, technical recovery, live/offline acceptance and shared UI saved-plan inspection/copying. Step 3 is closed; rendering remains pending. Filmmaker's single `system.md` matches MotionPlanV2/FilmmakerInputV2; no Filmmaker execution or video capability is claimed. [Wardrobe contract](../docs/agents/wardrobe.md).

Image prompts include compact Krea-derived guidance; Filmmaker includes the applicable H3 motion principles. Source/adaptation notes live in their domain docs. Pin these instruction versions with a compatible generation profile; do not append the full source guides or treat these drafts as proof of provider support. Future profiles may supply their own bounded guidance.

Render, montage and result saving are tools/services, not personas. Schema implementation, runtime registration and representative model/provider checks remain part of [Local MVP](../docs/roadmap-mvp.md).

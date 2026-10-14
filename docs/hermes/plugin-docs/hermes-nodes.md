# Ноды и контракты этапов

**Статус:** фиксированный cinematic target, не исполняемая Hermes schema. Storyboard и Filmmaker здесь описаны для будущей реализации, не как развёрнутые stages.

Ноды представляют **Agent / Tool / Review**. Agent создаёт творческое описание; tool выполняет эффект без обязательного LLM; review фиксирует решение человека. Это UI-роли, не требование трёх runtime-классов или child на каждую ноду. Предлагаемое отображение на native tasks — [архитектура](hermes-kinodel-architecture.md).

## Контракты этапов

Все входы — exact pinned revisions с проверенной доступностью и требуемыми approvals. Нужные bodies/text/media передаются через verified host path, не только IDs. Таблица показывает логические outputs, не новые API types.

| Этап / тип | Обязательные входы и контекст | Результат / условие перехода |
|---|---|---|
| Brief / автор | Идея, references/characters, vibe, shot count/duration, aspect/size, image/video profiles, video mode и разрешённые настройки | Неизменяемый submitted brief; без обязательного Producer/brief gate |
| Storytell / agent | Brief, bounded narrative canon/Bio выбранных персонажей и явно выбранное вдохновение | Story: hook, narrative, ordered shots с stable keys, subjects, action, state_before/state_after и generated cast |
| Story review / человек | Exact полная Story revision | Явный approval этой story либо feedback Storytell |
| Wardrobe / agent | Brief, approved Story/cast, выбранные appearance/style projections и доступное labelled image evidence, prompt guidance/capabilities | Provider-neutral compact V2 `wardrobe_plan`: ordered `batch_prompt` |
| Anchor generation / tool | Exact V2 plan, frozen image settings, exact earlier-unit refs | Candidates всех required anchor units + originals; не approval |
| Anchor review / человек | Complete set, plan, exact parent lineage | Один compatible candidate/unit и approval полного `anchor_frames` |
| Storyboard / agent | Brief, approved Story, V2 plan + approved anchors, appearance/continuity и image guidance | `storyboard_plan`: один opening-frame prompt/shot, роли anchors и объявленные earlier-frame dependencies |
| Frame generation / tool | Exact plan, selected anchors/required earlier frames, frozen image settings | Complete frame candidates, ключи/порядок как у Story |
| Frame review / человек | Complete frames + supporting plan/input lineage | Selected/approved `story_frames` либо feedback Storyboard |
| Filmmaker / agent | Brief/mode/duration, approved Story/frames; в optional ref2vid заранее проверенный per-shot pin совместимых approved portrait/sheet; motion/continuity guidance | `video_plan`: один continuous silent clip/shot, motion/camera prompt и mode-specific inputs |
| Video generation / tool | Exact video plan, frames/required anchors, mode-compatible provider settings | Complete clip candidates, без пропущенных shots |
| Video review / человек | Complete clips + plan/input lineage | Selected/approved `shot_videos` либо feedback Filmmaker |
| Montage / tool | Все approved clips в Story-порядке, output settings | Простые склейки full clips, объявленная нормализация, ffmpeg + ffprobe; verified silent final MP4 |

Четыре reviews можно показывать на карточках соответствующих результатов. Планы — проверяемая provenance, **не отдельные creative HITL**; дополнительные gates допустимы только как будущий явный выбор автора. Final technical completion не означает дополнительный human approval. При правке в рамках этапа сохраняются ключи соответствующих shots/units; нельзя переиспользовать их для другого смысла.

## Wardrobe V2: минимальный точный набор

- Каждая task содержит `unit_key, use_case, workflow, subject_ids, image_prompt, references`; каждый reference — `source, role`. Visual direction живёт в полном prompt, provider payload — в adapter.
- Targets: выбранные characters, если selection непустой; иначе generated cast утверждённой Story; иначе declared subjects; иначе N=0. Остальные персонажи Story не создают дополнительные targets.
- На каждого target один portrait (`hero-face`, txt2img без render refs) и один sheet (`hero-sheet`, img2img); плюс **одна общая character-free location**, txt2img без refs: **2N+1**, при N=0 только location.
- Sheet использует ровно два отдельных earlier-unit image inputs в порядке `[portrait, background]`, не коллаж. Stable unit keys уникальны; list order — execution order. Self/forward/missing refs запрещены; exact parent candidate IDs/digests фиксируются до child submit.
- После генерации — один review полного набора. Изменение portrait/location требует нового dependent sheet; нельзя смешивать выбранные parents с листом другой lineage.

## Storyboard и Filmmaker

Storyboard изображает **начало**, согласованное со `state_before`, а не уже завершённое `state_after`. По одному frame на каждый Story shot, те же keys/order. Required anchors связываются по ролям identity/body/environment; разрешены заранее объявленные earlier-frame refs. Provider mapping должен доказанно вместить все ordered refs; нет скрытого txt2img/single-image fallback.

Filmmaker развивает действие внутри одного непрерывного немого clip, без внутренних склеек/музыки/диалогов. **Базовый mode — `img2vid`**: exact selected frame — start image. Optional `ref2vid` требует проверенной provider support и явной совместимой portrait/sheet pair для каждого shot в approved anchors; ordered inputs `[storyboard_frame, portrait, character_sheet]`, без отдельного background и **без обещания frame 0**.

До вызова Filmmaker и provider сохранить/проверить per-shot pin: `shot_key`, exact selected frame ref/digest, `subject_id`, approved anchor-set ref/revision/digest и точные portrait/sheet unit keys, selected candidate refs/digests. Оба anchor принадлежат одному явно указанному subject, sheet соответствует выбранному portrait и его сохранённой parent lineage. Агент получает готовую привязку, не выбирает identity сам.

При **N=0**, отсутствии compatible approved pair или неразрешённой многоперсонажной привязке `ref2vid` недоступен **до submit**. Story может иметь несколько персонажей; ограничение относится к shot и поддержке обязательного multi-character conditioning выбранным mode. Неподдержанное conditioning блокирует mode, а не сокращает cast/refs. Нельзя auto-pick identity, drop required refs или молча перейти на img2vid. Profile/mode, число и длительность shots не меняются моделью.

Generic image refs/aspect ratio и video `reference_image_urls` не доказывают нужный role mapping. Video example маршрутизирует по `image_url`, а docs допускают clamping duration/size: adapter обязан проверить effective settings и отказать несовместимой подмене до заказа.

## Четыре специалиста и skills

| Специалист | Подготавливаемая craft guidance | Не делает |
|---|---|---|
| Storytell | Narrative, playable beats, character canon | Image/video prompts, render, routing |
| Wardrobe | Identity, wardrobe/environment, portrait + background → sheet guidance | Shot composition, Story edits, approval |
| Storyboard | Opening composition, multi-image roles, preserve/change guidance | Anchor redesign, motion/video planning |
| Filmmaker | Motion, performance, camera, exact-start или reference-mode guidance | Static redesign, montage, provider submit |

Это содержательные требования к skills, **не утверждение об установленных skill names**. Producer лишь помогает подготовить brief/feedback и не принимает творческие решения за автора. Montage не требует creative skill/LLM. Ожидание рендера не должно удерживать specialist LLM turn; подходящий механизм Hermes нужно проверить.

Контекст выбирается явно: required inputs, авторские references и bounded trusted guidance. Stage-visible trace различает **подготовленный контекст**, **фактически наблюдённую загрузку skill** и **информацию, недоступную наблюдателю**. Metadata skill discovery не доказывает загрузку. Нельзя обещать hidden/private reasoning; inspect не запускает LLM ради заполнения пробелов.

Owning specialist при revise получает previous full result, exact approved inputs и feedback и возвращает новую полную typed revision. `needs_input/out_of_scope` оставляет результат неизменным. Technical retry/regenerate/manual render различаются по [контракту действий](hermes-artifact.md#разные-действия--разные-эффекты); никто не изменяет ancestors или маршрут через чат.

## Источники

- [storytell.md](../../agents/storytell.md):21, 27–44; [wardrobe.md](../../agents/wardrobe.md):14–22, 36–41, 112–125 — Story/cast и compact V2.
- [storyboard.md](../../agents/storyboard.md):4, 14–44, 48–55; [filmmaker.md](../../agents/filmmaker.md):4, 19–42; [cinematic.md](../../pipelines/cinematic.md):92–102 — target handoffs, motion и Montage, не deployment evidence.
- [context.md](../../context/context.md):66–94, 135–159 — pins и bounded hydration; без переноса runtime.
- Снимок Hermes: [image-gen-provider-plugin.md](../hermes-docs/tools/image-gen-provider-plugin.md):128–155; [video-gen-provider-plugin.md](../hermes-docs/tools/video-gen-provider-plugin.md):129–135, 169–178; [api-server.md](../hermes-docs/backend/api-server.md):633–645 — capabilities требуют installed verification.

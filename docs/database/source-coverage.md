# Покрытие источников

Дата: 8 сентября 2026 года. Инвентаризация выполнена через `docs/**/*`. Все исходные Markdown ниже прочитаны целиком, как и четыре JSON/шаблонных файла. `SOUL.md` и `docs/README.md` прочитаны первыми. Никакие workflow/provider/graph calls не выполнялись. Новые страницы database являются результатом этого прохода, а не независимым доказательством реализации.

## Текущие контракты

| Просмотренные файлы | Что учтено в модели |
|---|---|
| [README](../README.md), [concept](../kinodel-concept.md), [SOUL](../../SOUL.md) | Routing, статусы, local-first, human authorship, separate truth owners |
| [architecture](../backend/architecture.md), [implementation](../backend/implementation.md) | Три logical stores, точные существующие table names, граница первого среза |
| [runtime](../backend/runtime.md), [state-machine](../backend/state-machine.md), [langgraph](../backend/langgraph.md) | Work segments, same-session ownership, fence, operations, terminal receipts, pending writes, cancel |
| [reviews](../backend/reviews.md), [artifacts](../backend/artifacts.md), [pipeline](../backend/pipeline.md) | Exact subject, apply/promotion, immutable bytes, dependencies, current/pinned refs, single owner |
| [comfyui](../backend/comfyui.md), [tools](../tools/tools.md) | Frozen profiles/request intents, restricted jobs, ambiguous acceptance, API-only commands |
| [agents index](../agents/README.md), [Producer](../agents/producer.md), [Storytell](../agents/storytell.md), [Critic](../agents/critic.md) | Raw request versus Brief/Story, bounded operation results, fixed revision owner, durable unit declarations |
| [Wardrobe](../agents/wardrobe.md), [Storyboard](../agents/storyboard.md), [Filmmaker](../agents/filmmaker.md) | Visual/anchor/shot/motion ownership, exact media selectors, declared counts/order |
| [Render](../agents/render.md), [Montage](../agents/montage.md), [Craft](../agents/craft.md) | Candidate/promotion distinction, separate plan/executor, evidence and separate memory approval |
| [Muse](../agents/muse.md), [Season](../agents/season.md), [Episode](../agents/episode.md) | Planned capabilities, stable sections/episodes, plan versus completed memory, aggregate publication |
| [cinematic](../pipelines/cinematic.md), [music-video](../pipelines/music-video.md), [serial](../pipelines/serial.md) | Full production topology versus foundation; later schemas не требуют миграции сейчас |
| [context](../context/context.md), [mentions](../context/context-injection.md), [RAG](../rag/rag.md), [chunks](../rag/chunks.md) | Frozen selections/projections, source/wiki/creative/index distinction, rights and lifecycle |
| [Web UI](../frontend/webui.md), [roadmap](../roadmap.md) | UI projection/reconnect, chat не runtime, activation order, ещё не выполненные checks |

## Предложения, история и evidence

| Просмотренный файл | Статус и использование |
|---|---|
| Исходные `database/README.md` и `database/open-questions.md` | Предварительный обзор и вопросы переработаны в текущий раздел; сохранены open hosting/auth/storage/chat/wiki/privacy решения и пользовательское уточнение free local/BYOK versus paid Kinodel GPU |
| [First foundation proposal](../notes/2026-09-08-first-foundation-deployment-proposal.md) | Предложение, не разрешение deploy; first-release decisions, acceptance и disk-loss distinction |
| [Foundation priorities](../notes/2026-09-08-cinematic-foundation-priorities.md) | Baseline и последующие dispositions читаются вместе; старые пункты не объявлены текущими поломками |
| [Architecture review 2026-09-07](../notes/2026-09-07-architecture-review.md) | Исторический аудит; часть замечаний уже закрыта design-правилами |
| [Panda dry run](../pipelines/test/cinematic-v1-panda-dry-run.md) | Paper trace и Finding Disposition: symbolic refs, не настоящие assets/approvals/tests |
| [Kung-fu dry run](../pipelines/test/cinematic-v1-kung-fu-dry-run.md) | Baseline плюс Validated Disposition; allocator finding отвергнут как сформулированный, не перенесён в новую схему |
| [Open WebUI](../frontend/openwebui.md) | Reference only; его chat/database schema не наследуется |
| [Legacy README](../README%20kinodel.md), [refactoring brief](../refactoring.md) | Product/migration evidence; нет `/goal`, file-state или Producer routing в новой БД |
| [EXPLAIN_FOR_PM](../EXPLAIN_FOR_PM.md) | Коммуникационная заметка с клиническими примерами, не Kinodel multi-tenant/security contract |
| [ALM](../features/alm.md), [montage feature](../features/montage.md) | Later analysis artifact и media-service perspective; agent/executor ownership берётся из agent contract |
| [archviz](../features/archviz.md), [UGC](../features/ugc.md), [VLM](../features/vlm.md), [post-production](../features/post-production.md) | Идеи/отложенные use cases; не основание создавать новые tables/tools сейчас |
| [cinematic.v1.json](../pipelines/cinematic.v1.json) | Явно `legacy_reference_only`; не executable graph snapshot для нового execution |
| [Flux JSON](../comfyui/workflow/flux_dev_txt2img.json) | API-format txt2img example с top-level metadata; model names/settings не product defaults |
| [Klein template](../comfyui/workflow/img2img_klein.json) | Не strict JSON: unquoted template expressions, внешние URLs и model/LoRA inputs. Не зарегистрированный trusted workflow |
| [MiniMax JSON](../comfyui/workflow/minimax%20ref2vid%20api%20v1.json) | Reference/video/audio node graph с placeholders; не proof configured endpoint, i2v capability, silence или timing |

В `docs` не обнаружены отдельные operations/security страницы за пределами database: соответствующие требования извлечены из backend/context/rag/tools и foundation proposal. Snippets прочитаны как pseudo-types/examples; они не выполнены и не считаются миграциями. Локальный skill по PostgreSQL использован как инженерная справка; это не выбор Supabase. Внешние технические источники перечислены в [эксплуатации](operations-security.md).

## Реальные стыки

| Наблюдение и evidence | Вывод без переписывания чужой архитектуры |
|---|---|
| [Start protocol](../backend/runtime.md#start-protocol) публикует InitialRequest до execution transaction; [managed storage](../backend/artifacts.md#managed-project-storage) защищает bytes prepared operation pin | #question Q8: конкретизировать долговечное start reservation до появления обычной операции. Это физический пробел, не наблюдавшаяся потеря данных |
| [Tools sketches](../tools/tools.md#p0-python-contracts) дают list candidate IDs и неполный commit envelope; [reviews](../backend/reviews.md#request-lifecycle) требует exact unit mapping/activation/closure | #question Q7/Q9: final DTO/DB representation должен покрыть более сильный contract. Sketch сам помечен незавершённым, не доказанный bypass |
| [RAG source/wiki layers](../rag/rag.md#layers) называют maintained Markdown canonical, но не задают отдельный publish registry | #question Q12: предлагаемый immutable snapshot + mutable editor + exact human publish требует согласования, не выдан за старое решение |
| [Roadmap Foundation](../roadmap.md#0-foundation) ещё содержит unchecked «define» для подробно описанных invariants и reconciliation legacy JSON | #todo Сверить design versus executable acceptance после согласования. JSON уже явно legacy; новый graph migration из него не нужен |
| [Montage feature](../features/montage.md) говорит deterministic MVP; [agent page](../agents/montage.md) разделяет creative planner/executor | Читать feature как execution perspective; #todo уточнить формулировку при следующей правке владельца, не создавать конкурирующую модель |
| Klein/MiniMax workflow evidence не совпадает с понятием готового frozen production profile | #question Q16/Q13: выбрать/test register transport и workflows до renderer; не импортировать runtime payload/defaults в Brief или wiki canon |

Ошибки бумажного subagent-вызова, отсутствие настоящих профилей в dry run и непройденные tests не являются доказательством неверных runtime маршрутов. Независимая subagent-проверка в этом проходе недоступна: инструмента делегирования нет; выполнена собственная сверка источников и раздела.

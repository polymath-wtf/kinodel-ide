# Историческое покрытие источников БД

Архив предыдущих проходов, сохранён при рефакторинге 21 сентября. Текущие выводы и ограничения проверки — [сверка БД](../database/source-coverage.md). Описания старого scope и API не являются действующими контрактами.

Дата: 8 сентября 2026 года. **Отчёт предыдущего прохода:** инвентаризация выполнена через `docs/**/*`; он сообщает о полном чтении Markdown ниже и четырёх JSON/шаблонных файлов. Это исторический охват, не заявление об их повторном чтении в каждом аудите. Никакие workflow/provider/graph calls в повторном аудите не выполнялись. Страницы database описывают дизайн, не являются независимым доказательством реализации.

## Повторный аудит

### Синхронизация последующих решений 9 сентября

Текущий проход исправляет основные разделы, а не дописывает противоречащие им summary: Supabase email/password с login/display label; Windows/Linux; MVP credits 1/3/5, text 1/2 per million, free 0, signup 100; без product daily limits MVP. Final-release #todo: 5M input + 1M output/account/day, midnight Europe/Chisinau с DST, final order retention и реализация принятой actual-token оплаты lost text. MVP order logs/identities без scheduled deletion, outputs 365 дней, workflow/input/prompt bodies отдельно. Hosted wire bodies уже существовали: уточнён scope, local file или `/view` import без hosted order/bucket и server-side browser files, не добавлен domain `origin`.

Проверены текущие целевые страницы чтением и directory-wide Grep по auth/OS/limits/retention/billing/DTO; просмотрен cumulative git diff, `git diff --check` без whitespace errors (LF/CRLF warnings). Это docs-only sync, не новая внешняя сверка, independent review, API/DB/launcher/crash tests или повторный запуск прежнего link checker. Предыдущие dirty/untracked изменения сохранены. Следующие разделы описывают **исторические проходы**, их claims о чтении/проверках не относятся к этой синхронизации.

### Физические контракты 9 сентября

Отдельный текущий docs-only проход: полностью прочитаны SOUL, docs README, все 12 database pages, backend architecture/runtime/artifacts/reviews/implementation/state-machine/langgraph/comfyui/pipeline, context/context, rag/rag/chunks, tools/tools, frontend/webui, roadmap, first-foundation-deployment-proposal, agents README/producer/storytell/critic и pipelines/cinematic. Прочитаны восемь запрошенных local skills/LangGraph: CLI, fundamentals, HITL, persistence, managed-deep-agents, deep-agents-core/memory/orchestration. Остальные agent craft pages, legacy, workflow JSON и dry runs не объявляются повторно проверенными.

Context7: Supabase password identifiers, LangGraph time travel/replay/interrupts и Pydantic v2 boundary validation. Primary web pages: Python venv/fcntl/msvcrt, Linux flock, Windows LockFileEx, SQLite PRAGMA (нужные busy/FK/version/integrity sections), GCS signed URLs/lifecycle. Дата обращения 2026-09-09; ссылки в новых local-startup/physical-dto/rework и обновлённых identity/credits pages. Это не проверка реального deployment, аккаунтов, bucket/IAM, provider terms, auth login или pinned saver integration.

Добавлены три backend proposal pages: local-startup, physical-dto, rework. Синхронизированы runtime/artifacts/reviews/tools/pipeline/implementation и database/roadmap. Прежние sketch DTO помечены non-authoritative, не выданы за совместимый shipped API. Supabase users/GCS/365-day outputs/MVP цены и signup grant отражены как требования пользователя; stdlib lock API, 15-minute URL TTL, terminal-only source и settlement outcomes как предложения. Backup/RPO/RTO/payment/subscription и подробный UX отложены, restart durability и authorization не отложены.

Проверка до этой записи: read-only Node checker из разрешённого temporary directory проверил 308 inline local links/heading anchors в 32 modified/untracked Markdown, ошибок нет; один JSON Story example успешно разобран. `git diff --check` прошёл (только LF/CRLF warnings). Это не Pydantic/schema validation, не проверка всех внешних ссылок и не независимое ревью. Исходные dirty/untracked изменения сохранены; git diff относительно HEAD включает предыдущую работу. Runtime/SQL/migrations/deploy не менялись. Task/subagent и TODO tools отсутствуют: делегирование экспертам и независимый reviewer недоступны; выполнены собственные research и consistency проходы, отложенная работа отмечена #todo/#future.

### Принятие решений 9 сентября

Текущая docs-only правка выполнена после явного выбора SQLite local / PostgreSQL server. Полностью прочитаны все 12 текущих `docs/database/*.md`, `SOUL.md`, `docs/README.md`; backend architecture/runtime/implementation/state-machine/artifacts/reviews/pipeline/comfyui/langgraph; context/context, rag/rag/chunks, tools/tools, frontend/webui, roadmap, first-foundation-deployment-proposal и cinematic-foundation-priorities. Приоритеты прочитаны как история с dispositions; dry-run/test reports не редактировались. Остальные файлы исторической таблицы ниже не объявляются прочитанными повторно.

Проверен исходный git status: изменения уже были, включая untracked local-vs-hosted и audit-and-decisions; они сохранены и дополнены через apply_patch. Полного предыдущего сообщения пользователя в этом turn нет: применены все решения, явно перечисленные в текущем запросе, и согласованный контекст прочитанных документов; неизвестные auth/vendor/retention/DTO ответы не придуманы.

Покрытие новых решений: database profiles/operations и canonical runtime/implementation/langgraph задают оба engine/ownership профиля; artifacts/reviews/pipeline задают exact prefix rework и current-revision approval; architecture/comfyui/credits задают local/hosted/endpoint/proxy границы; context/rag/wiki задают private selection, pre-retrieval ACL, public release pins и user-approved memory/taste. Implementation inventory сверён: 13 logical Project DB entities, 9 text foundation; chat persistence принято, physical chat tables ещё Q10. Обе saver integration остаются #todo.

Проверка этой правки: автоматический read-only checker проверил 248 локальных Markdown links/heading anchors в 29 изменённых docs, включая ранее dirty/untracked: ошибок нет. Это проверка inline Markdown links и heading slugs, не доступности внешних URL. `git diff --check` и отдельный `git diff --no-index --check` обоих untracked database-файлов прошли без whitespace errors; Git предупреждает только о LF/CRLF. Поиск по docs не оставил действующего PostgreSQL-only local требования; старые формулировки сохранены только как явно помеченная история. Runtime tests, SQL/migrations, provider calls и deployment не выполнялись. Исторические внешние сверки ниже не выдаются за повторные live API проверки. TODO tool в доступном наборе отсутствует; отложенная работа отмечена #todo в профильных документах.

### Уточнения 9 сентября

Ниже сохранён **предыдущий проход до принятия engine/rework решений**, не текущий статус; действуют предметные контракты, остаток вопросов собран в [future](../features/future.md).

В этом проходе прочитаны все 11 имевшихся страниц database, SOUL, docs README; backend architecture/runtime/implementation/state-machine/reviews/artifacts; context/context, rag/rag/chunks; agents/critic, frontend/webui и first-foundation-deployment-proposal. Осмотрены корень и git status; поиск dependency manifests/SQL не обнаружил executable foundation. Остальные материалы исторического списка ниже не объявляются заново прочитанными. Исходная dirty worktree сохранена; git diff относительно HEAD включает правки предыдущего прохода.

Добавлен [local-vs-hosted](../database/local-vs-hosted.md): подтверждённые режимы и backup, предложение SQLite вместо обязательной локальной PostgreSQL установки, точный инвентарь 13 planned Project DB tables (9 foundation). Уточнены HTTP-output commit, stale card, Q21 prefix reuse, privacy/proxy/render границы, wiki/RAG ACL и Q22 taste. Canonical backend/frontend/RAG получили небольшие scope notes и ссылки, не executable новые маршруты. PostgreSQL остаётся server baseline; SQLite, GCS и reuse protocol не выданы за выбранные/испытанные.

Context7 использован для LangGraph, OpenRouter и Google Cloud Storage; дополнительно прочитаны официальные SQLite uses, LangGraph checkpointers, OpenRouter limits и targeted signed-URL statements. Источники перечислены в local-vs-hosted и credits-billing. Не проверены реальные аккаунты, provider settings, redistribution terms, bucket, deployment, SQL/saver integration или crash recovery. Пункты приёмки остаются #todo.

Проверены новые локальные link targets и anchors по прочитанным файлам/заголовкам, без автоматического Markdown parser. `git diff --check` не выявил whitespace errors (предупреждения LF/CRLF не ошибки). Проверка новых untracked Markdown выполняется отдельно. Ниже сохранён отчёт предыдущего прохода, не перечень действий этого уточнения.

В текущем проходе полностью прочитаны все десять исходных страниц `docs/database/`, `SOUL.md`, корневой README, `docs/README.md`, `kinodel-concept.md`, `EXPLAIN_FOR_PM.md`; backend architecture/runtime/implementation/state-machine/reviews/artifacts/comfyui; обе страницы context и обе rag; tools/tools, agents/craft, frontend/webui, roadmap и first-foundation-deployment-proposal. Остальные agent/pipeline/feature pages и workflow JSON из исторического перечня ниже заново целиком не проверялись; проверка существования ссылки/anchor не означает аудит содержания целевого файла.

Осмотрены корень проекта, `docs/**/*`, `.agents/**/*`, поиск dependency manifests/SQL и git status/diff. Новый `backend/` и executable foundation не обнаружены; `.agents/` пуст. Уже имевшиеся пользовательские правки в `credits-billing.md` сохранены, исправление границы финансовой транзакции добавлено отдельно. Legacy и вспомогательные scripts не исполнялись; deployed окружение не исследовалось. Внешняя Context7-сверка из раздела эксплуатации относится к предыдущему проходу, не к этому review.

Старые audit/decision/review записи свёрнуты в [таблицу будущих тем](../features/future.md); этот исторический охват не подтверждает выполнение runtime tests.

## Текущие контракты

| Просмотренные файлы | Что учтено в модели |
|---|---|
| [README](../README.md), [concept](../kinodel-concept.md), [SOUL](../../SOUL.md) | Routing, статусы, local-first, human authorship, separate truth owners |
| [architecture](../backend/architecture.md), [implementation](../backend/implementation.md) | Три logical stores, точные существующие table names, граница первого среза |
| [runtime](../backend/runtime.md), [state-machine](../backend/state-machine.md), [langgraph](../backend/langgraph.md) | Work segments, same-session ownership, fence, operations, terminal receipts, pending writes, cancel |
| [HITL](../hilp/hilp.md), [artifacts](../backend/artifacts.md), [pipeline](../backend/pipeline.md) | Exact subject, apply/promotion, immutable bytes, dependencies, current/pinned refs, single owner |
| [comfyui](../backend/comfyui.md), [tools](../tools/tools.md) | Frozen profiles/request intents, restricted jobs, ambiguous acceptance, API-only commands |
| [agents index](../agents/README.md), [Producer](../agents/producer.md), [Storytell](../agents/storytell.md), [Critic](../agents/critic.md) | Raw request versus Brief/Story, bounded operation results, fixed revision owner, durable unit declarations |
| [Wardrobe](../agents/wardrobe.md), [Storyboard](../agents/storyboard.md), [Filmmaker](../agents/filmmaker.md) | Visual/anchor/shot/motion ownership, exact media selectors, declared counts/order |
| [Render](../agents/render.md), [Montage](../agents/montage.md), [Craft](../agents/craft.md) | Candidate/promotion distinction, separate plan/executor, evidence and separate memory approval |
| [Muse](../agents/muse.md), [Season](../agents/season.md), [Episode](../agents/episode.md) | Planned capabilities, stable sections/episodes, plan versus completed memory, aggregate publication |
| [cinematic](../pipelines/cinematic.md), [music-video](../pipelines/music-video.md), [serial](../pipelines/serial.md) | Full production topology versus foundation; later schemas не требуют миграции сейчас |
| [context и mentions](../context/context.md), [RAG](../rag/rag.md), [chunks](../rag/chunks.md) | Frozen selections/projections, source/wiki/creative/index distinction, rights and lifecycle; mentions позднее объединены с context |
| [Web UI](../frontend/webui.md), [roadmap](../roadmap.md) | UI projection/reconnect, chat не runtime, activation order, ещё не выполненные checks |

## Предложения, история и evidence

| Просмотренный файл | Статус и использование |
|---|---|
| Исходный обзор БД и список открытых вопросов | Предварительный обзор и вопросы переработаны в текущий раздел; сохранены open hosting/auth/storage/chat/wiki/privacy решения и пользовательское уточнение free local/BYOK versus paid Kinodel GPU |
| [First foundation proposal](../notes/2026-09-08-first-foundation-deployment-proposal.md) | Предложение, не разрешение deploy; first-release decisions, acceptance и disk-loss distinction |
| [Foundation priorities](../notes/2026-09-08-cinematic-foundation-priorities.md) | Baseline и последующие dispositions читаются вместе; старые пункты не объявлены текущими поломками |
| [Architecture review 2026-09-07](../notes/2026-09-07-architecture-review.md) | Исторический аудит; часть замечаний уже закрыта design-правилами |
| [Panda dry run](2026-09-08-cinematic-foundation-priorities.md#прогресс-panda-dry-run) | Paper trace и Finding Disposition: symbolic refs, не настоящие assets/approvals/tests |
| [Kung-fu dry run](2026-09-08-cinematic-foundation-priorities.md#прогресс-критическая-сверка-kung-fu) | Baseline плюс Validated Disposition; allocator finding отвергнут как сформулированный, не перенесён в новую схему |
| [Open WebUI](../frontend/openwebui.md) | Reference only; его chat/database schema не наследуется |
| [Legacy README](../../legacy/README%20old.md), [refactoring brief](../refactoring.md) | Product/migration evidence; нет `/goal`, file-state или Producer routing в новой БД |
| [EXPLAIN_FOR_PM](../EXPLAIN_FOR_PM.md) | В исходном аудите — коммуникационная заметка с клиническими примерами; позднее адаптирована к кинопроизводству Kinodel |
| [ALM](../features/alm.md), [montage feature](../features/montage.md) | Later analysis artifact и media-service perspective; agent/executor ownership берётся из agent contract |
| [archviz](../features/archviz.md), [UGC](../features/ugc.md), [VLM](../features/vlm.md), [post-production](../features/post-production.md) | Идеи/отложенные use cases; не основание создавать новые tables/tools сейчас |
| [cinematic.v1.json](../pipelines/cinematic.v1.json) | На 21 сентября заменён текущим `design_reference_not_executable`; отражает маршрут Markdown, не исполняемый граф |
| Исторический Flux JSON (`docs/comfyui/workflow/flux_dev_txt2img.json`, удалён) | API-format txt2img example с top-level metadata; model names/settings не product defaults. Актуальные project workflows: [workflow/comfyui](../../workflow/comfyui/) |
| Исторический Klein template (`docs/comfyui/workflow/img2img_klein.json`, удалён) | Не strict JSON: unquoted template expressions, внешние URLs и model/LoRA inputs. Не зарегистрированный trusted workflow |
| [MiniMax JSON](../../workflow/comfyui/minimax%20ref2vid%20api%20v1.json) | Reference/video/audio node graph с placeholders; не proof configured endpoint, i2v capability, silence или timing |

В `docs` не обнаружены отдельные operations/security страницы за пределами database: соответствующие требования извлечены из backend/context/rag/tools и foundation proposal. Snippets прочитаны как pseudo-types/examples; они не выполнены и не считаются миграциями. Локальный skill по PostgreSQL использован как инженерная справка; это не выбор Supabase. Внешние технические источники перечислены в [эксплуатации](../database/operations-security.md).

## Реальные стыки

| Наблюдение и evidence | Вывод без переписывания чужой архитектуры |
|---|---|
| [Start protocol](../backend/runtime.md#start-protocol) публикует InitialRequest до execution transaction; [managed storage](../backend/artifacts.md#managed-project-storage) защищает bytes prepared operation pin | #question Q8: конкретизировать долговечное start reservation до появления обычной операции. Это физический пробел, не наблюдавшаяся потеря данных |
| [Tools](../tools/tools.md#nonblocking-contract) и [HITL](../hilp/hilp.md#request-lifecycle) | Старые неполные sketches удалены; проверить executable DTO/job/selection контракт при реализации, не считать текст тестом |
| [RAG source/wiki layers](../rag/rag.md#layers) называют maintained Markdown canonical, но не задают отдельный publish registry | #question Q12: предлагаемый immutable snapshot + mutable editor + exact human publish требует согласования, не выдан за старое решение |
| [Local MVP](../roadmap-mvp.md) и [cinematic JSON](../pipelines/cinematic.v1.json) | На 21 сентября текущий JSON отражает полный новый маршрут как design reference, не runtime DSL; первый билд планируется только в Local MVP |
| [Montage feature](../features/montage.md), [Montage contract](../agents/montage.md) | MVP — deterministic full-clip assembly; creative planner после MVP |
| Klein/MiniMax workflow evidence не совпадает с понятием готового frozen production profile | #question Q16/Q13: выбрать/test register transport и workflows до renderer; не импортировать runtime payload/defaults в Brief или wiki canon |

Ошибки бумажного subagent-вызова, отсутствие настоящих профилей в dry run и непройденные tests не являются доказательством неверных runtime маршрутов. Независимая subagent-проверка в этом проходе недоступна: инструмента делегирования нет; выполнена собственная сверка источников и раздела.

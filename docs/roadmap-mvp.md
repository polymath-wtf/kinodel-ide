# Первый локальный билд: задачи и приёмка

Обновлено: **19 сентября 2026 года**. Статус: план реализации и проверки, не готовый релиз. Здесь только текущий путь до первого локального инженерного билда и его пользовательских испытаний. Общие последующие этапы — в [roadmap](roadmap.md).

Рекомендации ниже не становятся принятыми решениями автоматически. Незакрытая задача означает оставшуюся работу; описание теста не означает, что он пройден. Изолированные эксперименты можно писать уже сейчас. До допуска реальных запусков закрываются относящиеся к ним контракты; до передачи билда тестировщикам — вся техническая приёмка.

**Цель продукта:** [поэтапный нодовый интерфейс](pipelines/node-roadmap.md). Первый билд исполняет заранее заданный cinematic-маршрут с теми же границами агентов, генерации и согласования; реализация конструктора не входит в этот этап.

## Что получит создатель

Человек запускает приложение без аккаунта, согласует замысел и историю, затем видит весь набор якорей от Wardrobe. В первом примере это портрет, character-sheet на основе портрета и отдельная локация без персонажей. После утверждения Storyboard использует эти изображения для кадров. После перезапуска доступны тот же проект, решения и сохранённые изображения.

Текущий согласованный маршрут:

```text
Brief → review → Story → review → Wardrobe anchor plan
→ Render: hero_face → hero_sheet(hero_face) → location
→ review всего main_frames и сохранение выбора
→ Storyboard → генерация кадров → review кадров и сохранение выбора → complete
```

Четыре согласования: Brief, Story, изображения-якоря, изображения-кадры. Планы Wardrobe/Storyboard проверяются приложением без обязательного текстового approval. Между портретом, sheet и локацией нет выбора; один кандидат на единицу в первой генерации. Для первой приёмки достаточно истории с одним shot, но число якорей/кадров не зашито в DTO. Правка промпта идёт через Critic к владельцу; «Перегенерировать» меняет seed через Render и пересоздаёт зависимые якоря. Location независима. Сохранение утверждённого выбора — часть apply согласования, не отдельная нода promotion. Последовательные jobs не требуют `Send`; текстовый тест сохраняет отдельную идентичность графа.

Область выпуска: Windows/Linux, SQLite и managed local files, один владеющий каталогом процесс приложения и один активный graph runner. Локальное хранение не означает полностью офлайн-генерацию: прямые вызовы внешней модели или настроенного ComfyUI передают выбранные входы провайдеру. Облачная база, аккаунты и сервисные кредиты не являются зависимостями этого билда.

## A. Финальные решения перед фиксацией контрактов

| Задача | Что именно закрыть | Зачем и критерий закрытия |
|---|---|---|
| [ ] A1. Согласовать image-only Brief | Привести [architecture](backend/architecture.md#implementation-gates), [physical DTO](backend/physical-dtos.md#briefv1), [artifacts](backend/artifacts.md#brief-and-story-boundary), [ComfyUI profiles](backend/comfyui.md#profile-selection) и [cinematic first slice](pipelines/cinematic.md#first-slice) к одной области действия. Рекомендация: video явно неактивен; обязательный runnable image pin; длительность клипа, video workflow class и audio policy не обязательны для image-only. Сохранить story shot count и выбор representative moment | Нельзя заставлять запуск картинки притворяться видео. Есть полные примеры image-only, text-test и будущего cinematic Brief; image-only принимается без video pin, включённое видео без runnable video pin отклоняется |
| [ ] A2. Утвердить локальное хранение и версии | Q1/Q2/Q7–Q9: постоянный data root вне venv, точные поддерживаемые ОС/Python, версии LangGraph/checkpoint/FastAPI/Pydantic/ASGI и model adapter. Рекомендация для эксперимента: отдельные SQLite Project DB и saver DB в одном root, `aiosqlite` для async SQLite; короткие транзакции, проверенные WAL/synchronous/FK/busy настройки | Отдельное владение схемами без иллюзии общей транзакции. Решение фиксируется после реального storage/saver spike, вместе с manifest/lock и схемой безопасного запуска/обновления |
| [ ] A3. Утвердить минимальные физические записи | Strict DTO, canonical bytes/digests, стартовая reservation Q8, операции/work/controls/review, assets/jobs и минимальные group/candidate/selection записи Q13. Полные uniqueness/OCC/FK, публикация файлов и терминальные исходы. Конкретные node inputs/deltas и очистка временных refs | После сбоя нельзя потерять принятую команду или принять старое согласование. Одна таблица маршрутов с владельцами выходов; успешное завершение требует всех текущих approvals и exact promotion receipt |
| [ ] A4. Назначить модели, режимы и бюджеты | Q4: model IDs и modalities для пяти capabilities, output/context/media limits, timeout, технические attempts, structured repairs, polling/backoff, import size и shutdown bounds. Пять revise и пять clarify уже приняты независимо; технические повторы их не расходуют | Расход и ожидание ограничены; Critic реально видит проверяемую картинку. Есть versioned release config; исчерпание бюджета даёт понятный block/cancel, перезапуск не обнуляет счётчики |
| [ ] A5. Закрыть подключение ComfyUI | Q13/Q16: endpoint, протокол, auth, workflow/version, reference delivery, completion/reconciliation/cancel. Вопросы и условия — ниже | Отправка задания, его завершение и повтор после потери связи имеют проверяемый смысл |
| [ ] A6. Закрыть локальный API и минимальный экран | Session bootstrap и credential storage, Host/Origin/CSRF, authorized media reads; полные start/read/review/cancel/retry запросы и ответы, конфликт старой карточки. Выбрать сборку/раздачу TypeScript UI и prerequisites; рекомендация — готовые static assets из того же local application origin | Пользователь может открыть проект и закончить весь маршрут без консоли и ручного редактирования базы. UI не требует отдельного постоянно работающего dev server; CORS не заменяет сессию |

Эти изменения затронут все установки первого локального билда. Различия ОС относятся к установке, блокировкам и завершению процессов. Конкретные адрес, доступ и workflow ComfyUI задаются для подключения; они не меняют роли агентов и правила согласования.

<a id="comfyui-transport"></a>

## ComfyUI: что согласовать до подключения

**HTTP submission** — Kinodel отправляет workflow серверу. **Completion webhook** — сервер сам отправляет Kinodel уведомление о результате. **WebSocket** — соединение для событий; это не webhook и не долговечная очередь результатов.

| Задача | Предлагаемый минимум | Что нужно подтвердить |
|---|---|---|
| [ ] C1. Определить направление и расположение | Native `POST /prompt` с API-format graph; статус через `/queue` и `/history/{prompt_id}`, bytes через `/view`. Custom gateway только если это фактический endpoint пользователя | ComfyUI на том же компьютере, в LAN или удалённо? Под «webhook» имеется в виду submission или также обратное уведомление? Нужны адрес без секретов, тип auth, безопасный пример request/response и способ status lookup |
| [ ] C2. Зафиксировать image workflows включённых ролей | Портрет, sheet с изображением портрета, независимая локация и shot с несколькими референсами. Именованные типизированные входы/выходы, роли и вместимость workflow | Проверить реальные версии/nodes/models, mappings и output response. Доказать передачу лица в sheet и всех нужных якорей в shot; txt2img один этот путь не покрывает |
| [ ] C3. Определить доставку reference images | Для upload-based workflow использовать возвращённую сервером идентичность файла. URL-based workflow требует отдельно разрешённой, доступной именно ComfyUI доставки | Krea img2img использует `879: LoadImageFromUrl`; локальный путь и ответ `/upload/image` не доказаны как подходящий вход этого node. Либо проверенный URL transport, либо отдельно версионированный upload-compatible workflow. Не открывать весь data root |
| [ ] C4. Согласовать обратные уведомления, если нужны в первом билде | Проверка отправителя, привязка к endpoint/job/attempt/request digest, дедупликация и durable acceptance до подтверждения доставки. Уведомление будит reconciliation; только worker проверяет результат и создаёт уникальную работу для нужного wait | Кто отправитель, куда он может достучаться, формат события, event identity, auth/signature, повтор/ACK и status lookup после потери уведомления? При remote ComfyUI loopback Kinodel недоступен извне. Рекомендация для первого билда — исходящий polling; обязательный callback требует отдельно согласованного reachable ingress/relay, не открытия всего API |
| [ ] C5. Согласовать неизвестный исход submit и отмену | Сохранить intent и resolved request/seed до сети; сохранить `prompt_id` после ответа. При потере ответа — verified correlation/status lookup, иначе block. Не повторять POST автоматически; повторная генерация требует отдельного явного разрешения | Как пользователь разрешает новый потенциально платный attempt и как поздний результат старого исключается из promotion? Поддерживает ли сервер адресную отмену owned job? На общем сервере нельзя очищать всю очередь или прерывать чужую работу |

Для callback-пути проверить duplicate, out-of-order, lost event, уведомление до graph wait и поздний результат после cancel. Потерянное уведомление не должно оставлять задание навсегда в ожидании. Если callback не включён, эти же гарантии завершения доказываются polling/reconciliation без фиктивного webhook endpoint.

Сверенные JSON — только исходные данные для проверки. Например, txt2img размеры `854.inputs.width/height` связаны с `815/814`; таблица mappings должна выбрать реальные поля подстановки и согласованно проверить связи. `851.inputs.images` и `853.inputs.image` — входы сохраняющих nodes, не спецификация ответа `/history`. Нужен live output fixture с реальным именем коллекции, MIME и файлом. MiniMax/video в первый image-only билд не включается.

## B. Реализация до передачи билда тестировщику

Порядок ниже — зависимости работ. Offline workflow-проверку и получение примеров endpoint можно вести параллельно с локальным storage experiment.

| Задача | Минимальная реализация | Зачем / доказательство |
|---|---|---|
| [ ] B1. Воспроизводимая среда и DTO | Manifest/lock, isolated venv, один test command. InitialRequest, Brief/Story, refs/state/context, review/Critic/apply, start/commit/work/control; VisualAnchorPlan с динамическими единицами/ролями/зависимостями, FramePlan с несколькими референсами | Positive/negative fixtures, включая циклы/пропущенные якоря, смешанный face/sheet, чужие refs, неверные digests, неподдерживаемые роли. Trusted IDs/approvals добавляет adapter |
| [ ] B2. SQLite, immutable files и команды | Profile-specific migrations, start reservation, publish-without-overwrite, operation receipts, current bindings, durable command/work transactions. Файл виден пользователю только через committed metadata. Не внедрять автоматическое удаление неподтверждённых файлов до проверки pins/GC races | Start retry не создаёт второй запуск; replay возвращает сохранённый результат; файл после publish до DB commit не становится видимым результатом. Коррупция не исправляется тихой регенерацией |
| [ ] B3. Реальный LangGraph text-test | Отдельный frozen text graph с deterministic model doubles; async SQLite saver, `thread_id=execution_id`, sync durability, prepare/wait/apply и worker recovery classifier по saved tuples/pending writes | Проверить решение, уже сохранённое в checkpoint, но ещё не доведённое до следующей устойчивой остановки. Восстановление через `None` не должно отправлять старый ответ в новый interrupt. Сбои инъектируются реальным завершением процесса |
| [ ] B4. Прямой контекст и live model adapters | Versioned instructions/resources пяти capabilities; frozen projections, bounded structured output и modalities | Wardrobe получает anchor prompt guidance; Storyboard — проверенный план и весь утверждённый набор изображений с ролями; Critic видит медиа и план правильного владельца. Проверить in-scope repair и out-of-scope отказ |
| [ ] B5. Первый rendered graph и ComfyUI adapter | Wardrobe → последовательные anchors → общий review/save → Storyboard → shots → review/save. Frozen workflow/seed/mappings, verified import и зависимое перегенерирование | Face передан в sheet, три роли переданы в shot. Новое лицо пересоздаёт sheet, сохраняя location; location меняется отдельно. Новая версия набора требует review. Утверждённые изображения доступны после restart без ComfyUI |
| [ ] B6. API и пользовательский экран | Create/open, current stage и точный review subject, текстовая правка с пояснением, clarify/cancel, preview/selection, safe failure/retry. Polling и восстановление экрана из reads | Browser close/disconnect не теряет принятое задание. Duplicate click не создаёт вторую работу; accepted command не показывается как уже применённое решение |
| [ ] B7. Windows/Linux запуск и обновление | Общий Python startup core, `.bat`/shell, проверка prerequisites, bootstrap/data locks, автоматическая только fresh initialization, version preflight до saver auto-setup, bounded shutdown | Чистая установка на обеих ОС без PostgreSQL/аккаунта. Два clone/alias не открывают один root двумя writers; смерть launcher/app не оставляет writer или installer, конфликтующий со следующим запуском. Unknown/missing existing schema блокируется без reset |

B2/B3/B7 разрабатываются совместно: минимальное process ownership нужно уже storage/saver experiment; полная автоматизация installer не нужна до первых изолированных тестов. Модульные границы уже выбраны в [implementation](backend/implementation.md); пустые пакеты и отдельный framework агентов не требуются.

## T. Обязательная техническая приёмка до локального выпуска

Каждое доказательство записать с build/dependency/graph/workflow versions, ОС, командой, ожидаемым и фактическим результатом. Результаты SQLite не сертифицируют PostgreSQL. Полная матрица — [runtime](backend/runtime.md#acceptance-matrix), установка — [startup](backend/local-startup.md#acceptance-gate).

| Проверка | Обязательное наблюдение |
|---|---|
| [ ] T1. Смерть после start acceptance до graph invoke | Тот же запуск продолжается без повторного клика; два execution в одном проекте изолированы |
| [ ] T2. Смерть между file publish, DB commit и checkpoint | Нет видимого полурезультата, повторной canonical revision или повторной генерации уже committed результата; до commit повтор model call возможен |
| [ ] T3. Все окна review/resume | До interrupt binding карточка неактивна; после принятого ответа он не теряется. Смерть до apply, после apply/в следующем node и после следующего wait не переносит ответ между карточками |
| [ ] T4. Правка/уточнение/старое согласование | Новая revision не наследует approval; clarify сохраняет subject; scope/limits сохраняются после restart. Старый digest/selection отклоняется, идентичная команда возвращает тот же receipt |
| [ ] T5. Cancel против generation/approval/promotion/completion | Победившая транзакция определяет исход; после принятой отмены нет новых creative commits. Терминальный результат после DB commit до END остаётся терминальным |
| [ ] T6. Ownership и storage failure на обеих ОС | Второе приложение отказывает; живой lock не отбирается по времени. Busy/disk full/saver error дают bounded failure; после release ownership никто не продолжает запись. Потеря existing saver tables не создаёт пустую замену |
| [ ] T7. Неопределённый submit / restart provider | Потерянный ответ не вызывает слепой POST. Отсутствие записи после очистки history не доказывает, что job не было. Исчерпание attempts/terminal failure ведёт к явному block/retry/cancel, не вечному wait |
| [ ] T8. Быстрый/повторный/поздний render result | Один wake для точного wait; результат до interrupt дожидается привязки; повтор/неверный attempt/late cancelled output не продвигают graph |
| [ ] T9. Импорт и promotion | Неверный job/unit/node, неполный manifest, битые bytes, MIME/size mismatch, path escape отклоняются. Выбранный файл и receipt после restart точно те же; `/view` не является постоянным AssetRef |
| [ ] T10. Контекст, local API и media access | Retry использует прежнюю версию ресурса, withdrawn/неразрешённый required ref блокирует вызов. Чужие IDs, stale commands, неподходящие Host/Origin/session и произвольные пути не проходят; секреты не попадают в UI/logs/artifacts |
| [ ] T11. Чистая установка и повторный запуск | Windows/Linux, путь с пробелами/кириллицей, нет Python/network/disk, incompatible version: working readiness либо понятный отказ без порчи данных. Утверждённые anchors и shot открываются без render provider |
| [ ] T12. Зависимости якорей | Сбой после портрета или подготовки sheet не меняет его родителя/seed. Face B + sheet A отклоняется; при замене лица sheet пересоздаётся, location сохраняется только при неизменных входах |
| [ ] T13. Несколько входных изображений | Реальный shot использует лицо, anatomy/clothing и окружение в своих ролях. Недостаточная вместимость workflow блокирует отправку, а не теряет референс |

Готовность первого локального инженерного билда: A/C закрыты для включённых путей, B реализован, T пройден на заявленных ОС; оставшиеся ограничения явно перечислены. Проверка ссылок, lint, in-memory saver и один успешный render этого не заменяют.

## U. Пользовательские испытания после установки проверенного билда

- [ ] U1. Пройти «идея → история → весь набор якорей → раскадровка» через интерфейс. Проверить понятность каждой карточки и следующего шага.
- [ ] U2. На anchor review перегенерировать лицо и увидеть новый sheet при прежней location; затем изменить только location. Проверить творческую правку через Critic/Wardrobe и кадра через Critic/Storyboard; история доступна, старое утверждение не переносится.
- [ ] U3. Закрыть браузер и приложение на ожидании человека и ComfyUI, затем открыть проект. Продолжить без повторного ввода уже принятого решения; увидеть понятную причину остановки при недоступном провайдере.
- [ ] U4. Отменить генерацию, дождаться возможного позднего результата. Убедиться, что он не стал выбранным автоматически и остановленный запуск не ожил.
- [ ] U5. Оценить качество идеи, истории, визуального плана и кадра; записать фактическое время/расход и неудобные места. Исправить дефекты и повторить затронутые проверки до расширения аудитории.

Это приёмка сценария и творческого качества, не перенос обязательных crash/security проверок на пользователя.

## Следующая финальная правка архитектуры

- [ ] Получить ответы на C1–C3 и обязательность C4; подтвердить поддерживаемые ОС/архитектуры и модельный набор A4. Секреты передаются через выбранный credential mechanism, не в документы или чат.
- [ ] Утвердить предложения A1–A6 после минимальных проверок; синхронизировать профильные страницы и статусы Q1/Q2/Q4/Q7–Q9/Q13/Q16 в [реестре решений](database/open-questions.md). Отдельно дописать local read/media/retry API и физические graph deltas.
- [ ] Начать реализацию B1–B3; вопросы о ComfyUI не блокируют независимый SQLite/recovery experiment. Не объявлять контракт «проверенным» до соответствующих fixtures и process-death tests.

Справочные механизмы сверены 11 сентября 2026 года: локальные [LangGraph fundamentals](../skills/LangGraph/langgraph-fundamentals/SKILL.md), [HITL](../skills/LangGraph/langgraph-human-in-the-loop/SKILL.md), [persistence](../skills/LangGraph/langgraph-persistence/SKILL.md), [ComfyUI toolkit](../skills/comfyui-skill/SKILL.md), официальные [checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) и [ComfyUI routes](https://docs.comfy.org/development/comfyui-server/comms_routes). Пример skill «side effect после interrupt выполняется один раз» не покрывает crash до checkpoint: операция всё равно обязана быть идемпотентной. Toolkit и текущие upstream docs не подтверждают работоспособность конкретного установленного сервера или нашего saver adapter.

# Архитектура: localhost WebUI поверх Hermes

**Статус:** направление выбрано, конкретная упаковка и APIs подлежат проверке в целевом Hermes. Отдельный браузерный интерфейс — требование продукта, а не запасной вариант Desktop.

## Как интерфейс общается с Hermes

```text
Браузер: React + React Flow
        ↕ один локальный origin: команды, чтение, поток событий
Тонкий web-слой пакета Kinodel
        ├─ раздача UI и передача запросов/событий Hermes
        └─ действия проекта: brief, версии, выбор, review, render
        ↕
Hermes Kanban: tasks / dependencies / dispatcher / worker runs
        ↕ profiles / skills / sessions / tools / providers
        ↕
Материалы проекта: сохранённые версии, originals и решения автора
```

Предлагаем серверную передачу HTTP + SSE: ключ Hermes остаётся на сервере, браузер получает только доступ к Kinodel. Это небольшой транспортный слой, не второй агентный backend. Где он размещается — в поддерживаемой host-поверхности плагина или в поставляемом вместе локальном сервере — уточним при реализации. Native dashboard и Electron SDK для интерфейса не требуются.

UI отправляет сообщение в связанную с проектом Producer session; Hermes выполняет turn и возвращает события. После reconnect UI перечитывает сохранённое состояние, а не восстанавливает производство из потерянного SSE. Прямые кнопки выбора, review и Generate вызывают действия плагина без обязательного разговора с моделью.

## Что переиспользуем, что добавляем

| Hermes предоставляет | Kinodel добавляет |
|---|---|
| Sessions, историю, model/tool loop, сжатие | Связь проекта и производства с Producer session |
| Kanban tasks, dispatcher, профили, skills и model overrides | Фиксированный cinematic, пять ролей, точные входы и проверку результатов |
| Image/video tools и provider interfaces | Связь заказов с шотами, сохранённые originals и выбор дублей |
| Run status, stop, события | Четыре review конкретных версий и фиксированные переходы |
| Доступные механизмы хранения/учёта | Только недостающие записи версий, решений и операций |

Один общий проверяемый путь обслуживает UI и tools агента: прочитать точные входы → проверить действие → сохранить операцию → выполнить → сохранить результат. Producer предлагает действия, но не меняет маршрут и не утверждает работу вместо автора. Observer hooks показывают события, а не заменяют проверку перед действием.

## Минимальная оркестрация

**Выбрано: фиксированный workflow поверх Hermes Kanban.** Plugin задаёт последовательность; Kanban владеет задачами, claims, запуском workers и историей попыток. Producer хранит brief и оформляет правки, но не диспетчеризует pipeline и не ждёт workers внутри своего turn. Отдельный scheduler/task DB не создаём.

### Запуск и переходы

Ниже — требуемая последовательность действий. Конкретный host/plugin механизм её выполнения и восстановления выбираем уже внутри Hermes; [вопросы 1–4](hermes-questions.md) сохраняют эти пробелы и рекомендации. Наличие этого описания не означает готовый обработчик переходов.

1. Автор подтверждает brief. Plugin сохраняет производство и версию шаблона `cinematic.pipeline`.
2. По шаблону plugin создаёт Kanban-задание Storytell: конкретный assignee/profile, skills, модель, точный подготовленный input и контракт output. Повтор команды использует ту же привязку production/stage/task.
3. Dispatcher запускает worker. Plugin принимает только валидный structured result, сохраняет артефакт; карточка ожидает human review. Завершение LLM не разрешает следующий этап.
4. Автор утверждает точную версию. Plugin сохраняет решение и завершает карточку через поддержанный Kanban lifecycle. Затем подготавливает точные входы и создаёт следующую task с parent-связью.
5. На визуальных этапах worker создаёт план; общий render-путь исполняет его без удержания творческого LLM turn. Карточка этапа отражает подготовку, генерацию и review; точное отображение tool-wait на host lifecycle проверяется при реализации.

Для MVP задачи создаём **по мере допуска этапов**, а весь будущий маршрут UI показывает из шаблона. Это уменьшает риск преждевременного запуска дочерней task по одному `parent done`. Одна task соответствует производственному этапу; доработки на текущем review используют её attempts. Завершённая карточка остаётся историей; новый проход получает новую привязку.

### Два интерфейса, одна система задач

Kinodel показывает Pipeline/Canvas, штатный интерфейс Hermes — те же Kanban-карточки, прогресс, вложения и attempts. В task metadata/attachments сохраняем ссылки на production, input snapshot и результаты; в Kinodel — ссылки на task/run/session. Карточки не дублируются в независимой БД.

Штатный `complete`, status patch или перемещение карточки не должны обходить creative approval. Любой downstream запуск повторно проверяет собственные точные входы и решение Kinodel. Общий просмотр прогресса выбран; объём управления из Hermes UI пока открыт. Рекомендация: разрешать approval оттуда только через ту же проверку версии. Обычный статус `done` сам по себе фильм не продвигает.

### Ограничения автоматизации

- Для Kinodel отключаем `auto_decompose`, `review_dispatch` и автоматические creator-session wake-ups (`auto_subscribe_on_create`); область config должна быть проверена, при необходимости используется отдельный Hermes home/profile, чтобы не менять чужие workflows.
- Manual mode отключает decomposer, но сам по себе не запрещает `kanban_create`. У workers исключаем произвольное создание/связывание задач, делегирование, terminal и редактирование кода. Способ ограничения проверяется в установленном host; одним prompt это не обеспечивается.
- Не используем `/goal`, автоматический ремонт окружения или творческую смену модели/провайдера. Ошибка возвращается как `needs_input`/`failed`, этап останавливается.
- Комментарий к task сохраняет feedback, но сам по себе не запускает работу. Request changes идёт через разрешённый lifecycle и ожидаемую версию результата.

Следующий этап допускается по сохранённому результату и необходимому approval, а не по `task done`. Работающий child не считается восстановимым checkpoint. После перезапуска используем сохранённые результаты и известные заказы; неизвестный исход сначала выясняем. Правила состояний — [ноды](hermes-nodes.md), сохранности — [артефакты](hermes-artifact.md).

## Подтверждено документацией, не установкой

| Механизм | Источник и граница |
|---|---|
| Внешние UI: sessions/history, chat, session fork | [api-server.md](../hermes-docs/backend/api-server.md):603–630; fork относится к беседе, не к фильму |
| Runs, SSE, stop, capabilities | [api-server.md](../hermes-docs/backend/api-server.md):448–565, 252–274; события не вечный журнал, shutdown может прервать run |
| Bearer auth и CORS | [api-server.md](../hermes-docs/backend/api-server.md):708–774; локальный web-слой хранит ключ и проверяет доступ/Origin |
| Регистрация tools/skills, direct dispatch | [plugins.md](../hermes-docs/backend/plugins.md):95–119; `ctx.dispatch_tool` не доказывает готовый HTTP execute-tool endpoint |
| Ограниченное делегирование | [subagent-lifecycle-api.md](../hermes-docs/backend/subagent-lifecycle-api.md):8–61; active parent, in-process retention, не самостоятельный durable worker |
| Structured output | [delegation.md](../hermes-docs/backend/delegation.md):55–59; `completed` может сопровождаться невалидной schema |
| Task skills/model/attachments | [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):257–285, 632–703; attachments не доказывают фактическую загрузку нужного содержимого |
| Human review и доработка | [kanban-worker-lanes.md](../hermes-docs/kanban/kanban-worker-lanes.md):79–93; та же task и implementer. Пользователь дополнительно проверил resume прежней worker session; точный механизм интеграции уточняется |
| Автоматические wake-ups и handoff | [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):818–834, 1344–1354; latest parent metadata не заменяет exact input bindings |

Dashboard plugin routes и API server — разные поверхности. В [Kanban snapshot](../hermes-docs/kanban/kanban-big-context.md):873 и 915–919 противоречивое описание auth; не переносим его на новый UI. Уточнить размещение custom routes и прямой вызов tools — [открытые вопросы](hermes-questions.md). Формат минимального хранилища выбираем по реальному пробелу, без обещания, что чатовая БД уже хранит все производственные факты.

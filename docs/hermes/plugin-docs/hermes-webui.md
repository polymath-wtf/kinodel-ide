# React: рабочее пространство, dashboard, материалы

**Статус:** UI-контракт MVP, не проверенная упаковка. Предпочтение — native dashboard plugin после installed SDK/auth verification; не default отдельный localhost backend.

## Одно компактное пространство

- **Dashboard в центре:** фиксированный маршрут brief → story → anchors → frames → videos → Montage/final. Карточка этапа показывает роль Agent/Tool/Review, статус, прогресс units, выбранную ревизию и причину ожидания. Связи объясняют зависимости, не редактируются пользователем.
- **Библиотека проекта:** локальные images/videos, typed outputs, inputs/references, candidates и прошлые production/revision lineages. Личные Hermes-чаты и чужие проекты сюда не попадают.
- **Контекстные детали:** входы, prepared context, результат, versions/candidates, prompt/settings и доступные действия выбранной ноды. Frameboard — упорядоченное представление тех же shots, не новый архив.
- **Producer chat по желанию:** компактная открываемая панель для замысла/feedback. Работа напрямую через brief/review/manual render не требует чата. Node discussion адресуется owning specialist, а не всегда Producer.

Изображения, клипы и final видны как материалы с originals, не только как пути в чатах. Dashboard, библиотека и chat используют одни refs/receipts; автор не переносит ответы специалистов вручную. Исторический результат явно показывает свою lineage, не выдаётся за текущую версию.

## Детали контекста и наблюдаемость

Показывать задание, exact input revisions, подготовленные bounded projections и их роли, pinned guidance/settings, output validation и approval отдельно. В раскрываемой trace различать:
1. **Подготовлено к передаче** — сохранённый input/context snapshot.
2. **Наблюдалось** — доступный host факт загрузки skill/tool execution.
3. **Недоступно** — нет поддержанного события/transcript или невозможно подтвердить фактическое использование.

Каталог skills не равен loaded skills; пустая activity не означает отсутствие работы. Child-chat/transcript открывать только через проверенный authorized host path, если доступен. Не обещать private reasoning или полную child-tool ленту в parent SSE. Inspect/read не инициирует LLM для объяснения отсутствующих данных.

## Состояния и универсальный Continue

Это названия для UI, **не новая Hermes API enum**. Host/plugin проецирует состояние и разрешённые действия из task/run, operations, approvals и provider receipts. UI не решает маршрут самостоятельно.

| Наблюдаемая ситуация | Поведение |
|---|---|
| Не хватает required input/capability | Показать конкретный blocker, не отправлять generation с урезанными refs |
| Активная работа | Прогресс и разрешённый Cancel; Continue не создаёт новый заказ/agent turn |
| Остановленная незавершённая работа | Continue доставляет разрешённое продолжение существующей logical operation в сохранённых inputs/бюджете |
| Human review | Exact subject/plan и complete selection; отдельные Approve/Revise, Continue не заменяет решение автора |
| Provider wait / частичный набор | Known job IDs и X/N; ждать/сверять существующие заказы, не submit всего набора снова |
| Unknown/crash ambiguity | Blocked reconciliation с объяснением; нет automatic paid retry |
| Недостаточный/исчерпанный/неизвестный allowance | Blocked/wait; показать scope и остаток LLM/media attempts/cost cap либо причину неопределённости, запросить явное дополнительное согласие/сверку до вызова |
| Failed/cancelled/blocked | Только явно разрешённое recovery/new production; не скрытый restart |
| Этап завершён / final | Продолжить только объявленный доступный следующий handoff; terminal не открывается заново, final даёт просмотр/скачивание |

Continue — универсальная команда доступного продолжения, не кнопка «ещё раз запусти выбранную ноду» и не Wardrobe-only start. Маршрут движется автоматически в пределах сохранённого разрешения; не вводить обязательный ручной Continue на каждой обычной границе. Continue/restart/retry не обновляют caps попыток/стоимости; planned downstream authorization выбирается явно и не возникает из story approval.

## Review и manual render

- На четырёх gates показать точную story revision или complete media set и supporting plan. Selection и approval — отдельные действия; невалидные/несовместимые candidates нельзя утвердить. Устаревшая вкладка получает stale denial и перечитывает факты.
- Revise явно вызывает owning specialist и новую typed revision. Простое сообщение «ок», просмотр файла или `task done` не approval.
- Technical retry сохраняет inputs/seeds и успешные units, не вызывает творческого агента; новая платная попытка расходует существующее allowance либо требует отдельного явного согласия. Regenerate разрешает новую стоимость и новый candidate с frozen prompt/settings.
- Prompt/seed/settings edit в компактной render-панели создаёт **новый явный request**, связанный с plan revision и exact refs; effective settings/override видны до submit. Никакой перезаписи прежнего плана/дубля и обязательного LLM turn.
- UI и специалист используют одну validation/operation boundary для render, не два независимых submit/accounting paths. Incompatible mode/required refs блокируют действие, а не молча заменяются.
- Базовый video mode — img2vid. Optional ref2vid показывает per-shot subject/frame и compatible approved portrait/sheet pins; N=0, отсутствующая pair или неразрешённое/неподдержанное multi-character conditioning дают unavailable с причиной до submit. Никаких auto identity/drop refs/скрытого mode fallback; несколько персонажей в Story сами по себе не запрещены.

Повтор доставки, reload и новый delivery key той же logical operation возвращают её saved receipt/status. Потеря ответа отображается как неопределённая доставка/сверка, не приглашение сделать новый платный заказ. Command acceptance не равен готовому результату. Правка утверждённого предка предлагает новую lineage без автоматической пересборки старых сцен.

Обновления использовать через verified native events + повторное чтение сохранённого состояния; если событий недостаточно — ограниченное polling. Observer stream не canonical state. Exposed controls/media запрещены до устранения auth contradiction; tokens/secrets/raw paths не помещать в UI.

## Границы и основания

Нет graph editor, drag-to-change routing, timeline/editor, generic tool dashboard или новой chat system. [Артефакты и действия](hermes-artifact.md) задают точные гарантии, [MVP](hermes-mvp.md) — приёмку полного фильма.

- [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):845–896, 915–929 — documented dashboard/events и противоречивый auth, не installed evidence.
- [api-server.md](../hermes-docs/backend/api-server.md):499–523, 633–645; [subagent-lifecycle-api.md](../hermes-docs/backend/subagent-lifecycle-api.md):43–55 — private reasoning/child-tool gaps, skill metadata и in-process lifetime.
- [hooks-big-context.md](../hermes-docs/backend/hooks-big-context.md):500 — observer события могут теряться; [hilp.md](../../hilp/hilp.md):13–38, 54–60 — exact действия и compatible selection.

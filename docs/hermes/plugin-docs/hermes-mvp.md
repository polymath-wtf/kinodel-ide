# Cinematic MVP — объём и приёмка

**Статус:** целевой продуктовый объём; реализация в Hermes не проверена. Промежуточные срезы уменьшают риск сборки, но не меняют определение MVP.

## Обязательный результат

Автор проходит `brief → story → anchors → frames → videos → Montage → final` в React-dashboard. Четыре специалиста: Storytell, Wardrobe, Storyboard, Filmmaker. Четыре явных review: story, полный набор anchors, полный набор frames, полный набор videos. Producer необязателен; планы не требуют отдельных согласований.

Финал — **локально сохранённый, технически проверенный немой MP4** из всех утверждённых клипов в Story-порядке. Один opening frame и один непрерывный clip на каждый shot; Montage использует полные клипы, простые склейки и объявленную нормализацию, без творческого LLM-монтажёра.

Минимальные функции:
- фиксированный маршрут, контекстные детали этапа, упорядоченная раскадровка и проектная библиотека;
- typed JSON results, точные входы/контекст и неизменяемые ревизии;
- просмотр, выбор дубля, technical retry и explicit manual render без обязательного LLM;
- approvals точных ревизий/наборов, stale denial и сходящиеся дубликаты команд;
- reopen сохранённых originals без провайдера; восстановление известных операций либо понятный blocked reconciliation;
- отсутствие личных Hermes-чатов в проекте и контроль доступа ко всем действиям/медиа.

## Сборка после согласованного аудита

| Срез | Наблюдаемая приёмка | Какой риск снимает |
|---|---|---|
| 0. Installed audit | Версия/commit, native SDK, Kanban, auth, storage и provider capabilities подтверждены по установленным источникам; выбран минимальный план | Не строить на вымышленных API |
| 1. Brief → Storytell | Валидный story сохранён, повторно открыт; invalid output не публикуется; approval v1 из устаревшего окна отклоняется после v2 | Валидация, сохранность и точное human review |
| 2. Wardrobe → anchors | V2 plan, 2N+1 units, exact dependent refs; полный совместимый набор выбран/утверждён; проверен N=0 | Покрытие targets и lineage выбора |
| 3. Storyboard → frames | Каждый Story shot имеет opening frame; все обязательные anchors/ранние frames переданы без потери ролей | Полнота раскадровки и conditioning |
| 4. Filmmaker → videos | По одному немому clip/shot; базовый img2vid использует точный frame; optional ref2vid требует provider support и exact per-shot pin compatible approved portrait/sheet pair | Неподдерживаемые modes, длительность и подмена входов |
| 5. Montage → final | Все утверждённые clips в Story-порядке; ffprobe подтверждает MP4, ожидаемые параметры/длительность и отсутствие audio stream | Полный фильм, а не image-only демо |

Провайдер image/video выбирается из реально доступных средств Hermes. ComfyUI — кандидат, не доказанная готовая интеграция. До платных LLM/media calls сохранить выбранное автором разрешение области operation/stage/production и caps попыток/стоимости с учётом известных provider limits; для render согласовать модель/workflow, размер, длительность и seed-политику. Использовать host accounting прежде собственной узкой metadata, не новый budget engine. Неподдерживаемые роли, настройки или режим **блокируют submit**, а не молча урезаются.

## Сквозная приёмка

1. На небольшом проекте пройти весь маршрут с четырьмя gates; никакой task `done` не заменяет approval.
2. Между этапами и зависимыми media units перезапустить Hermes. Сохранённые результаты/успехи не пересоздаются, executing/unknown заказ не отправляется автоматически повторно.
3. Reload, повторный клик, потеря ответа и **новый delivery key той же logical operation** сходятся к одной операции/receipt. Stale revision и чужой проект отклоняются до эффекта.
4. Technical retry сохраняет frozen inputs/seeds и успехи без творческого вызова; новая платная попытка расходует остаток либо требует явного дополнительного согласия. Regenerate/manual edit создают явный новый платный заказ и candidate, не перезаписывают прежний.
5. Неопределённое окно crash после submit даёт blocked reconciliation; UI не обещает exactly-once у неподдерживающего провайдера. Cancel агента не считается отменой уже принятого render.
6. Правка утверждённого предка создаёт новую lineage без каскадного rebuild и без переименования старых approvals в новые. Старый фильм доступен как исторический.
7. После отключения провайдера проект открывает локальные original images/videos/final с проверяемыми refs/digests, не только URL/cache.
8. Проверить caps платных LLM attempts (включая repair/judge) и media orders: Continue/restart/retry не обновляют allowance; дубликаты не резервируют его повторно. Недостаточный/исчерпанный/неизвестный остаток блокирует вызов, дополнительное согласие сохраняется явно. Story approval без scoped downstream authorization не разрешает новые заказы.
9. Ref2vid: проверить exact per-shot frame/subject/approved portrait-sheet pins и parent compatibility. N=0, отсутствующая pair, неразрешённый multi-subject binding или неподдержанное multi-character conditioning делают mode недоступным до submit, без auto identity/drop refs/fallback. Несколько персонажей в Story сами по себе не запрещены; базовый img2vid остаётся отдельным явным выбором.

## Не входит

Graph editor, произвольные маршруты, selective automatic rebuild, timeline/editor, музыка/голос, Critic, новые creative gates, broad retrieval/chunking и автоматическая публикация памяти. Доступ к child-чатам — полезная штатная возможность, не повод строить свою chat system. Новый runner, task DB и LangGraph не являются частью базового плана.

## Основания и пределы

- [cinematic.md](../../pipelines/cinematic.md):35–51, 84–102 — handoffs, modes, Montage и full-film acceptance.
- [wardrobe.md](../../agents/wardrobe.md):22, 36–41 — V2 и 2N+1; [storyboard.md](../../agents/storyboard.md):4, 31–44 и [filmmaker.md](../../agents/filmmaker.md):4, 21–33 — target contracts, не заявление о развёрнутых stages.
- Ограничения recovery/media-провайдеров: [архитектура](hermes-kinodel-architecture.md), [артефакты](hermes-artifact.md). Следующий шаг — [read-only аудит, затем утверждение плана](hermes-questions.md).

# Hermes Kanban: архитектура и границы исполнения

Основа: [K, строки 97–158](kanban-big-context.md#L97-L158), [D, строки 555–579](../backend/delegation.md#L555-L579).

Это срез локальной документации, а не проверка установленного runtime.
Kanban хранит работу, зависимости и историю попыток независимо от чата.
Dispatcher назначает попытку процессу; агент выполняет поручение внутри неё.
`delegate_task` создаёт дочернее рассуждение в дереве владельца-сессии.
Goal engine продолжает работу внутри сессии, но не заменяет очередь задач.
Публичный lifecycle API позволяет плагину управлять дочерней сессией через handle.
Три оси следует читать отдельно: состояние карточки, состояние попытки, состояние сессии.
Успешный ответ модели не равен завершению карточки.
Сохранённый результат не равен возобновляемому исполнению.
Принятое уведомление не равно завершившемуся ходу агента.
Ниже факты сопровождаются ссылками на исходные диапазоны строк.
Обозначение K: `kanban-big-context.md`, основной обзор доски.
Обозначение W: `kanban-worker-lanes.md`, контракт worker и владения.
Обозначение D: `../backend/delegation.md`, актуальный контракт делегирования.
Обозначение L: `../backend/subagent-lifecycle-api.md`, публичный lifecycle API.
Обозначение P: `../backend/plugins.md`, регистрация и возможности плагинов.
Обозначение H: `../backend/hooks-big-context.md`, точные границы hooks.
Ссылки относительные; `#L…-L…` обозначает строки локального исходника.
Разделы со сценарием и плагином явно выделяют предлагаемую композицию.
При расхождении общего обзора и специального контракта приоритет указан отдельно.

## Сущности и места хранения

Источники: [K, 124–158](kanban-big-context.md#L124-L158), [K, 1342–1398](kanban-big-context.md#L1342-L1398).

Board — самостоятельная очередь с собственной SQLite-базой.
Доска `default` использует `~/.hermes/kanban.db`.
Именованная доска хранит базу в `~/.hermes/kanban/boards/<slug>/kanban.db`.
Для каждой доски отделены рабочие каталоги и логи.
Task — логическая единица работы, а не процесс и не диалог.
Task содержит название, описание, assignee, статус и необязательный tenant.
Необязательный idempotency key служит дедупликации повторного создания.
`task_runs` содержит отдельную строку каждой попытки исполнения.
`tasks.current_run_id` указывает на текущую незакрытую попытку.
При закрытии попытки сохраняется outcome, а указатель очищается.
Три попытки одной задачи дают три run, а не три задачи.
`summary` и `metadata` принадлежат run: это свидетельства конкретной попытки.
`result` на task — короткое legacy-поле, не замена подробному handoff.
`task_links` хранит направленные зависимости между карточками.
Комментарии образуют долговечную переписку вокруг задачи.
`task_events` фиксирует переходы и может ссылаться на run.
Agent session хранит разговор и исполнение агента; она не тождественна task_run.
Один профиль может исполнять разные задачи в разных сессиях.
Зарезервированные workflow-поля не означают наличие готового workflow-router.
Tenant — мягкое пространство имён внутри доски, не отдельная база.

## Состояния карточки и зависимый запуск

Источники: [K, 131–138](kanban-big-context.md#L131-L138), [K, 461–476](kanban-big-context.md#L461-L476), [K, 1386–1416](kanban-big-context.md#L1386-L1416).

`triage` — идея или работа, требующая уточнения и маршрутизации.
`todo` — работа, ещё не допущенная к исполнению, в частности из-за родителей.
`ready` — кандидат на claim диспетчером.
`running` — карточка с выполняющейся попыткой.
`blocked` — остановка, требующая разрешения причины блокировки.
`review` — отдельная фаза проверки той же карточки.
`done` — завершённая работа в текущем состоянии доски.
`archived` — карточка, скрытая из обычного представления.
Ребро parent → child означает: сначала prerequisite, затем зависимая работа.
Базовое описание promotion: все родители `done` позволяют `todo → ready`.
Контракт финального handoff отдельно допускает родителей `done`/`archived`.
Не следует переносить эту оговорку на все переходы без проверки реализации.
Связь с незавершённым родителем может вернуть `ready`-ребёнка в `todo`.
Claim повторно проверяет родителей, а не доверяет одному видимому статусу.
Добавить зависимость к уже работающему чужому child нельзя.
Исключение: worker связывает свою карточку перед dependency-block handoff.
Dependency-block с открытым родителем переводит работу в `todo`.
Без открытого родителя такой block переклассифицируется в `needs_input`.
Support-карточку нельзя ставить после заблокированной задачи, которую она разблокирует.
Для смысловой ссылки без scheduling gate достаточно ID в описании.

## Dispatcher, профиль и worker lane

Источники: [W, 12–47](kanban-worker-lanes.md#L12-L47), [K, 138–158](kanban-big-context.md#L138-L158), [K, 1297–1340](kanban-big-context.md#L1297-L1340), [K, 1447–1449](kanban-big-context.md#L1447-L1449).

Assignee — имя профиля, а не адрес уже живущего агента.
Worker lane задаёт исполнителя, механизм запуска и способ завершения claim.
Стандартная lane запускает `hermes -p <assignee> chat -q <prompt>`.
Запуск происходит в закреплённом workspace задачи.
Dispatcher обычно работает внутри gateway и обходит доски по тикам.
Документированный интервал по умолчанию — 60 секунд; это настройка, не SLA.
Поддерживаемая эксплуатационная позиция — один host и один dispatcher.
В нескольких gateway только один сохраняет `kanban.dispatch_in_gateway: true`.
Остальные gateway могут доставлять уведомления своих профилей.
Неизвестный assignee оставляет задачу `ready` с `skipped_nonspawnable`.
`HERMES_KANBAN_TASK` передаёт ID назначенной карточки.
`HERMES_KANBAN_DB` закрепляет абсолютный путь базы доски.
`HERMES_KANBAN_BOARD` передаёт slug доски.
`HERMES_KANBAN_WORKSPACES_ROOT` задаёт корень рабочих каталогов.
`HERMES_KANBAN_WORKSPACE` задаёт каталог конкретной задачи.
`HERMES_KANBAN_RUN_ID` связывает worker с текущей попыткой.
`HERMES_KANBAN_CLAIM_LOCK` несёт lock вида `<host>:<pid>:<uuid>`.
`HERMES_PROFILE` обозначает профиль worker, в том числе для авторства комментариев.
`HERMES_TENANT` передаёт tenant, если он задан.
Новая внешняя CLI-lane требует отдельной интеграции, а не простой подмены имени.

## Claim, идентичность попытки и восстановление

Источники: [W, 127–137](kanban-worker-lanes.md#L127-L137), [K, 138](kanban-big-context.md#L138), [K, 1342–1392](kanban-big-context.md#L1342-L1392), [K, 1427–1443](kanban-big-context.md#L1427-L1443).

Claim атомарно закрепляет доступную задачу и создаёт её task_run.
Run ID и claim lock отличают актуального владельца от устаревшего worker.
Завершающие tools поддерживают `expected_run_id` для отказа устаревшей попытке.
Живой claim нельзя закрыть из посторонней сессии обычным complete.
Для оператора отдельно предусмотрен явный override; это не право дочернего агента.
TTL claim в lane-контракте по умолчанию составляет 15 минут.
Истечение TTL само по себе не доказывает смерть процесса.
Живой локальный worker получает продление claim вместо повторного запуска.
Пропавший PID позволяет определить crash до истечения TTL.
PID сопоставляется с fingerprint запуска при завершении оставшегося процесса.
Это защищает от сигнала постороннему процессу с переиспользованным PID.
Worker может сам зарегистрировать PID, если dispatcher умер после spawn.
Саморегистрация происходит до первого модельного вызова.
Если run уже reclaimed, опоздавший worker выходит без работы над карточкой.
При ручном выводе карточки из `running` открытый run закрывается как `reclaimed`.
Закрытие никогда не claimed-карточки может создать синтетический run нулевой длительности.
Так сохраняется handoff оператора, даже если процесса исполнения не было.
Orphan reconciliation восстанавливает карточки с нарушенным claim bookkeeping.
Повторный запуск — новая попытка с историей предыдущих исходов.
Это не checkpoint-resume произвольных внешних эффектов внутри старой попытки.

## Протокол исполнения и причины остановки

Источники: [K, 457–476](kanban-big-context.md#L457-L476), [K, 561–625](kanban-big-context.md#L561-L625), [K, 1434–1443](kanban-big-context.md#L1434-L1443).

Назначенный worker начинает с `kanban_show()` и читает `worker_context`.
В контексте доступны описание, родители, прежние попытки и комментарии.
Длительная операция требует наблюдаемой активности или `kanban_heartbeat`.
Обычная tool-активность также поддерживает liveness назначенного worker.
Успех фиксируется `kanban_complete`, а не финальной фразой модели.
Передача на проверку фиксируется `kanban_request_review`.
Невозможность продолжить фиксируется `kanban_block` с причиной.
Reviewer завершает свою попытку complete, request_changes или обоснованным block.
Exit code 0 при всё ещё `running` — `protocol_violation`.
Перед таким выходом runtime может дать модели до двух terminal-call nudges.
Эти nudges относятся только к назначенному worker, не к его потомкам.
Повторяющиеся нарушения протокола ограничены отдельным retry budget.
Документированный default — три последовательных нарушения; task `max_retries` влияет на границу.
Обычный spawn breaker имеет свой default `failure_limit: 2`.
Временные provider-сбои с exit 75 дают `rate_limited` и requeue без failure tick.
Непоправимый provider error с exit 78 блокирует карточку уже на первой попытке.
Истёкший `max_runtime_seconds` — ограничение wall-clock конкретного run.
Stale-detection отдельно учитывает долгую работу и отсутствие heartbeat.
Его default: более четырёх часов работы и последний heartbeat старше часа.
Stale-requeue не увеличивает failure counter; обычный TTL-reclaim может увеличивать.

## Handoff, workspace и сохраняемые результаты

Источники: [K, 134–137](kanban-big-context.md#L134-L137), [K, 527–559](kanban-big-context.md#L527-L559), [K, 1160–1192](kanban-big-context.md#L1160-L1192), [K, 1348–1354](kanban-big-context.md#L1348-L1354).

Зависимость переносит не только право запуска, но и результат prerequisite.
Child получает summary и metadata последнего completed run каждого parent.
Полный родительский transcript автоматически вместо handoff не передаётся.
Retry той же карточки читает собственные prior attempts: outcome, summary, error.
Summary объясняет выполненное человеку; metadata позволяет переиспользовать факты машинно.
Рекомендуемые поля metadata включают changed_files и verification.
Dependencies, retry_notes и residual_risk помогают следующему исполнителю принять решение.
Это соглашение о содержимом, а не обязательная JSON-схема ядра.
Длинные логи и чужие диалоги не заменяют короткий проверяемый результат.
Новые свидетельства после завершения parent помещаются в body follow-up карточки.
Git-ветка показывает изменения, но не заменяет объяснение решений и проверок.
Scratch — временный каталог и удаляется при завершении задачи.
Объявленные через `artifacts` файлы копируются в durable attachment storage до очистки.
При request_review такое копирование выполняется уже на этапе handoff.
Отсутствующий объявленный scratch artifact оставляет задачу in-flight для исправления пути.
Необъявленные scratch-файлы не получают обещания сохранности.
`dir:<path>` использует существующий абсолютный путь и сохраняется после завершения.
`worktree` предоставляет сохраняемую git-рабочую копию для кодовой задачи.
Доска разделяет свои каталоги, но worker работает с правами локального пользователя.
Сохранение артефактов следует проектировать раньше terminal-call, а не после cleanup.

## Проверка, доработка и новые задачи

Источники: [W, 74–95](kanban-worker-lanes.md#L74-L95), [W, 136–137](kanban-worker-lanes.md#L136-L137), [K, 48–95](kanban-big-context.md#L48-L95), [K, 1160–1205](kanban-big-context.md#L1160-L1205).

Для этапа реализации выбирают одну из двух моделей review.
Same-card review: реализация заканчивается request_review, карточка переходит в `review`.
Этот переход не является block и не расходует block-loop accounting.
Dispatcher по умолчанию запускает reviewer с bundled skill `sdlc-review`.
Reviewer подтверждает результат через `kanban_complete`.
Reviewer возвращает конкретную доработку через `kanban_request_changes`.
Review-run закрывается, а работа направляется исходному implementer.
При этом заново применяется parent gating.
В human-only режиме `kanban.review_dispatch: false` отключает автоматического reviewer.
Другая модель — заранее созданная downstream review/QA/release карточка.
Тогда implementer завершает свою фазу через complete, открывая зависимый этап.
Дополнительный same-card review в таком графе может дублировать проверку или остановить цепь.
Sticky-block `review-required:` на prerequisite оставляет его reviewer-child без допуска.
Диагностика обнаруживает такой deadlock, но не снимает пользовательскую блокировку сама.
PR completion contract связывает разрешённое завершение с состоянием PR и evidence.
Проверка PR — снимок на момент gate, а не постоянное наблюдение за будущим CI.
Позднее падение CI оформляется follow-up с новой причиной и ссылкой на done parent.
Предпочтение новой карточки сохраняет границу выполненного и вновь обнаруженного объёма.
При конфликте двух веток возможна reconciliation-карточка с обоими результатами-родителями.
Нейтральный исполнитель получает оба handoff вместо догадок по одному конфликтующему diff.

## Три разных источника оркестрации

Источники: [K, 738–765](kanban-big-context.md#L738-L765), [K, 800–843](kanban-big-context.md#L800-L843).

Встроенный auto decomposer — отдельный auxiliary LLM-вызов.
Его модель задаётся через `auxiliary.kanban_decomposer`.
Он читает roster профилей и их описания для маршрутизации работы.
Auto mode обрабатывает triage-карточки на тиках dispatcher.
Default `auto_decompose_per_tick: 3` ограничивает число разложений за тик.
Завершённый built-in fan-out записывается атомарно вместе с дочерним графом.
Возврат такого root в triage не должен повторно создавать тот же built-in граф.
Это не семантическая дедупликация независимо созданных ручных графов.
Точная ориентация auto-root связей в обзоре неоднозначна; здесь она не реконструируется.
Orchestrator profile — обычный профиль, которому поручена организация работы.
`kanban.orchestrator_profile` выбирает владельца root после fan-out.
Эта настройка не загружает prompt и custom logic профиля внутрь decomposer.
Custom decomposition профиля требует явной работы этого профиля.
`auto_decompose: false` отключает только автоматический triage-decomposer.
Ручные decompose/specify и профильные `kanban_create` остаются отдельными возможностями.
Creator chat controller — исходная сессия, которая может проснуться по outcome задачи.
Creator wake определяется подпиской, независимо от настройки auto_decompose.
`auto_subscribe_on_create: false` отключает новую auto-subscription; существующие/унаследованные wake-подписки сохраняются [K, 1116–1122](kanban-big-context.md#L1116-L1122).
Общие проектные решения фиксируются до fan-out и передаются в body каждой нуждающейся карточки.
Профильные роли распределяют ответственность, но не создают новый тип task lifecycle.

## События, уведомления и доставка обратно

Источники: [K, 1243–1340](kanban-big-context.md#L1243-L1340), [K, 1382–1402](kanban-big-context.md#L1382-L1402).

Task event сообщает о состоянии работы; подписка определяет место доставки.
Связь session parent/child сама по себе не задаёт destination уведомления.
Подписка хранит профиль, platform, chat и нужные thread/scope anchors.
`notify` отправляет пассивное сообщение и не запускает ход агента.
`wake` принимает синтетическое входящее сообщение для обычного agent turn.
`notify+wake` сочетает пассивный ping и admission этого turn.
Для последнего режима нужны и отправленный ping, и принятый wake.
Checkpoint отправки ping отделён от admission wake.
Отклонённый wake не требует повторения уже checkpointed ping.
Но crash между отправкой и checkpoint допускает повторную доставку.
Поэтому здесь нет гарантии exactly-once.
Принятая очередь не гарантирует успешный model turn или ответ в platform.
Missing handler, неверный route и полная очередь требуют последующей попытки admission.
Completed и review_requested могут передать summary прямо в wake.
Status, archived и unblocked — bookkeeping; они не обязаны будить агента.
Profile-owned notifier использует адаптеры профиля назначения, а не профиль исполнителя.
Legacy-подписки без profile stamp доставляет владелец dispatcher singleton lock.
Desktop уведомления доступны только при работающем приложении и живом event stream.
Gateway-подписка нужна для доставки, не зависящей от открытого desktop окна.
Подробный run остаётся источником результата; сокращённый event summary его не заменяет.

## delegate_task: контекст и область ответственности

Источники: [D, 7–32](../backend/delegation.md#L7-L32), [D, 80–105](../backend/delegation.md#L80-L105), [D, 329–341](../backend/delegation.md#L329-L341), [W, 49–72](kanban-worker-lanes.md#L49-L72).

Делегирование создаёт свежую дочернюю беседу для ограниченного поручения.
Child не получает автоматически историю родительского разговора и tool calls.
Рабочее поручение передаётся через `goal` и `context`.
Project context files resolved workspace добавляются по правилам Hermes.
Поэтому «исправь ту ошибку» без воспроизводимых фактов — неполный контракт.
В parent context возвращается итоговая сводка, а не весь ход рассуждений child.
Child имеет собственную terminal session, но это не обязательно отдельная файловая копия.
Tools наследуются от parent с дополнительными запретами для детей.
Model-facing `delegate_task` не даёт параметром произвольно расширять toolsets.
Leaf не делегирует дальше и не обращается к пользователю через `clarify`.
Shared memory writes, cross-platform messages и создание cron также ограничены.
Orchestrator-child сохраняет delegation capability при допустимой глубине.
Worker Kanban может делегировать локальное исследование внутри своей попытки.
Унаследованный `HERMES_KANBAN_TASK` не делает child владельцем карточки.
Descendant fence запрещает ему завершать run supervising worker.
Дочерние shell, kernels, hooks и обычные stdio MCP также получают non-owner scope.
Routing доски и workspace сохраняются для чтения и работы над поручением.
Fence относится к board root данной lineage, не ко всем независимым тестовым home.
Это cooperative runtime scoping, а не OS sandbox против произвольного Python-кода.
Итог child оценивает владелец run; terminal board outcome остаётся его обязанностью.

## Делегирование: lifetime, batch и процессы

Источники: [D, 184–262](../backend/delegation.md#L184-L262), [D, 535–616](../backend/delegation.md#L535-L616).

Top-level model calls могут сразу вернуть handle и продолжиться фоном.
Это требует сессии, способной позднее принять результат.
Stateless request/response путь без такой доставки использует synchronous fallback.
Nested orchestrator ждёт своих workers в текущем turn и собирает общий ответ.
По умолчанию batch доставляет одну сводку после завершения всех задач.
`independent_completions` включает доставку по отдельным completion units.
Group управляет объединением результатов, а не порядком исполнения зависимых задач.
Если B требует результат A, B запускается после получения A, а не через одинаковую group.
Default concurrency — 10; размер batch сверх настроенного лимита отклоняется.
Default `max_spawn_depth: 1` означает плоское дерево.
Одного `role="orchestrator"` недостаточно: для grandchildren нужно повысить глубину.
Новые сообщения parent не отменяют фоновых детей автоматически.
Stop, close или reset owning session прерывает её детей и их synchronous descendants.
Закрытие viewer чужой gateway-owned сессии не равно закрытию владельца работы.
Background terminal process принадлежит агенту, который его запустил.
При завершении child оставшиеся его процессы прекращаются.
Возврат PID или общий terminal backend не передаёт process ownership.
Явный `process_manage(action="handoff", ...)` передаёт допустимый процесс parent.
Для bounded build/test child обычно ждёт завершения и сообщает фактический результат.
Для долгого watcher проще вернуть PR/SHA, чтобы parent создал свой процесс.

## Долговечность результатов и рабочей копии child

Источники: [D, 13–25](../backend/delegation.md#L13-L25), [D, 219–232](../backend/delegation.md#L219-L232), [D, 355–382](../backend/delegation.md#L355-L382), [D, 582–616](../backend/delegation.md#L582-L616).

Завершённое background delegation событие сохраняется в profile-local `state.db`.
Если процесс умер до доставки готового результата, pending event может быть восстановлен.
Admission через очередь проверяет ownership и использует durable claim.
Отказ admission оставляет результат для повторной доставки.
Crash/restart delivery остаётся at-least-once с ограничениями replay age и retry policy.
Для API server completion добавляет timeline row; следующий model turn инициирует клиент.
Запущенный, но не завершённый child после исчезновения owner не возобновляется.
Его outcome становится `unknown`: внешние эффекты могли уже произойти.
Повтор поручения после unknown требует учёта этих эффектов, а не слепого replay.
Default cwd child совпадает с cwd parent.
Параллельные изменения общих файлов поэтому могут конфликтовать.
`delegation.worktree_isolation: true` включает отдельные git worktree и ветки.
В результате появляются path, branch, commits и dirty для последующей интеграции.
Чистый worktree без новых commits может быть автоматически удалён.
При ошибке проверки worktree сохраняется, а defaults не считаются измеренным отсутствием работы.
Опция действует только для git и local terminal backend.
Non-git, remote backend или ошибка создания возвращают shared-workspace поведение.
Default delegation не задаёт общего wall-clock timeout на весь child.
Настраиваемый `child_timeout_seconds` ограничивает inactivity; progress обновляет окно.
Stale-monitor, iteration budget и board max_runtime — разные ограничители разных уровней.

## Goal engine и отдельное состояние /goal

Источник: [K, 716–735](kanban-big-context.md#L716-L735); это единственный содержательный локальный контракт `/goal` в данном наборе.

Goal-mode карточка включает continuation loop внутри worker session.
CLI-флаг — `--goal`; инструмент создания использует `goal_mode=True`.
`--goal-max-turns` задаёт предел продолжений; документированный default — 20.
Title и body карточки служат текстом acceptance criteria.
После turn auxiliary judge сопоставляет output worker с этими критериями.
Если работа не закончена и бюджет остаётся, worker продолжает в той же сессии.
Loop заканчивается по verdict, terminal board action или исчерпанию бюджета.
Исчерпание goal-бюджета блокирует карточку для human review.
Verdict `unachievable` сразу блокирует цель с объяснением judge.
Complete и request-review не обходят реальный отрицательный judge verdict.
Gate отклоняет handoff только по полученному verdict, а не по сетевой ошибке judge.
Judge auth/timeout/relay error допускает handoff и оставляет warning в логе.
Это fail-open поведение проверки, не доказательство достижения цели.
Worker log показывает turn N/M и verdict поверх обычной tool-ленты.
Goal mode полезен для итеративной работы с явными критериями результата.
Для короткого one-shot поручения он добавляет стоимость judge на каждом turn.
Chat `/goal` использует тот же engine, но отдельное состояние разговора.
Установка chat goal не создаёт, не claims и не перемещает Kanban-карточку.
Chat `/goal status` не показывает loop worker другой сессии.
`delegate_task(goal=...)` передаёт текст поручения; это не включение goal loop.

## Публичный Subagent Lifecycle API

Источник: [L, 8–61](../backend/subagent-lifecycle-api.md#L8-L61), полный локальный контракт сервиса.

Сервис доступен как `ctx.subagent_lifecycle`.
Тип запроса импортируется как `SubagentLaunchRequest` из `agent.subagent_lifecycle`.
Документированный launch принимает goal, context, role, correlation_id, allowed_toolsets.
Пример role — `leaf`; allowed_toolsets может сузить доступ до `("file",)`.
Parent определяется из активного agent turn, включая turn Kanban-worker.
Произвольный startup или HTTP handler без parent получает `No active Hermes parent session`.
Возвращаемый handle сериализуется через `handle.to_dict()`.
Handle содержит versioned opaque capability; его нельзя заменять угадываемым ID.
Методы наблюдения и управления: `status`, `wait`, `cancel`, `result`, `reconnect`.
`wait(handle, timeout_seconds=2)` ограничивает ожидание вызывающей стороны.
Этот timeout не задаёт максимальную продолжительность исполнения child.
Состояния: `PENDING`, `STARTING`, `RUNNING`, `SUCCEEDED`, `FAILED`.
Также: `INTERRUPTED`, `CANCEL_REQUESTED`, `CANCELLED`, `UNKNOWN`.
`cancel(handle, reason=...)` просит cooperative interrupt на безопасной границе.
`CANCEL_REQUESTED` не считается подтверждением завершившейся отмены.
Terminal result immutable и idempotent, ограничен 32k символов, содержит stable hash.
Он не возвращает transcript или hidden reasoning.
Initial implementation хранит metadata и terminal results in-process один час.
После restart reconnect даёт `RECONNECT_UNAVAILABLE` и не создаёт replacement child.
Per-launch timeout, cwd override, per-tool blocks и расширение parent toolsets отклоняются.

## Сквозной сценарий: одна работа, несколько исполнителей

Композиция на основе [K, 461–510](kanban-big-context.md#L461-L510), [W, 85–95](kanban-worker-lanes.md#L85-L95), [D, 555–564](../backend/delegation.md#L555-L564).

Предлагаемый сценарий начинается с явно описанной implement-карточки и assignee.
Creator фиксирует ожидаемый результат, границы изменения и доказательства приёмки.
До запуска выбирается same-card review, без параллельной downstream review-карточки.
Dispatcher claims карточку, создаёт run и запускает профиль в workspace.
Worker читает board context и устанавливает, что уже пробовали прошлые attempts.
Для узкого анализа он создаёт child с самостоятельным goal/context.
Child исследует проблему, но не закрывает карточку родительского worker.
Worker получает summary, проверяет применимость и завершает собственную реализацию.
Если child не пережил restart, его unknown не считается выполненным анализом.
Если worker потерял run ownership, старый handle child не возвращает ему claim.
Перед review worker объявляет нужные scratch artifacts для durable копирования.
Request_review закрывает implementation attempt и оставляет карточку в фазе review.
Reviewer получает handoff и проверяет конкретный результат, а не обещание исполнителя.
Request_changes создаёт путь к новой implementation attempt с сохранённой историей.
Complete reviewer закрывает работу по выбранной модели review.
Notifier отправляет outcome туда, где зарегистрирована подписка creator.
Wake admission лишь даёт creator возможность отдельным turn оценить результат.
Новая проблема после done оформляется отдельной follow-up карточкой с parent handoff.
Goal mode, если выбран заранее, меняет внутреннюю итерацию worker, а не эту ответственность.
Плагин может показать связи всех объектов, не объединяя их статусы в один «готово».

## Разночтения источников и пределы выводов

Сверка: [K, 97–110](kanban-big-context.md#L97-L110), [K, 705–735](kanban-big-context.md#L705-L735), [K, 800–925](kanban-big-context.md#L800-L925), [K, 1160–1390](kanban-big-context.md#L1160-L1390), [D, 555–564](../backend/delegation.md#L555-L564), [H, 1757–1781](../backend/hooks-big-context.md#L1757-L1781).

Старая сравнительная таблица K описывает delegate_task как всегда блокирующий RPC.
Актуальный D описывает background top-level, sync nested и stateless fallback.
Тезис той таблицы об исчезающем audit тоже нельзя распространять на нынешнюю delegation.
D описывает durable completed delivery, live logs и post-hoc просмотр.
K рекомендует completed cards как immutable history, но также описывает reopen.
Следовательно, новая follow-up карточка — предпочтительная практика, не абсолютный запрет reopen.
K 1264 обещает удаление подписки на done; K 836 описывает reopen-safe retention.
Retention подписок остаётся противоречивым: поведение на done/archive/GC требует проверки кода.
Multi-host примеры не расширяют single-host posture worker/claim detection.
Общий обзор hooks обещает post-commit для всех трёх lifecycle callbacks.
H уточняет исключение: dependency-wait blocked hook вызывается ещё внутри транзакции.
Worker-spawned observer выполняется внутри dispatch lock, поэтому не место долгой работы.
K 873 заявляет token-защиту всех dashboard routes.
K 915 отдельно утверждает отсутствие HTTP auth для `/api/plugins/`, а WS требует token.
Эту коллизию нельзя разрешить ссылкой на ключ другого API server.
Auto-root fan-out описан без достаточно однозначной схемы зависимостей для реконструкции.
Отдельная goals-страница в доступном наборе отсутствует; полный `/goal` API не выводится.
Общий engine не доказывает restart-resume goal session или side-effect checkpoints.
Retention lifecycle API L не приравнивается к durable delivery model-facing delegation D.
Для проектирования достаточно различать durable board, session-owned child и admission доставки.

## Кастомный плагин: подключение существующего Hermes backend

Предложение адаптера; опорные API: [P, 19–106](../backend/plugins.md#L19-L106), [P, 150–197](../backend/plugins.md#L150-L197), [K, 845–896](kanban-big-context.md#L845-L896).

Плагин — тонкий адаптер команд, представления и корреляции существующих сущностей.
Он не создаёт второй scheduler, собственный AIAgent или параллельный task lifecycle.
Запись статусов должна проходить через штатный Kanban backend, не через raw SQL.
Минимальный пакет содержит `plugin.yaml` и `__init__.py` с `register(ctx)`.
General plugin обнаруживается отдельно от включения; нужен opt-in в `plugins.enabled`.
Для project-local расположения дополнительно требуется разрешение project plugins.
`ctx.register_tool` публикует проверяемый tool contract и handler адаптера.
`ctx.register_command` добавляет пользовательскую slash-команду на поддержанных поверхностях.
`ctx.register_hook` подключает наблюдение за событиями, а не владение транзакциями доски.
`ctx.dispatch_tool(name, args)` вызывает зарегистрированный tool; parent context документирован для вызовов из commands.
Это не универсальный исполнитель произвольной slash-строки вроде `/goal`.
Системную подсказку можно добавить отдельной секцией, если она нужна поведению агента.
Для доски уже существует REST namespace `/api/plugins/kanban/`.
Чтение board/task и запись штатных действий должны переиспользовать этот контракт.
WebSocket `/events?since=<event_id>` сообщает об изменениях и поддерживает catch-up.
Предлагаемый UI после событий перечитывает board, не дублирует state machine локально.
Board slug входит в адаптерную идентичность вместе с task ID.
Run ID хранится отдельно, чтобы отличать retry от нового логического задания.
Профиль assignee показывается отдельно от сессии creator и destination подписки.
Correlation card ↔ child handle — предлагаемая карта только запускаемых адаптером children, не встроенная связь Hermes.

### Активный turn, child lifecycle и доставка сообщения

Контракты: [L, 8–61](../backend/subagent-lifecycle-api.md#L8-L61), [P, 929–976](../backend/plugins.md#L929-L976), [H, 400–425](../backend/hooks-big-context.md#L400-L425).

Собственный plugin tool внутри активного agent turn может вызвать `ctx.subagent_lifecycle`.
Launch использует `SubagentLaunchRequest`, а не импорт приватного delegate_tool или полей AIAgent.
Предлагаемый correlation_id связывает поручение с task/run для отображения, не выдаёт board ownership.
Сериализованный handle сохраняется как opaque capability, без попытки восстановить его по task ID.
Status и result отделены от статуса карточки; краткий wait может вернуть timed_out при работающем child.
Cancel в UI сначала отображает запрос отмены, затем подтверждённый terminal state.
После process restart адаптер показывает reconnect unavailable вместо скрытого replacement launch.
Для повторного запуска требуется новое явное решение с учётом возможных старых эффектов.
Startup callback и обычный HTTP request не имеют автоматически активного Hermes parent.
Поэтому они не должны имитировать turn ради прямого launch child.
Для входящего текста существует `ctx.inject_message(content, role='user', *, session_key=None, origin=None) -> bool`.
В gateway используется известный session_key либо origin для маршрута в собственном профиле плагина.
`allow_gateway_injection` выдаётся отдельно конкретному плагину.
True означает принятие в очередь/dispatch, а не готовый ответ или успешную отправку пользователю.
Injected text не исполняет slash-команды, не approve tools и не разрешает pending prompts.
Следовательно, injection текста `/goal ...` не является программным включением goal mode.
Для итеративной board-работы адаптер использует документированную goal-mode карточку.
Публичные `ctx.goal` и `ctx.delegate` в этих источниках не определены.
Опциональный `ctx.register_system_prompt_section` задаёт правила применения tools, но не заменяет API.
Адаптер получает child result через handle (`wait/result`) и явно возвращает supervising worker; board handoff — отдельное действие.

### Hooks, HTTP-границы и минимальная приёмка адаптера

Контракты: [H, 1757–1781](../backend/hooks-big-context.md#L1757-L1781), [P, 810–832](../backend/plugins.md#L810-L832), [API, 448–491 и 605–617](../backend/api-server.md#L448-L617), [K, 871–925](kanban-big-context.md#L871-L925).

Lifecycle hooks подходят для короткой телеметрии и корреляции уже известных идентификаторов.
Dependency-wait hook может находиться внутри DB-транзакции; callback не запускает встречную мутацию.
Worker-spawned hook находится под dispatch lock; callback не ждёт LLM или child completion.
Hooks не дают адаптеру transactional veto или exactly-once delivery.
Пропущенное наблюдение восполняется чтением canonical board/run, а не придуманным outcome.
HTTP agent API `/v1/runs` управляет agent runs, не строками Kanban `task_runs`.
`/api/sessions` управляет сессиями и chat turns; это отдельный namespace.
Его `API_SERVER_KEY` не доказывает защиту dashboard `/api/plugins/kanban/`.
Из-за расхождения K 873/915 нельзя обещать dashboard REST auth без проверки конкретного backend.
Адаптер потребляет готовый dashboard REST/WS; полного локального контракта собственного HTTP router здесь нет.
Метод `ctx.register_http_route` не следует выдумывать для заполнения этого пробела.
Default plugin isolation — `in_process`; права Python-кода не ограничиваются одной tool schema.
Host mode отделяет interpreter, но часть возможностей требует in-process исполнения.
В частности, streaming dashboard endpoints перечислены среди ограничений host mode.
Предлагаемый первый объём: чтение карточки, одно штатное действие, показ текущего run и handoff.
Child launch добавляется только для поручения, действительно требующего дочернего рассуждения.
Приёмка адаптера должна различать повтор команды, новый run и повтор уведомления.
Отдельно проверяются stale ownership, unavailable reconnect и отсутствие ложного «готово» после admission.
Эти критерии — план будущей реализации, а не заявление о выполненных тестах плагина.
Открыты два интеграционных вопроса: фактическая dashboard auth и контракт расширения HTTP router.
Итоговая граница: Hermes исполняет и хранит lifecycle, плагин связывает намерение, наблюдение и интерфейс.

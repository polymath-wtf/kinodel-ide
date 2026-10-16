---
date: 2026-10-16
feature: runtime-fix
design: ../../runtime-fix.md
status: draft
approval: pending
---

# Code plan: Runtime fix

**Цель:** убрать блокировки управляющего контура, затем реализовать Project → Run и устойчивые Stop / Continue в существующем runtime.

- [Архитектура](../../runtime-fix.md) согласована пользователем после трёх уточнений.
- [Ранний proof](../../../../test-results/README.md#runtime-graph-step-pause-proof--16-october-2026) выполнен на установленном LangGraph: последовательное исполнение по одному superstep, свежий invocation saver barrier, восстановление той же work без отдельного Continue wake. Это не приёмка application integration.
- Этот code plan и точные [контракты](contracts.md) ожидают **Gate 2**. Запросить повторное архитектурное решение, если интеграция опровергнет proof или потребует другого владельца состояния.

## Стратегия и зависимости

Первая архитектурная фаза разделена на два ограниченных среза: durable facts и публичные reads. Остальные этапы сохраняют порядок согласованного дизайна. Proof уже снял неопределённость механизма паузы; реализация управления начинается после responsiveness/lifecycle/project slices.

| Файл | Результат | Зависимости | Архитектурный этап |
|---|---|---|---|
| [01 — compact facts](phase-01.md) | Slot/reference/result reads без повторной сборки ancestry/config | Gate 2 этого среза | 1a |
| [02 — reads и responsiveness](phase-02.md) | Metadata/status + переключение действующего polling UI, bounded original/v1 reader | 01 | 1b |
| [03 — lifecycle](phase-03.md) | Readiness без production work, due/wake loop, корректный shutdown | 01–02 | 2 |
| [04 — Project / Run](phase-04.md) | Durable draft, отдельные проекты/история, атомарный Run | 03; ранний proof | 3 |
| [05 — backend Stop / Continue](phase-05.md) | Pause-aware stepped runner, dispatch fencing, тот же work/thread | 04; ранний proof | 4 |
| [06 — UI](phase-06.md) | Три стабильные кнопки, Cancel в меню, journal и единый status | 02, 04–05 | 5 |
| [07 — автоматический batch](phase-07.md) | Review/активация same-execution Story → Wardrobe → batch | 01–06 | 6 |

01–03 не требуют завершённого Project/control API. Изменение wire в 02 принимается в его срезе. Не подключать незавершённый Story-anchor route ради Project меню или ради ускорения reads.

## Исходный baseline и границы

На момент планирования schema version **24** (`backend/database.py:18`), есть `native_terminal_observations`; terminal observer сохраняется. Рабочее дерево содержит незакоммиченные backend/frontend изменения и незавершённый баг 5. Перед каждым заданием сверять соответствующий diff; не заменять его содержимое по старому HEAD.

Горячие пути подтверждены [аудитом](../../../../test-results/README.md#read-only-responsiveness-audit--16-october-2026). Точки интеграции: `backend/image_group_worker.py:188–240`, `backend/portrait_submission_store.py:199–326`, `backend/anchor_reference_store.py:304–385`, `backend/wardrobe_store.py:209–261`, `backend/image_reads.py:147–227`, `backend/api.py:426–459`, `backend/story_runner.py:81–113,332–333,385–628`.

Исторические graph triples/outcomes, saved command envelopes и отдельный image bridge не переписываются. Новый runtime-status показывает exact execution, а не timestamp-last или автоматически подставленный consumer. Существующий `/continue` сохраняет прежний смысл для уже сохранённых envelopes; новые команды используют отдельные paths из contracts.md.

## File map

### Новые production-модули — только три backend owner и typed client

| Файл | Ответственность | Фаза |
|---|---|---|
| `backend/runtime_reads.py` | Compact runtime projection/DTO и availability, без graph construction | 02 |
| `backend/projects.py` | Project DTO, draft storage, receipts и create/save/run use cases | 04 |
| `backend/runtime_control.py` | Initial running-control owner; затем pause/continue receipts и dispatch-only guard | 04–05 |
| `web/src/entities/project/contracts.ts` | Strict Project/draft/receipt DTO | 06 |
| `web/src/entities/project/queries.ts` | Project/history queries; HTTP через существующий shared client | 06 |
| `web/src/entities/execution/runtime.ts` | Strict runtime status/control DTO; используется действующим polling уже в 02 | 02 |

`RunControls.tsx` переименовать в `RuntimeControls.tsx`, обновив callers; не оставлять два новых конкурирующих control owner.

### Основные изменяемые файлы

| Область | Файлы и исходные точки |
|---|---|
| Saved facts | `portrait_submission_store.py:286–389`, `anchor_reference_store.py:281–385`, `wardrobe_store.py:209–289,468`, `anchor_parent_resolver.py:43`, `image_group_results.py:182–244,374–479` в `backend/` |
| Slot/worker | `backend/image_group_worker.py:157–240`, `backend/portrait_worker.py:78–96,428–698`, `backend/anchor_reference_worker.py:52–67,112–155,307–367` |
| Reads/API | `backend/image_reads.py:80–227`, `backend/story_reads.py:38–118`, `backend/api.py:426–459,628–707,776–809` |
| Admission/storage | `backend/database.py:90–126,402–448,830–843`, `backend/story_start.py:145–283`, `backend/story_control.py:126–246` |
| Graph delivery/effects | `backend/story_runner.py:38–113,144–382,385–628`, `backend/image_runner.py:11–19,281–341`, `backend/openrouter.py:209–317`, `backend/openrouter_wardrobe.py:246`, `backend/wardrobe_operation.py:47–59`, `backend/wardrobe_store.py:329–349`, `backend/review_store.py` decision admission |
| Same-execution route | `backend/story_anchor_start.py:21–99`, `backend/story_anchor_graph.py:37–79`, `backend/story_graph.py` authored Wardrobe transition, `backend/image_group_store.py:103–208` |
| UI | `web/src/pages/workspace/Workspace.tsx:35–125,214–230,270–317`, `pages/workspace/model/{productionDraft,cache}.ts`, `pages/workspace/ui/{ProductionForm,StartStoryForm}.tsx`, `features/commands/{useCommands,RunControls,ContinueControls}.tsx` и `journal.ts`, `entities/execution/{queries,images}.ts`, `ImageCandidates.tsx`, `shared/api/http.ts:19–27,55–71`, существующие scoped styles |

Ни новая registry/command bus, ни ValidationManager, ни ORM/очередь/глобальный cache не вводятся. Exact места изменений и удаления находятся в отдельных фазах.

### Проверки

Новые файлы: `tests/test_runtime_fact_reads.py`, `tests/test_runtime_reads.py`, `tests/test_runtime_lifecycle.py`, `tests/test_projects.py`, `tests/test_runtime_pause.py`; `web/checks/runtime-controls-check.cjs`, `web/checks/runtime-controls-browser-check.cjs`. Существующие fixture helpers и affected suites переиспользуются. В сумме план добавляет **13 production/test/client файлов**, переименовывает один control component; documentation/evidence считаются отдельно.

## Wiring и lifetime

1. `open_story_runtime` (`backend/story_control.py:235–246`) по-прежнему единолично владеет application DB, saver и root lock.
2. `create_app` lifespan (`backend/api.py:426–459`) выставляет runtime после preflight/setup, но не вызывает production run до readiness.
3. Новые use cases вызываются через `StoryRuntime`: `_open` и command-task tracking сохраняются; command acceptance не вызывает LangGraph.
4. Runner отбирает due work/known native attempts; отдельный in-process event ускоряет sweep, DB остаётся источником истины.
5. Для каждого graph superstep строится свежий `_InvocationSaver`; barrier закрывается до перехода к следующему шагу или освобождения claim. Stepped runnable boundary не становится terminal/stable human wait.
6. Дорогой read/PNG decode вне event loop использует своё read-only соединение и отслеживаемую задачу. Текущий writable SQLite connection в thread не передаётся. Cleanup дожидается readers/writers до store/root release.

## Storage/API решения

Подробности: [contracts.md](contracts.md). Предлагаются две additive migration:

- **24 → 25:** `projects`, `project_commands`, `execution_runtime_controls`; Run сразу создаёт running-control, pause-команды ещё не активны.
- **25 → 26:** `runtime_control_commands` — exact command receipts, без delivery queue и новых work kinds.

Если к началу реализации schema изменилась, перенумеровать migrations после проверки истории; не менять прежние migration bodies. Missing compact facts в старой истории дают явный unavailable/block, не свободный слот/complete/разрешение POST. Массовый backfill через status GET запрещён.

Ошибки новых commands используют существующее FastAPI `detail`, без новой общей error taxonomy. Exact shape и HTTP statuses — в contracts.md; старые routes/error shapes сохраняются.

## Условия приёмки

- [ ] Ноль Wardrobe/config/native-request reconstruction в status/slot/idle; metadata не читает PNG bytes.
- [ ] На сопоставимом fixture: status/Stop p95 ≤ 200 мс, max event-loop lag ≤ 100 мс; счётчики тяжёлых вызовов подтверждают причину улучшения.
- [ ] API готово до provider/model work; shutdown не теряет uncertainty и не освобождает ownership с живыми writers.
- [ ] Create → restart не создаёт work; конкурентный Run с одной project revision принимает один execution.
- [ ] Stop/Continue сохраняют work/thread/attempt/seed/бюджет, не обходят review, не повторяют принятый submit.
- [ ] Terminal Cancel доступен из меню при backend capability, работает при paused/blocked; новый Run ждёт terminal receipt.
- [ ] UI polling не выключает commands; journal сохраняет/replays тот же envelope, включая старые endpoints.
- [ ] Новый authored batch идёт в одном execution/thread; live/restart/provider-off acceptance выполнена отдельно от mocks.
- [ ] Для изменённых контрактов обновлены domain docs; текущее выполнение отражено в roadmap; доказательства — только в test-results.

## Проверки и следующий шаг

Фазы указывают точные affected команды. Backend использует `.venv313`; TEMP/TMP — утверждённый `C:\Users\Seryoger\AppData\Local\Temp\opencode`. UI после изменения проверяется screenshots каждого затронутого экрана по AGENTS.md. Полная suite не запускается автоматически поверх каждого среза.

**Gate 2:** утвердить этот code plan целиком либо bounded phases 01–03. До реализации любой принятой фазы проверить её baseline и зависимости. Новое открытие архитектурного вопроса останавливает соответствующий срез, а не запускает ещё один управляющий слой.

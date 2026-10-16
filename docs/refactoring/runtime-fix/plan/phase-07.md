---
phase: 7
name: authored-same-execution-batch
depends_on: phase-01 through phase-06
---

# 07. Review и активация автоматического Wardrobe → batch

## Цель

Новый поддержанный pipeline идёт от Run через Story approval и Wardrobe к ordered anchor batch в одном execution/thread. Пауза применяется на всех границах; промежуточный image-consumer handoff не нужен.

## Контекст

Project/control/stepped runner/UI уже приняты. В рабочем дереве **уже существуют** Story-anchor Start, same-execution group storage, authored graph и часть runner/read интеграции; domain docs описывают более ранний checkpoint готовности. Эта фаза начинается с review существующего diff, не с написания нового pipeline поверх него. Frozen historical Story/Wardrobe/image routes неизменны.

## Review gate

Сопоставить actual code, tests и evidence бага 5 с [архитектурой](../../runtime-fix.md) и [contracts §2–4](contracts.md). Подтвердить одного владельца group/wait/result/join, frozen render authorization и соблюдение pause. Удалить лишние route-specific ветки, но не authored semantics и не provider recovery facts.

## Изменить существующее по результатам review

### `backend/story_anchor_start.py:21–99`, `backend/projects.py`

- Project Run может явно принять exact Story-anchor graph из draft и frozen `AnchorRenderIntentV1` (size/profile/connection). Replay не читает сегодняшние profiles/env и не меняет route.
- После acceptance route становится default только для **новых** Project drafts. Старые сохранённые drafts/envelopes не ретаргетятся автоматически; смена graph — явное сохранение намерения перед новым Run.
- Не выдавать video/full cinematic capability, которой здесь нет. Авторизован только поддержанный Story→anchor batch slice.

### `backend/story_graph.py`, `backend/story_anchor_graph.py:37–79`

- Story approval идемпотентно даёт Wardrobe activation, но не terminal completion нового route.
- Committed Wardrobe plan ведёт authored edge к `prepare_anchor_batch`; group registration на том же execution, exact external wait и graph-owned join.
- До `batch_wait.interrupt` только сохранённые exact refs; resume проверяет matching result/wake/task, join сохраняет terminal receipt перед END.
- Внутренние phase helpers не вставляют production side effects до pause guard или перед replayable interrupt.

### `backend/image_group_store.py:103–208`, `backend/image_group_results.py:422–479`, `backend/image_runner.py:163–281`

- Group identity связана с exact Wardrobe transition/render intent, replay registration даёт ту же membership/wait; нет второго consumer execution.
- Group result/wake publication и exact join сохраняют один owner. Provider attempts/parent refs/retained results не заменяются graph state bodies.
- Pause между parent jobs запрещает следующий dispatch; observation/import опубликованного job разрешены, graph delivery ждёт running-mode.

### `backend/story_runner.py:398–447,567–571`, `backend/story_reads.py:73–118`, `backend/continue_command.py:388–482`

- Проверить new graph selection/exact checkpoint classifier на stepped runner, где intermediate `snapshot.next` уже законная operational boundary.
- Runtime-status/reads нового execution не проходят source→effective handoff resolution и не требуют terminal Wardrobe source.
- Новый route не использует Continue production_intent/start_images. Existing historical bridge остаётся только для его исходных sources и saved old envelopes, без reopen terminal source.

### `web/src/pages/workspace` и `web/src/features/commands/ContinueControls.tsx`

- Run отображает exact frozen render settings до запуска, из сохранённого Project draft.
- После Wardrobe ничего не auto-click-ать и не POST-ить из UI effect; progression принадлежит графу.
- У нового route отсутствует post-Wardrobe authorization form. Progress/первый сохранённый original видны до завершения всего batch, с честным recorded/verified смыслом.

## Проверка

Переиспользовать и расширить `tests/test_story_anchor_start.py`, `tests/test_story_anchor_storage.py`, `tests/test_story_anchor_runtime.py`; не создавать вторую параллельную группу тестов той же topology.

```powershell
.\.venv313\Scripts\python.exe -B -m unittest tests.test_story_anchor_start tests.test_story_anchor_storage tests.test_story_anchor_runtime
.\.venv313\Scripts\python.exe -B -m unittest tests.test_runtime_pause tests.test_image_group_worker tests.test_image_result_runtime tests.test_continue
```

- [ ] Один Run → Story review → exact approval → Wardrobe → ordered portrait/background/sheet; **один execution/thread**.
- [ ] Restart после каждого parent и между steps: те же job/attempt/seed/refs, никакого повторного POST/upload.
- [ ] Stop до Wardrobe, после plan, перед group preparation, во время external wait и между parents; Continue работает без новых settings/budget.
- [ ] Uncertain acceptance/failed native job/invalid output дают конкретный block или поддержанный Retry, а не скрытый consumer/new run.
- [ ] Historical terminal outputs/bridge/replay byte-identical; current defaults не переписывают accepted routes.

Затем отдельная live приёмка по ComfyUI roadmap: реальные portrait → background → sheet, controlled restart между parents/steps, выключенный provider и чтение сохранённых результатов. Рабочие incident executions не исправлять как побочный эффект code-plan проверки. Live acceptance не подменяется passing mocks.

После UI изменений — affected typecheck/build/browser checks и desktop screenshots по AGENTS.md. После приёмки синхронизировать runtime/pipeline/artifacts/frontend contracts и соответствующий roadmap checklist; evidence только в test-results.

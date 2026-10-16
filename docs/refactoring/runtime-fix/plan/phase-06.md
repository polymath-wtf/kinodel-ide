---
phase: 6
name: stable-runtime-ui
depends_on: phase-02, phase-04, phase-05
---

# 06. Project workspace и три стабильные кнопки

## Цель

Один Topbar control owner показывает Run / Stop / Continue с неизменным смыслом. Проекты существуют до execution; фоновые reads не делают команды периодически недоступными. Из неисправимого block есть terminal Cancel в закрытом меню.

## Контекст

Backend Project/status/metadata/control endpoints уже приняты по [contracts §2–5](contracts.md). Старый journal (`web/src/features/commands/journal.ts:7–124`) сохраняет exact endpoints/body; старый `continue` смешивает recovery/handoff и не может стать новой управляющей командой. Новые graph settings не выбираются UI автоматически.

## Создать

### `web/src/entities/project/contracts.ts`, `queries.ts`

- Strict draft/project/history/Run receipts из contracts.md; duplicate/foreign project/current-execution refs отвергаются.
- Queries используют existing shared HTTP/session client. Project list и history — разные keys; current execution выбран явно, не latest timestamp.

### `web/src/entities/execution/runtime.ts` — использовать существующий результат 02

Strict runtime/control DTO, nullable control, reason/availability consistency; execution/project selector ответа обязан совпадать с запросом. Не создавать второй state store для progress.

### `web/checks/runtime-controls-check.cjs`, `runtime-controls-browser-check.cjs`

Pure DTO/journal checks и браузерные mock/guarded API сценарии. Переиспользовать existing shell/browser fixtures; не создавать ещё один frontend prototype.

## Изменить

### `web/src/features/commands/journal.ts:12–82,107–124`

- Добавить kind variants `project_create`, `project_save`, `project_run`, `pause`, `runtime_continue`; payload/endpoint/receipt validators — exact по contracts.md.
- `runtime_continue` соответствует `/controls/continue`; старый `continue` сохраняет `/continue` и свой DTO без retarget. Existing prefix/envelopes читаются без переписывания их endpoint/body/key.
- Receipt matching проверяет command key, project/execution identity, accepted revision и graph/snapshot там, где нужно. Expected HTTP status выводится из command kind: create=201, save=200, run/control=202; без новых обязательных полей в старых envelopes.
- Delivery сохраняет receipt/rejection **до** navigation/invalidation. Lost response повторяется exact saved envelope. 409 не создаёт новый key и не перебазирует пользовательскую команду автоматически.
- Replay старого accepted receipt не перезаписывает cache более новой project/control revision. Receipt подтверждает acceptance; текущие данные перечитываются независимым GET.

### `web/src/shared/api/http.ts:19–27,55–71`

- Поддержать 201 в expectedStatus и narrow parsing нового `detail:{message,current_revision}` наряду с прежним string detail.
- Передавать current revision в typed command feedback, не вводя общий error framework. Повтор session bootstrap сохраняет payload/key; 401/403 handling не расширяется на автоматический retry conflict.

### `web/src/features/commands/useCommands.tsx:18–69,93–102`

- Добавить сообщения/точные delivery handlers новых kinds. Блокировать pending Run/save по project ID, pending управляющие команды — по execution ID, а не все проекты глобально.
- Command busy отделить от Query fetching/error age. Удалить runtime-командные вызовы `useFresh`; review body/subject validation не ослаблять ради этого удаления.
- Если после обновления callers `useFresh` больше не нужен, удалить сам timer/hook; не оставить неиспользуемый interval.

### `web/src/features/commands/RunControls.tsx:6–20` → `RuntimeControls.tsx`

- Rename и превратить в постоянный `[Run][Stop][Continue] + status`, с props Project + exact RuntimeStatus + Commands.
- Доступность: required saved identity/revision, backend capability и command delivery state. `isFetching`/12 секунд не permission gate; последний полученный снимок допускает отправку, backend решает stale OCC.
- В закрытом меню: inspector и «Завершить и отменить запуск» при cancel capability, в том числе paused/blocked. После принятия показать cancelling; новый Run только после terminal status.
- Не скрывать operational block после снятия pause и не обещать, что Continue исправит provider/выдаст Retry.

### `web/src/pages/workspace/Workspace.tsx:35–125,214–230,270–317`

- Project selection в URL/cache отдельно от execution selection. Existing `?execution=` открывает его точный project/history, не создаёт новый проект/run.
- «Создать проект» отправляет create только; workspace редактирует durable draft. History executions выбранного проекта отдельно от Project menu.
- Run при dirty draft сначала сохраняет exact draft через journal, затем после accepted revision создаёт новый Run envelope. Отдельный обязательный Save/«Проверить настройки» click не нужен. До сохранения Run envelope reload не может сам запустить генерацию.
- Никакого `project_id=uuid` + немедленного Start в Create handler. Accepted Run выбирает execution по receipt, не по перечитанному recent list.
- Один runtime-status query owner на selected execution для Pipeline/Chat. Body/activity/inspector queries грузятся по потребности, не параллельным status polling.

### `web/src/pages/workspace/model/{productionDraft,cache}.ts`, `ui/{ProductionForm,StartStoryForm}.tsx`

- Перенести durable production values в Project DTO; session cache хранит presentation/unsaved editing state, не заменяет canonical draft.
- Добавить exact graph/connection поля из ProjectDraftV1, без current-library/provider fallback. Partial text fields не теряются при reload.
- Старые session-only drafts можно показать как несохранённый ввод; не создавать execution/project автоматически из cache или при mount.

### `web/src/entities/execution/{queries,images}.ts`, `ImageCandidates.tsx`

- Сохранить принятое в 02 переключение на metadata v2/runtime-status: recorded counts/status не выдаются за проверенные bytes. Lazy original error остаётся видимой и может быть явно перечитана без мутации.
- Встраивание Project/control UI не возвращает старые polling: status shared/nonoverlapping, metadata редкий, terminal/error quiet, manual retry только GET.
- Inspector/legacy actions остаются demand-driven; не возвращать default focus/reconnect storm или background full `/process`/activity reads.

### `web/src/features/commands/ContinueControls.tsx:62–94` и scoped styles

- Удалить из нового основного UI open/review/resolve/no-op, duplicated refresh, allowed_actions list и post-Wardrobe authorization.
- Поддержанный historical handoff оставить явным изолированным действием в inspector для соответствующего старого frozen route; saved old journal продолжает доставляться. Не дублировать новые Topbar controls.
- Story approval остаётся возле exact загруженного Story; paused decision delivery объясняется status, не превращается в Continue.

## Проверка

Из `web/`:

```powershell
npm run typecheck
npm run build
npm run check:schemas
npm run check:commands
node checks/runtime-controls-check.cjs
node checks/runtime-controls-browser-check.cjs
node checks/continue-browser-check.cjs
node checks/image-browser-check.cjs
```

- [ ] Create/edit/reload без generation; Run использует сохранённую revision, double click/lost receipt не создаёт второй execution.
- [ ] Slow status polling/transient GET error не делает command availability таймерной; pending POST и реальный backend запрет блокируют нужную команду.
- [ ] Stop/Continue из двух вкладок: stale command показывает conflict/current revision, не автоматически переотправляет новую мутацию.
- [ ] Blocked→paused→Cancel из меню→terminal→новый Run; внешняя генерация может оставаться outstanding без ложного «слот свободен».
- [ ] Persisted старые Start/Continue/Cancel envelopes доставляются неизменными. Новые project/control receipts строгие и matched.
- [ ] Pipeline/Chat имеют один command/status owner; Story approval точный, metadata записанные результаты не становятся approval/byte verification.
- [ ] Desktop screenshot каждого изменённого экрана сохранён в новом `test-results/screenshots/story-workspace/vNN-runtime-controls/.../screen-state-desktop.png`, открыт и проверен; test-results index обновлён. Не снимать каждое промежуточное состояние.

Удалить обработчики/imports/styles только после поиска оставшихся callers. Проверки старых legacy surfaces менять вместе с явно изменённым UI-контрактом, не ослабляя journal/guard regressions.

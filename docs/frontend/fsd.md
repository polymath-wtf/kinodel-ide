# Frontend — FSD и владельцы

Статус: **актуальный контракт размещения `web/src`**. Поведение и визуальный язык — в [Web UI](webui.md); порядок сборки и приёмка — в [Local MVP](../roadmap-mvp.md). FSD не меняет backend ownership, route или durable delivery.

## Дерево

```text
web/
  src/
    main.tsx                      # bootstrap, providers
    style.css                     # используемые tokens/layout/component styles
    pages/workspace/
      Workspace.tsx               # URL, навигация, композиция, persistence
      model/cache.ts              # схема/defaults чтения workspace UI state
      ui/StartStoryForm.tsx        # live Start, валидация, секунды → integer ms
      ui/CharacterSelection.tsx   # выбор и чтение exact revisions для Start
    widgets/
      pipeline/                   # Flow, authored scopes/contracts, inspector/activity
      chat/                       # сохранённая идея и история решений
      characters/                 # локальная библиотека/editor, pending.ts
    features/
      commands/                   # delivery journal, hook/status, Run controls
      story-review/               # адресный draft, guards и decision UI
    entities/
      execution/                  # schemas, queries, StoryReader, approval predicate
      character/                  # schemas, exact refs/images и HTTP API
    shared/
      api/http.ts                 # validated same-origin transport/session
      ui/                         # ContextPanel, SuccessToast
      assets/background.png       # runtime asset, независимый от docs
  checks/                         # connected CJS checks и общий TS loader
  prototype/                      # standalone mock + собственный checker
  assets/                         # бинарные mock-фото; runtime их не импортирует
  dist/                           # игнорируемая пересобираемая Vite-сборка
```

## Как выбрать владельца

| Слой | Что размещаем |
|---|---|
| Bootstrap | `main.tsx`: корневой render/providers; отдельный `app` появится при реальном росте |
| Page | Композиция экранов, URL/selection, общий panel/Back, page-local формы и UI cache |
| Widget | Самостоятельная поверхность: Pipeline/inspection, Chat history, Characters editor; её локальная логика и запросы остаются рядом |
| Feature | Общее пользовательское действие/правило: exact Story review и durable command delivery |
| Entity | Доменные схемы/refs, read queries, отображение сохранённого результата и низкоуровневый typed API |
| Shared | Примитив без доменного решения: транспорт, native panel, toast, runtime assets |

Начинаем локально в page/widget. Выносим ниже при реальном повторном использовании или общей доменной ответственности. Не создаём пустые слои, сегменты `ui/model/api`, registry и forwarding-компоненты ради формального дерева.

## Импорты и точки входа

- Направление: bootstrap → pages → widgets → features → entities → shared; можно пропускать слои. Нижний слой не импортирует верхний.
- Peer slices изолированы. Page связывает StoryReview и commands через `ready/busy/onRespond`, не через импорт delivery feature в review.
- `onRespond` получает зафиксированные execution/request/digest/binding revision/base ref и action/message. Page отправляет этот target; новый snapshot не переназначает команду.
- Inspector/activity принадлежат `widgets/pipeline`, поэтому StageContract и view metadata не экспортируются в соседний widget. ContextPanel содержит только presentation/focus.
- Единственное entity cross-import: `execution/contracts.ts` использует `character/contracts.ts` для frozen selected-character snapshot. Обратной зависимости нет; `@x` пока не нужен.
- Внешние импорты идут через явные модули (`Pipeline`, `contracts`, `queries`, `StoryReader`, `StoryReview`, `useCommands`, `RunControls`, `Characters`, `api`). Внутри среза — относительные пути. Barrel `index.ts` и aliases не обязательны.

## State и доставка

- React Query владеет server snapshots и точными body queries; backend — каноническими данными. Query cache можно восстановить из API.
- Workspace владеет view/scope/viewport/node/version selection и Start/review drafts. `kinodel.workspace.v1` сохраняется в sessionStorage; cache schema/defaults и старый scope alias сохраняют ранее записанные черновики.
- Panel, opener/focus и Back history — transient. Flow ведёт pan/zoom; Workspace сохраняет viewport только на завершении gesture.
- Start form сохраняет временно невалидный текст длительности при навигации; picker монтируется только в открытой форме. Characters остаётся mounted после первого открытия, чтобы Back/rail не потеряли unsent editor и исходный OCC.
- StoryReview владеет draft target и guards; read-only StoryReader не отправляет commands. Отправка approve требует текущего exact review и прочитанного body; approved отображается только по committed review/outcome, не по существованию output.
- `features/commands/journal.ts` сохраняет endpoint/exact payload/key до POST и receipt до reconciliation. `widgets/characters/pending.ts` владеет IndexedDB save/delete envelopes и exact replay. Ошибки/401/403/terminal snapshot не разрешают удалить неизвестную доставку.
- Browser drafts и pending journals — пользовательские данные, не устаревший component cache. Очистка build/cache не меняет storage keys, refs или pending bytes.

## Проверки и материалы

`web/checks` хранит runnable checks; `load-typescript.cjs` переиспользует установленный TypeScript с единым module cache/class identity. Команды и capture-инструкция — в [web/README](../../web/README.md#checks). Playwright остаётся внешним, backend/browser roots — disposable.

Runtime build не зависит от `docs/frontend/refs`; refs остаются дизайн-источниками для mock/документации. Desktop evidence хранится в новых версиях `test-results/screenshots/story-workspace`, индекс — `test-results/README.md`, Playwright output — отдельно в `test-results/prototype`.

Основание: FSD [pages first](https://feature-sliced.design/docs/guides/migration/from-v2-0), [cross-imports/composition](https://feature-sliced.design/docs/guides/issues/cross-imports), [отложенная декомпозиция](https://feature-sliced.design/docs/guides/issues/excessive-entities). Исторический [препродакшн](story-workspace-preproduction.md) объясняет первый срез, не заменяет этот контракт.

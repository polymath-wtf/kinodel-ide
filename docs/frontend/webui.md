# Web UI — Kinodel Workspace

**[Открыть standalone-прототип](prototype/index.html) · [Запуск и сборка — web/README.md](../../web/README.md).** Живой интерактивный **MOCK, без backend**: настоящий React Flow, адаптация публичного BaseNode и semantic CSS; полный shadcn/Tailwind app не установлен. 22 scope, mock Inputs/Outputs каждого этапа, внутренние схемы агентов в стиле LangGraph и пути раскрытия ComfyUI — демонстрация навигации, не исполнения.

Статус: **прототип собран, целевой дизайн и production UI ещё не утверждены/не интегрированы**. `web/` — исходники одноразового HTML-эксперимента, не обязательный фундамент приложения. Макеты и промпты — [UI/UX wireframe](uiux-wireframe.md). Порядок сборки, pins и приёмка — только в [Local MVP](../roadmap-mvp.md). Эта страница задаёт целевой стек, визуальный язык и правила взаимодействия.

## First UI Slice

**Один запуск, два вида: `Pipeline` и `Chat`.** Снаружи — короткая дорожка творческих этапов. Каждый составной этап раскрывается в матрёшку: агент, generation tools и точный review. Canvas и результаты видны сразу; правая панель **закрыта по умолчанию** и открывается по явному запросу деталей конкретной ноды/фотографии. Решение по полному набору доступно в контексте review, без обязательной постоянной панели.

UI показывает сохранённое производство и отправляет команды. LangGraph маршрутизирует; агенты создают планы; tools выполняют эффекты; backend хранит результаты и применяет approval. Переключение вида, вход внутрь ноды и закрытие браузера не запускают работу.

## 1. Стек и проверка React Flow UI

| Слой | Выбор | Обоснование |
|---|---|---|
| Приложение | React 19 + TypeScript + Vite | SPA, static build с существующего FastAPI origin |
| Canvas | `@xyflow/react` 12 | Выбор, pan/zoom, handles, authored layout; не runtime |
| Стили | Tailwind CSS 4 + `@tailwindcss/vite` | Общие semantic tokens для canvas, инспектора и чата |
| Примитивы | shadcn/ui + React Flow UI (целевой вариант, после утверждения дизайна) | Берём нужные компоненты по мере реальных экранов, не переносим библиотеку ради mock |
| Server state | `@tanstack/react-query` 5 | Polling, reconnect, единый cache для обоих видов, mutation invalidation |
| Wire boundary | Typed `fetch` + Zod 4 | Runtime validation JSON; TypeScript cast не проверяет ответ |
| UI state | React state + React Flow | Выбранный этап, scope, viewport, вкладка и черновик сообщения |
| Навигация | Один workspace, без router на первом экране | Виды и breadcrumbs — локальное состояние; run ID сохраняется для повторного открытия |
| Иконки | Одна семья Lucide | Общий язык с shadcn; 16px внутри нод, 20px в rail, подписи/accessible names обязательны |

### Что действительно есть в референсе

[AI Workflow Editor](https://reactflow.dev/ui/templates/ai-workflow-editor) от **xyflow, команды React Flow**, построен на Next.js, React Flow UI, shadcn/ui/Tailwind, AI SDK и Zustand. Он показывает полезную композицию: Text Input → Generate Text → Generate Image, именованные порты, model selector и результат внутри ноды.

`gpt-4o-mini` и `dall-e-2` на скриншоте — примеры из шаблона, а не список поддерживаемых моделей Kinodel. Здесь selector получает доступные модели/профили из backend-конфигурации. В draft он редактируемый; после Run показывает закреплённую версию. Image/video profile включает workflow и возможности, это не просто строка с названием модели.

Шаблон скачивается через **React Flow Pro** и имеет отдельную [Pro license](https://xyflow.com/pro-license). React Flow — MIT; публичные компоненты React Flow UI доступны через registry. Для нашего концепта достаточно публичного Base Node и собственного UI. Исходники платного шаблона и его lockfile не изучались; точные версии его зависимостей не заявляются. При использовании полученных исходников сохраняем применимые notices/license.

### Решение по Next.js

**Оставляем Vite.** React Flow [рекомендует Vite для старта](https://reactflow.dev/learn); Next.js не является требованием React Flow UI. Canvas в основном интерактивный, public SEO/SSR-страниц у local workspace нет, Python уже владеет API, jobs и recovery. Vite даёт статические файлы без второго server runtime в пользовательской поставке.

SSR у React Flow возможен, но требует размеров нод и координат handles на сервере. Это отдельная возможность, а не бесплатное преимущество шаблона. Next.js имеет смысл пересмотреть при реальной потребности в RSC/SSR и отдельном web-продукте; даже hosted SPA сама по себе не требует перехода.

Не переносим AI SDK runner, Zustand, ELK или drag-and-drop palette только ради сходства с шаблоном. Здесь нет клиентского AI-исполнения, редактируемой топологии и задачи автоматической раскладки произвольных графов.

### Что проверено сейчас

- В `web/` собран standalone React Flow MOCK; исходники, зависимости и команды — в [README](../../web/README.md). Таблица выше описывает целевой production-стек, а не полный набор установленных в прототипе библиотек.
- В прототипе установлены React 19.3.0, React Flow 12.11.6 и Vite 8.0.16 (исправленный patch вместо устаревшего кандидата 8.0.10 из roadmap). Это не выбор структуры production-приложения.
- Текущие Tailwind 4.3.3 и Vite plugin 4.3.3 поддерживают Vite 8; Query 5.103.2 поддерживает React 19; Zod 4.6.5 не обнаруживает конфликта в metadata. shadcn CLI 4.21.0 проходит Node requirement.
- React Flow UI официально поддерживает React 19 / Tailwind 4. Интеграция целевого production-стека и его проверки ещё нужны на шаге 6; standalone build и registry metadata их не заменяют.

## 2. Что берём из локальных референсов

Все изображения в `refs/` — визуальные ориентиры; сгенерированные экраны не подтверждают работающие API или правильную топологию.

| Референс | Берём | Уточняем для Kinodel |
|---|---|---|
| [React Flow template](refs/react%20flow%20ui%20workflow%20template.png) | Основная палитра: нейтральный near-black, серо-белые controls; Base Node, тонкие рамки, именованные handles, model selector | Формы живут внутри раскрытого этапа/инспектора, а не в каждой внешней карточке |
| [Pipeline zbs](refs/zbs%20ref%20v1/pipeline%20zbs.png), [pipeline kaif](refs/zbs%20ref%20v1/pipiline%20kaif.png) | Короткая дорожка, простор, фон с точками, спокойный левый rail | Без постоянного инспектора и дублирования media; review виден на этапе, подробности открываются отдельно. Живописный фон — необязательный материал проекта при достаточном контрасте |
| [Wardrobe zbs](refs/zbs%20ref%20v1/wardrobe%20zbs.png) | Три ясных шага, фото непосредственно под Anchor generation | Не повторять те же фото справа; там только выбранная фотография и её детали. Portrait → sheet зависит от exact portrait, location независима |
| [ComfyUI zbs](refs/zbs%20ref%20v1/comfyui%20zbs.png), [zbss](refs/zbs%20ref%20v1/comfyui%20zbss.png) | Минимализм первого и удобочитаемость графа второго | Панель закрыта по умолчанию; связи/порты только из проверенного workflow, не из txt2img-фантазии |
| [Chat zbs](refs/zbs%20ref%20v1/chat%20zbs.png) | Узкая хронология и крупные визуальные результаты | Один actionable review, компактный адресный composer, без повторной правой панели |
| [Project hz](refs/zbs%20ref%20v1/project%20hz.png) | Чистая иерархия идеи → Run | Референс пока не утверждён: меньше формы и фиктивных профилей, подробнее — в wireframe |

## 3. Матрёшка: Nested Node

**Nested node / матрёшка** — единый раскрываемый элемент UI. Это новое название прежнего `node-pack`; визуальное раскрытие и будущая исполняемая упаковка имеют разные границы, закреплённые в [node.md](../backend/node.md).

### Уровни

| Уровень | Что видно | Что означает вход внутрь |
|---|---|---|
| L0 · Pipeline | Brief → Storytell → Wardrobe → Storyboard → Filmmaker → Montage → Final | Короткая карта производства |
| L1 · Production stage | Агент → generation tool (если есть) → Review | Точные существующие `stage_id`, отдельные статусы и результаты |
| L2 · Agent или tool | У агента: context, закреплённые инструкции/model, объявленные tools, сохранённый план. У tool: units/jobs и provider workflow | Inspection выбранного владельца/задания |
| L3 · Provider workflow | Например, mapped inputs → encode/sample/decode → verified output | Read-only детали конкретного workflow/job; не граф Kinodel |

Один React Flow canvas показывает **один scope за раз**. Не вкладываем живой `<ReactFlow>` внутрь каждой ноды. Breadcrumbs возвращают назад с прежними viewport и выбором. `parentId`/subflows нужны для одновременного отображения групп на одном canvas, но drill-down сам по себе их не требует.

### Свернутый cinematic без потери границ

| Внешняя карточка | Содержимое / backend identity | Смысл summary |
|---|---|---|
| Brief | `brief` | Submitted input |
| Storytell | `storytell → story-hitl` | Story + её review |
| Wardrobe | `wardrobe → anchor-gen → anchor-hitl` | План, генерация якорей, выбор полного набора |
| Storyboard | `storyboard → frames-gen → frames-hitl` | Image prompts и начальный кадр каждого shot |
| Filmmaker | `filmmaker → video-gen → video-hitl` | Motion prompts, videos и review |
| Montage | `montage` | Детерминированная сборка; внутри видны inputs и проверка файла |
| Final | `final` — поверхность результата Montage | Player/download; не новый агент или финальный approval |

Это фиксированная **view-группировка** существующего маршрута. Например, canvas ID `view:wardrobe` не записывается вместо `stage_id=wardrobe` или `anchor-hitl`. У группы нет своего execution, approval, binding или процента выполнения.

Summary берётся из активного вложенного этапа: `Generating · 2/3 units` только при наличии подтверждённых счётчиков; `Review anchors · set 2` при actionable gate. Ошибка/блок вложенного этапа остаётся видимой с его именем. `Complete` появляется после завершения всех обязательных шагов группы, включая применение решения. Завершённый вызов агента не завершает матрёшку.

### Правила раскрытия

- Один click/keyboard selection выделяет ноду; `Open inside` входит в scope, `Details` явно открывает панель. На фото click/Enter открывает его детали справа; закрытие возвращает focus/ширину canvas. Double-click — только дополнительный shortcut.
- Если ждём решения, `Open review` ведёт к текущему результату и точному review inline либо в широком sheet; сам переход ничего не утверждает.
- Breadcrumbs: `The Magic begin / Wardrobe / Anchor generation / hero_sheet / Workflow`. Длинные пути сворачиваются, текущий unit остаётся виден.
- `Pipeline` и `Chat` сохраняют один execution и выбранный предмет. Возврат из чата восстанавливает canvas scope; ссылка из review-карточки открывает её этап.
- Вся топология фиксирована. Add/delete/connect/reconnect запрещены; pan/zoom разрешены. Статическая раскладка authored для каждого небольшого scope.
- Детали логики — объявленные входы, подготовленные инструкции, вызовы tools и сохранённые ответы. Не рисуем выдуманную цепочку скрытого reasoning и не показываем фиктивные live-статусы внутренних шагов.

## 4. Семантические типы нод

Один Base Node shell, пять вариантов содержимого. Матрёшка — возможность раскрыться, не шестой исполнительный тип.

| Вариант | Внешний вид | Порты и детали |
|---|---|---|
| Input | Название + короткий текст/thumbnail | Только output; Brief, context/ref/parameter внутри inspection |
| Agent | Иконка роли, имя, status, output summary, `Open inside` | Typed inputs → validated plan; model/settings в Config |
| Tool | Иконка инструмента, provider badge, job/unit summary | План + refs + frozen profile → candidates/result; ComfyUI и Montage |
| Review | `Your decision`, exact subject, отдельный request revision | Полный предмет review → approved selection; явное решение рядом с результатом или в review sheet |
| Output | Результат, version, thumbnail/player | Только input; selected/approved/candidate подписываются раздельно |

В L0 карточка компактна: имя, один понятный status, действие раскрытия; summary только если добавляет новую информацию. В L1/L2 — читабельное имя, состояние и при необходимости один preview; не повторять там же полный результат. Длинные prompts, job IDs и advanced parameters скрыты в `Details`, без обрезанного микротекста и одинаковых play/delete-кнопок на каждой ноде. Важные labels читаемы на **начальном рабочем масштабе**: не делать 65% zoom стартовым только ради `Fit`; overview допускает панорамирование, а текстовые подробности остаются в `Details`.

Порты снаружи — краткое резюме boundary, не исчерпывающий список зависимостей. Полные exact inputs доступны в Inputs. Линия L0 обозначает порядок этапов; dependency lines внутри scope обозначают конкретные named inputs и имеют подписи. Провод не является командой.

## 5. Инспектор, настройки и действия

**Контекстная правая панель, закрыта по умолчанию:** открывается только для выбранного фото или по `Details` ноды. В ней header и нужный для предмета раздел `Config / Inputs / Outputs`; desktop около 360px, на узком экране — sheet. Не показываем все три раздела одновременно и не повторяем contact sheet/preview, уже видимые на canvas. Review нескольких фото разворачивается в широкий sheet; кнопка Approve связана с полным точным предметом, а не с выбором одного фото.

| Вкладка | Содержимое | Редактирование |
|---|---|---|
| Config | Назначение, model/profile, instruction/workflow version, разрешённые параметры | До Run — только поддерживаемые поля. В execution — закреплённые значения read-only |
| Inputs | Exact upstream refs и роли; пользовательский контекст; у job фактически переданные prompt/seed/dimensions | Выбор refs в draft только при поддержке backend; prepared input не заменяется на latest |
| Outputs | Preview/contact sheet, versions, provenance, approval state, техническая проверка | Выбор кандидатов в текущем review, затем отдельное подтверждение |

Явное открытие деталей текущего review начинает с Outputs; детали новой draft-ноды — с Config. Переключение вкладки не теряет draft сообщения или candidate selection. При обновлении предмета старый draft сохраняется как неприменённый; отправка требует повторной проверки новой версии.

`Discuss with Wardrobe` доступен рядом с review или в Chat, с переключателем `Ask / Request changes`. Это один разговор об exact subject, не второй чат внутри постоянного инспектора и не четвёртая вкладка `Chat / Logs / History`.

| Действие | Что отправляем / показываем |
|---|---|
| Approve | Явная кнопка `Approve Story v2` / `Approve anchor set 2`; exact subject и полная selection |
| Request changes | `revise` текущему owner; новый результат требует нового approval |
| Ask | `clarify`; ответ может открыть новый request на прежнем output |
| Regenerate | Только где backend объявляет действие, сначала anchor review; тот же prompt, новые seeds с учётом зависимостей |
| Retry | Техническое восстановление разрешённого work/job с прежними inputs; не creative reroll |
| Cancel run | Отдельное управление запуском; `cancelling` до authoritative terminal outcome |

У historical output нет активного Approve. Approved ancestor или frozen configuration меняются в новом execution. Неподдерживаемые изменения не выглядят редактируемыми. Ключи, произвольные provider URLs, raw payloads и queue internals не попадают в обычный инспектор.

### Wardrobe и ComfyUI

Wardrobe сохраняет `wardrobe_plan`; `anchor-gen` делает рендер и единолично записывает media binding. UI может собрать их под общей карточкой Wardrobe, но не превращает творческий агент в долгоживущий render worker.

Contact sheet показывает, например, `hero_face`, `hero_sheet`, `location`. Это **пример**, не фиксированное число: keys/count приходят из плана. Sheet хранит ссылку на exact face; несовместимый выбор объясняется рядом с парой. Генерация MVP последовательная, даже если схема показывает независимую location. Новый face требует нового sheet; location может сохраниться.

Внутри Wardrobe фото/слоты находятся **под Anchor generation прямо на canvas**, без второго такого же набора в sidebar. Во время работы незаполненный слот показывает компактный spinner + `Generating…` и реальное состояние (`Waiting on portrait`, `Queued`, `Verifying`); после verified import — candidate image. При ошибке показать причину вместо бесконечного спиннера. Click/Enter по конкретной фотографии открывает справа только её крупный preview, exact ref/lineage и доступные действия. Отдельный review полный набор сверяет и подтверждает вместе.

ComfyUI — **Tool с раскрытием внутри `anchor-gen` / `frames-gen` / `video-gen`**, если закреплённый provider именно ComfyUI. Workflow scope относится к выбранному job/unit; разные роли могут использовать разные workflows. В L0 нет обязательной глобальной ноды ComfyUI.

Сначала показываем читаемый read-only граф/semantic inputs и один output на canvas; inspector закрыт, техническая конфигурация доступна по `Details`. Детальный граф — только из проверенной, sanitised adapter projection; credentials/paths скрыты. Если данных нет, пишем `Workflow details unavailable`, а не генерируем похожую схему. Не нужен встроенный ComfyUI editor/iframe. Параметры sampler/latent/VAE не возникают у workflow, который их не имеет. Decode/Save ещё не означают импорт, выбор или approval результата.

## 6. Chat — второй вид того же запуска

Это спокойная вертикальная **лента производства**, а не новый глобальный агент. Верх: название/run status и компактная строка этапов. Середина: пользовательский brief, сохранённые ответы владельцев, карточки результатов и decisions. Низ: composer, явно адресованный `To Wardrobe · anchor set 2 · request r4`.

- Текущий review содержит тот же preview, версии и точные действия, что Pipeline. Оба вида используют один query cache, компоненты и mutation handlers.
- Mode `Ask`/`Request changes` выбирается явно. Сообщение «ок» ничего не утверждает. Approve существует только отдельной кнопкой на карточке.
- Пока run выполняется, показываем одну обновляемую activity-строку; не засоряем ленту polling-событиями и не выдаём status за ответ агента.
- Если actionable review нет, composer объясняет, когда станет доступен. Brief до Run редактируется в стартовой форме; полноценный свободный чат/очередь сообщений не заявлены.
- Historical cards read-only, свёрнуты до заголовка и версии; `View in pipeline` открывает связанный предмет. Во время чтения истории новое сообщение не отбирает scroll/focus.
- Результаты представлены текстом, contact sheet, video player или final download. Чат не должен требовать открыть canvas, чтобы выполнить весь автоматизированный pipeline с обязательными решениями.
- На узком экране Chat — рекомендуемый стартовый вид. Автоматизация между gates не отменяет обязательных human approvals.

## 7. API: реальность и необходимые проекции

По коду `backend/api.py` на 25 сентября доступен **internal Story fixture**: session bootstrap, start, execution read, immutable Story read, respond (`approve/revise/clarify`), retry и cancel. Discussion с typed owner responses уже есть в исходниках. Некоторые статусы backend-документов ещё описывают clarify как pending; это расхождение с кодом, не повод убирать его из концепта. Полная runtime-приёмка не проводилась этим frontend-аудитом.

| Уже можно проверить на fixture | Ещё требуется для полного экрана |
|---|---|
| Story versions, current review, request digest, work/status, persisted discussion | Cinematic stage projection и public Brief start |
| Exact approve/revise/clarify; retry/cancel | Model/profile readiness и разрешённые настройки |
| Poll/reconnect того же execution | Jobs, assets/previews, candidate manifests/selection, workflow inspection |
| `review.revision` отдельно от `binding_revision` | Allowed actions/remaining budgets, полная review history и base-result refs discussion |

Story approval завершает **fixture**, а не запускает Wardrobe. Нельзя рисовать остальные этапы как реально выполненные. Отдельный visual specimen всего cinematic маркируется `Demo data`. Наличие `cinematic.v1.json` не означает наличие исполняемого frontend/backend compiler.

Минимальная целевая read projection: run identity/status + frozen route; stages с `stage_id/kind/owner/status`; exact input/output refs; current review subject/request/digest/allowed actions; versioned candidates/selection; jobs с достоверным progress; discussion с порядком и subject refs; command/work outcome. Это требования к API, не объявление новых endpoints/готового DTO. Большие media bodies не грузятся в graph nodes; preview загружается по авторизованной ссылке и exact ref.

### Командный цикл

1. Получить localhost session/CSRF, затем authoritative execution read. Dev proxy использует тот же контракт; не отключать Host/Origin/CSRF ради Vite.
2. Валидировать ответ. Преобразовать его в view nodes; UI state не записывать в artifact/graph state.
3. Poll активный/waiting/blocked run, refetch при reconnect/focus; после terminal прекратить interval. Status и connection freshness — отдельные вещи.
4. Зафиксировать command payload + key **до отправки**. Повтор после потерянного ответа использует тот же payload/key; не создавать новую правку автоматически. Минимальный pending envelope хранится до reconciliation, чтобы reload не потерял identity отправки.
5. В текущем Story API `expected_revision = review.binding_revision`, **не** `review.revision`. `request_id` и digest фиксируют конкретный request. У retry — work ID + work version. Не переносить эти DTO на ещё не реализованный media API без контракта.
6. HTTP 202 означает принятие; UI показывает `Applying…`, затем читает committed state. Запретить повторную отправку с той же карточки в обоих видах. Не делать optimistic approval/result.
7. Stale/conflict/budget exhaustion — refetch, сохранить draft и показать причину. Не переназначать старое сообщение новому review автоматически. При offline/reconnecting действия заблокированы; чтение последнего snapshot доступно.

## 8. Визуальная система — Quiet Graphite

**Нейтральный near-black и графит, ясная геометрия, сдержанное серо-белое выделение** по React Flow template. Цвет в основном дают кадры фильма; только фон canvas допускает мягкие рассеянные blue-gray / warm stone поля с тонким зерном, вдохновлённые colour-field graphic art. Интенсивность атмосферы регулируется вплоть до отключения. Без свечения нод/проводов, стекла, serif-заголовков и медной editorial-темы. Внешний pipeline компактный; пространство оставляем вокруг пути, а не внутри пустых карточек.

| Token | Dark (основной концепт) | Light |
|---|---|---|
| Canvas/background | `#101012` | `#F5F6F7` |
| Card / panel | `#19191C` | `#FFFFFF` |
| Secondary surface | `#23272C` | `#E8EBEE` |
| Structural border | `#383E46` | `#D0D5DA` |
| Text | `#F1F3F5` | `#171A1E` |
| Muted text | `#A5ADB8` | `#535D68` |
| Primary / selection | `#E4E4E7` | `#3F3F46` |
| Primary text | `#18181B` | `#FFFFFF` |
| Canvas atmosphere (low-opacity only) | Blue-gray `#647080`, warm stone `#8A8075` | Те же приглушённые оттенки |
| Focus/control outline | `#89939F` | `#63707D` |
| Error text | `#FF9B9B` | `#A51D2D` |
| Review text | `#EBCB82` | `#765300` |

Primary зарезервирован для выбора и главного действия, amber — `Your decision`, red — ошибки. Completed достаточно check + текста; завершённые провода остаются нейтральными. Neutral border разделяет поверхности; focus/control outline используется там, где граница нужна для распознавания интерактивного элемента.

- **Шрифт:** self-hosted `IBM Plex Sans` с реальным Cyrillic subset, если интерфейс русскоязычный; моноширинный для refs/revisions при необходимости. Основной текст 14/20, вторичный не меньше 12/16 при рабочем масштабе, node title 14/20 semibold, section title 18/24. В текущем mock импортирован только Latin subset — это пока не доказательство готовности кириллицы.
- **Геометрия:** 4px spacing grid; 12px node/panel radius, 8px controls; rail 56px, header 56px, breadcrumbs 40px. Controls 36px desktop / минимум 44px touch.
- **Canvas:** деликатные точки поверх регулируемого grainy gradient, как в `pipiline kaif.png`; полноэкранный scenic background необязателен, не должен съедать контраст нод. Атмосфера только на canvas, панели и ноды непрозрачные, без glow. Edges 1.5px нейтральные, named handles 8px. Нет декоративных пунктирных потоков по всему экрану. MiniMap только по запросу, controls — zoom / fit / current stage.
- **Media:** `object-fit: contain` на review, ratio box без обрезки важных частей; маленький cover-thumbnail допустим на внешней карточке. Video не autoplay; сеть не перегружается десятками mounted players.
- **Motion:** 120–160ms opacity/transform для панели/selection. Не анимировать сам layout нод при polling, не делать постоянные pulses. Reduced motion отключает переходы; progress — текст, когда процент неизвестен.
- **Responsive:** ≥1280 rail + canvas/chat, панель только по запросу; 768–1279 details/review как sheet; <768 Chat по умолчанию, детали full-screen, Pipeline доступен с pan/zoom. Ниже 1280 не сжимать одновременно ноды и панель до нечитаемости.
- **Accessibility:** текст у каждого статуса; видимый focus, подписи icon buttons, keyboard `Open inside`/Back, доступный список этапов рядом с canvas controls. Нельзя заставлять пользователя double-click или различать только цвет. Sheet возвращает focus к вызвавшей кнопке; toast не единственное место ошибки.

## 9. React Flow UI: публичный код и Kinodel shell

Ниже **reference для целевой production-реализации** с Tailwind/shadcn; собранный прототип использует адаптацию BaseNode с semantic CSS (см. [атрибуцию](../../web/README.md#public-component-attribution)). Использованы настоящие exports публичного [Base Node registry](https://ui.reactflow.dev/base-node): `BaseNode`, `BaseNodeHeader`, `BaseNodeHeaderTitle`, `BaseNodeContent`, `BaseNodeFooter`. Варианты Kinodel и callbacks — наша адаптация, не код платного шаблона.

После настройки Vite, `@/*`, Tailwind и shadcn в `web/`:

```sh
npx shadcn@4.21.0 add https://ui.reactflow.dev/base-node
```

Registry source коммитится вместе с приложением и сохраняет applicable notices. CLI command сам по себе не pin содержимого registry. Остальные packages устанавливаются exact из roadmap; это не команда установки в текущей documentation-задаче.

### `KinodelNode.tsx` — один shell для всех ролей

```tsx
import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import {
  BaseNode, BaseNodeHeader, BaseNodeHeaderTitle,
  BaseNodeContent, BaseNodeFooter,
} from "@/components/base-node";

type NodeData = {
  title: string;
  kind: "Input" | "Agent" | "Tool" | "Review" | "Output";
  status: string; // human-readable label from the validated projection
  summary: string;
  input?: string;
  output?: string;
  nested: boolean;
  onOpen: () => void; // view-only callback: never an execution command
};

export type KinodelFlowNode = Node<NodeData, "kinodel">;

export const KinodelNode = memo(function KinodelNode({
  data, selected,
}: NodeProps<KinodelFlowNode>) {
  return (
    <BaseNode className="kinodel-node w-[208px]" data-selected={selected}>
      {data.input && (
        <Handle id="in" type="target" position={Position.Left}
          isConnectable={false} aria-label={`Input: ${data.input}`} />
      )}
      <BaseNodeHeader className="gap-2 px-3 py-2">
        <span className="text-xs text-muted-foreground">{data.kind}</span>
        <BaseNodeHeaderTitle className="min-w-0 truncate text-sm">
          {data.title}
        </BaseNodeHeaderTitle>
      </BaseNodeHeader>
      <BaseNodeContent className="space-y-1 px-3 py-2">
        <p className="text-sm">{data.status}</p>
        {data.summary && <p className="text-xs text-muted-foreground">{data.summary}</p>}
      </BaseNodeContent>
      <BaseNodeFooter className="px-3 py-2">
        <button type="button" className="nodrag nopan node-open"
          aria-label={`${data.nested ? "Open inside" : "Details"} ${data.title}`}
          onClick={(event) => { event.stopPropagation(); data.onOpen(); }}>
          {data.nested ? "Open inside" : "Details"} <span aria-hidden>↗</span>
        </button>
      </BaseNodeFooter>
      {data.output && (
        <Handle id="out" type="source" position={Position.Right}
          isConnectable={false} aria-label={`Output: ${data.output}`} />
      )}
    </BaseNode>
  );
});

// Module-level identity, not a fresh object on each render.
export const nodeTypes = { kinodel: KinodelNode };
```

`data` здесь — view model, не backend DTO: callbacks добавляются в UI adapter и не сериализуются. `nested` задаёт только навигацию. Review показывает отдельную явную кнопку Approve у полного предмета решения. В подробном scope labels портов рендерятся рядом с handles; несколько портов получают стабильные уникальные IDs, edges указывают `sourceHandle/targetHandle`. При динамическом изменении handles требуется `useUpdateNodeInternals`.

### Canvas boundary

```tsx
import {
  Background, Controls, ReactFlow, type Edge, type OnNodesChange,
} from "@xyflow/react";
import { nodeTypes, type KinodelFlowNode } from "./KinodelNode";

export function PipelineCanvas({ nodes, edges, onNodesChange, colorMode }: {
  nodes: KinodelFlowNode[];
  edges: Edge[];
  onNodesChange: OnNodesChange<KinodelFlowNode>;
  colorMode: "light" | "dark";
}) {
  return (
    <div className="h-full min-h-0 min-w-0" aria-label="Production pipeline">
      <ReactFlow<KinodelFlowNode>
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        onNodesChange={onNodesChange} colorMode={colorMode}
        nodesDraggable={false} nodesConnectable={false}
        edgesReconnectable={false} deleteKeyCode={null}
        fitView minZoom={0.5} maxZoom={1.5}
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
```

Workspace задаёт canvas реальную высоту через `100dvh` grid с `minmax(0, 1fr)`. Родитель хранит controlled nodes и применяет `onNodesChange` через `applyNodeChanges` (или `useNodesState`), включая keyboard selection; выделение **не** открывает inspector автоматически. Кнопка `Details` или click/Enter по фото раскрывает его явно. Adapter задаёт accessible `ariaLabel` каждой ноде и сохраняет выбор при polling. `colorMode` получает разрешённую общую тему workspace, чтобы встроенные Controls не оставались светлыми в dark UI. `fitView` нужен при первом входе в scope, не при каждом polling update. В приложении сохраняем viewport по scope; browser Back/явная Back не должны запускать работу. Pan не заменяет доступный список этапов.

### Общие tokens и минимальные overrides

В глобальном CSS `@import "tailwindcss";`, необходимые shadcn styles, затем `@import "@xyflow/react/dist/style.css";` — **до обычных CSS rules**. React Flow CSS не импортировать отдельно из `App.tsx`. Далее shadcn `@theme inline` связывает semantic utilities с переменными; существующие token names сохраняются:

```css
:root {
  --background: #f5f6f7;
  --foreground: #171a1e;
  --card: #ffffff;
  --card-foreground: #171a1e;
  --muted: #e8ebee;
  --muted-foreground: #535d68;
  --border: #d0d5da;
  --primary: #3f3f46;
  --primary-foreground: #ffffff;
  --ring: #3f3f46;
  --control-outline: #63707d;
}
.dark {
  --background: #101012;
  --foreground: #f1f3f5;
  --card: #19191c;
  --card-foreground: #f1f3f5;
  --muted: #23272c;
  --muted-foreground: #a5adb8;
  --border: #383e46;
  --primary: #e4e4e7;
  --primary-foreground: #18181b;
  --ring: #e4e4e7;
  --control-outline: #89939f;
}
.react-flow {
  --xy-background-color: var(--background);
  --xy-edge-stroke: var(--control-outline);
  --xy-edge-stroke-width: 1.5;
}
.kinodel-node {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--card);
  color: var(--card-foreground);
  box-shadow: none;
}
.kinodel-node[data-selected="true"] { border-color: var(--primary); }
.node-open {
  min-height: 36px;
  border-radius: 8px;
  color: var(--foreground);
  padding: 0 8px;
  text-align: left;
}
.node-open:hover { background: var(--muted); }
.node-open:focus-visible { outline: 2px solid var(--ring); outline-offset: 2px; }
@media (pointer: coarse) { .node-open { min-height: 44px; } }
@media (prefers-reduced-motion: no-preference) {
  .node-open { transition: opacity 140ms ease; }
  .node-open:active { opacity: .8; }
}
```

Это не полный theme reset: popover, input, destructive и остальные shadcn tokens приводятся к той же палитре при сборке. Theme выбирается на корне всего workspace (`system / dark / light`), не отдельно в разных панелях. Проверка контраста обязательна для обоих вариантов.

## 10. Структура приложения и FSD

Сейчас `web/src/App.tsx`, `data.ts` и `styles.css` — единый эксперимент для сборки HTML, не шаблон структуры production. Нужно создать FSD перед утверждением дизайна, чтобы писать код в заведомо известной архитектуре. Прежний минимальный webui прямо откладывал обязательную шестислойную Mini-FSD, по пора занятся ей.

Для production принимаем **принцип Feature-Sliced Design**: экран/workspace собирает виджеты, пользовательское действие (`review`, обсуждение) владеет своим UI и запросом, `execution`/`artifact` — только типизированными read projections, общие низкоуровневые примитивы лежат отдельно. Не создаём `pages/widgets/features/entities/shared` заранее ради дерева папок: выделяем срез, когда появляется реальный Story review с API и второй потребитель того же поведения в Pipeline/Chat. Размещение данных определяется их владельцем, не названием картинки или типа ноды. Разрешённые зависимости направлены к более общим слоям; экран не становится местом хранения mock runtime и команд всех фич. FSD описывает организацию клиентского кода, не меняет backend route и ownership.

## 11. Граница следующей сборки

Сначала утвердить компактный HTML-дизайн без дублирующей панели; затем решить, переиспользовать ли React Flow shell из `web/` и как подключить общий Story review и Chat/Pipeline к реальному fixture. Mock-данные, копирайтинг, CSS, scripted approval и single-file сборка не являются production-контрактом. Дальше расширять workspace по мере готовности cinematic projection. Фиксированные матрёшки — view navigation первого концепта; произвольная упаковка, graph editor, palette, общий project chat и ComfyUI editor не нужны для этого прохода.

Все рабочие задачи/критерии находятся в [шаге 6 и приёмке roadmap](../roadmap-mvp.md#remaining-steps). Здесь не ведём второй checklist. Минимальные browser checks должны подтвердить одинаковый exact review в двух видах, сохранение scope при навигации, отсутствие duplicate command при reconnect, явное отличие candidate/selected/approved и доступность на узком экране.

## Источники

Проверено 25 сентября 2026 по официальным страницам, публичному registry и npm metadata:

- [React Flow UI](https://reactflow.dev/ui), [AI Workflow Editor](https://reactflow.dev/ui/templates/ai-workflow-editor), [Base Node](https://reactflow.dev/ui/components/base-node).
- [Custom nodes](https://reactflow.dev/learn/customization/custom-nodes), [Handles](https://reactflow.dev/learn/customization/handles), [SSR](https://reactflow.dev/learn/advanced-use/ssr-ssg-configuration).
- [shadcn + Vite](https://ui.shadcn.com/docs/installation/vite), [Vite](https://vite.dev/guide/), [Pro license](https://xyflow.com/pro-license).
- Контракты Kinodel: [node](../backend/node.md), [cinematic](../pipelines/cinematic.md), [HITL](../hilp/hilp.md), [ComfyUI](../backend/comfyui.md), [текущий API source](../../backend/api.py).

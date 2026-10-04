# UI/UX-аудит — меньше оболочки, больше производства

Дата: **4 октября 2026**. Статус: **аудит → UX1–UX5 → пользовательские правки → Characters/Projects → исправление draft/layout реализованы и проверены**. Разделы 1–6 — исходный аудит/proposal, раздел 7 — первая итерация; **текущее поведение и evidence — в разделах 8–10**. Пользователь одобрил предыдущий результат; visual approval последней версии ещё не заявлено.

Проверены два пользовательских скриншота из `refs/na pravki/`, текущие `web/src`, `web/prototype/index.html`, UI-контракты и браузерная геометрия. Десктопные снимки: [v31-ux-audit](../../test-results/screenshots/story-workspace/v31-ux-audit/), все восемь просмотрены. Backend/библиотека изолированы, remote transport замокан; навигация UI не отправила ни одного POST. Это UX-проверка, не повтор полной функциональной приёмки.

## Вывод

Основная проблема — **одни и те же сведения получают несколько отдельных поверхностей**, а результат уступает место диагностике. Нужны одна верхняя строка управления, canvas сразу под ней и контекстные детали справа. Сохранение/review/retry уже работают; для упрощения оболочки новый backend не нужен.

Второй пользовательский скриншот показывает **modal Story reader**, не toast. В исходниках нет отдельной toast-системы: сообщения доставки выводятся inline через `DeliveryStatus`. Замена библиотеки уведомлений не исправит блокирующий reader.

## 1. Проверенные потери площади

| Проверенный viewport | Геометрия текущего интерфейса |
|---|---|
| 1440×900, Pipeline | Topbar 60px; строка запуска 52px; progress с отступами 92px; scope toolbar 60px; пояснение 19px. Canvas начинается на **y=283**, высота **617px**, 69% высоты экрана. |
| 820×900, Pipeline | Canvas начинается на **y≈436**, высота **≈464px**: около 52% экрана. |
| 390×900, Pipeline | Canvas начинается на **y≈611**, высота 280px, но рабочая область заканчивается на y=832. До прокрутки видны только **≈221px** canvas; его низ уходит под нижнюю навигацию. |
| 1440×900, Story review | Modal 840×836px. Сам reader начинается на **y=553**, review/composer — на **y≈1071**, за первым экраном. |

При единственном header 60px теоретический desktop canvas — 840px: **+223px / +36% к текущей высоте**. Это расчёт предлагаемой геометрии, не достигнутый результат. Карточки дополнительно стоят на authored `y=175` (`Pipeline.tsx:104`): после удаления полос нужно перепроверить начальный viewport, иначе пустота над нодами останется.

## 2. Что убрать, перенести и оставить

| Приоритет / элемент | Проблема | Минимальное изменение |
|---|---|---|
| P0 · Строка запуска | Статус, связь, данные, Run, список, создание и тестовые действия образуют второй header. | Run-status и глобальные действия — в topbar. `Данные запуска`, поддерживаемые Retry/Cancel и тестовый Start — внутри меню запуска. |
| P0 · Большой `Идея → Storytell → ваше решение` | Повторяет статус ноды и объяснение scope; существует ещё и внутри reader. | Убрать постоянный banner. На Storytell оставить actionable status и **«Проверить Story v1»**; после approval — **«Читать Story v1»**. Сообщение о недоступном продолжении — рядом с результатом. |
| P0 · Отдельные `Pipeline` и scope-note | Название вида уже известно; постоянное пояснение разработки занимает ещё две полосы. | Проект + короткий breadcrumb — в topbar. Ограничения текущего среза — в стартовой форме/контекстных деталях, при проблеме — короткая локальная причина. |
| P0 · Details | Обычный просмотр настроек блокирует всю рабочую область затемнением. | На desktop правый **неблокирующий** inspector около 360–400px, закрытый по умолчанию; ниже 1280px sheet. Одна панель для выбранного предмета, без параллельных окон. |
| P0 · Story reader | Progress → Activity → исходная идея → история решений идут раньше результата. | Текст Story первым. Идею, модель/промпт, exact refs и решения — в раскрытия после результата/в соответствующие детали. Footer решения доступен без поиска внизу длинного документа. |
| P1 · Pipeline/Chat в topbar и rail | Две навигации с одинаковым назначением; лишние Tab-остановки. | Сохранить переключатель **Pipeline / Chat** сверху. Rail использовать для самостоятельных поверхностей, сейчас Characters; будущие пункты показывать при активации. Не оставлять широкую почти пустую rail только ради одного пункта. |
| P1 · Кнопки внутри нод | Каждая заканчивается одинаковым крупным `Открыть этап`, хотя сама нода тоже реагирует на click. | Одно понятное действие раскрытия на ноде; для текущего review — конкретное действие. Уменьшить визуальный вес, сохранить keyboard/focus и доступные имена. |
| P1 · Служебные summary | `story-hitl`, `wardrobe → anchor-gen → anchor-hitl` объясняют разработчику топологию вместо содержимого. | Storytell: короткая выдержка Story + версия. Недоступные этапы: спокойный статус; технический маршрут внутри inspection. Семь стадий сохранить. |
| P1 · Нормальная связь | `На связи / Обновляем…` постоянно конкурирует с состоянием работы. | Здоровую связь показывать тихо или по запросу; offline/read failure — заметно. Свежесть снимка и execution status остаются разными данными. |
| P1 · Start | Несколько вводных объяснений до идеи, technical shot IDs и миллисекунды, постоянно открытый пустой picker. | Идея первой, короткий model/readiness, необязательный выбор персонажей компактно. Длительность показывать в секундах с конвертацией на API-boundary; shot keys — расширенная настройка, сохранить существующий exact payload. |
| P1 · Characters | `Audio · позже` / `Video · позже` выглядят как действия, но ничего не делают. | Убрать будущие кнопки до активации. Revision сохранить, длинный subject ID раскрывать по запросу; это требует поправки текущего требования о видимом ID. |
| P2 · Request graph | Неиспользуемый ToolNode и несколько пояснений `не trace / не approval` занимают пространство. | Если схематический ToolNode нужен для inspection — показывать по запросу, не как действующего участника. Сохранить честную границу END ≠ approval. |

**Не переносить Approve в глобальный topbar:** он относится к прочитанной exact Story/полной candidate selection. Глобальны создание, открытие запуска и управление запуском; творческое решение находится рядом со своим результатом.

## 3. Предлагаемая минимальная композиция

```text
KINODEL  [Проект / открыть другой ▾]  / Storytell    [Статус · Run ▾] [+ Новая] [Pipeline | Chat]
─────────────────────────────────────────────────────────────────────────────────────────────
Rail     Рабочий canvas: один scope, ноды и связи      │ Правая панель — только по запросу
         без progress/banner/второй шапки             │ Story v1 · требует решения       ×
                                                      │ Завязка → История → Кадры ▾
         [Brief] → [Storytell] → [Wardrobe] → …        │ Персонажи / История / Детали ▾
                     Проверить Story v1                │
                                                      │ [Обсудить ▾] [Утвердить Story v1]
         [−] [+] [Fit] [Текущий этап]                 │ footer, привязанный к exact subject
```

- Проектный dropdown открывает сохранённые запуски: заменяет отдельную кнопку, не добавляется к ней.
- Inspector для metadata узкий. **Story reader шире: ориентир 480–560px на широком desktop**, текст 14px с нормальным межстрочным интервалом. Проверить остаточную ширину canvas; не пытаться уместить всю семинодовую дорожку микрошрифтом. Панель уменьшает viewport, pan/Current возвращают текущий этап; закрытие восстанавливает прежний viewport.
- Полное чтение Story доступно также в существующем Chat. Для media-set review сохраняется широкий focused sheet: панель одного фото не заменяет проверку полного набора.
- В Chat один текущий результат и один адресный composer. Техническая activity не стоит над результатом; историю старых результатов можно раскрыть. Не требуется второй чат в inspector.
- Narrow/mobile: один способ переключения вида, основное создание и меню сверху; остальные действия в меню. Chat остаётся default. Не переносить весь существующий ряд кнопок в topbar без сворачивания: это повторит текущую проблему на 820px.

## 4. Уведомления: место определяется смыслом

| Событие | Поверхность | Пример понятного текста |
|---|---|---|
| Короткое подтверждение обычного действия | Неблокирующий toast справа снизу, 320–360px, 1–2 строки, около 4s; пауза при hover/focus; не более двух одновременно. | `Персонаж сохранён · версия 2` |
| Команда принята, работа продолжается | Состояние отправленной кнопки/предмета; successful receipt в деталях. | `Правка принята. Storytell обновляет историю.` |
| Backend применил approval | Статус exact результата; необязательное краткое подтверждение. | `Story v2 утверждена` — только после authoritative read. |
| Выполнение или ожидание review | Карточка этапа / текущего результата. | `Создаём историю…` / `Story v1 готова к проверке` |
| Ошибка поля | Под соответствующим полем. | `Добавьте хотя бы одно изображение.` |
| Неизвестно, принял ли сервер команду | Постоянное сообщение рядом с действием, без auto-dismiss; exact повтор существующего envelope. | `Подтверждение не получено. Отправка сохранена. [Повторить отправку]` |
| Offline, read failure, storage denial | Постоянная компактная причина у заблокированных действий / в header при глобальной проблеме. | `Нет связи. Показаны сохранённые данные; отправка недоступна.` |
| Подробности Story/model/inputs | Правая панель по явному открытию, не toast. | `Story v2` / `Модель и входы` |

Не показывать пользователю `Snapshot не заменяет receipt`, `Applying`, `exact payload`, `body/metadata`, `reopening`, `binding_revision` в основных сообщениях. Технические данные доступны по «Подробности». Не скрывать неподтверждённую доставку за исчезающим toast и не превращать receipt в «Готово». Не нужна отдельная notification center/новая очередь/библиотека тостов для этого среза.

## 5. Документация против реализации

| Контракт / evidence | Фактическое состояние | Как трактовать |
|---|---|---|
| `webui.md:132`, правый desktop inspector | `ExecutionDetails.tsx:10` вызывает `showModal()`, CSS задаёт центрированный 720px dialog. | **Реальное расхождение presentation.** Вернуть inspector. |
| `webui.md:108`, inline или широкий review sheet | Story review — modal 840px; сам по себе разрешён. | Проблема — порядок содержимого и блокировка для обычного чтения. Правый Story reader — предлагаемое уточнение, не уже существующее требование. |
| `webui.md:126`, Storytell с текстовой выдержкой | `Pipeline.tsx:95` выводит `Story v1 · story-hitl`. | **Отсутствует полезный preview**, заменить technical summary. Не грузить большой body в graph state. |
| `webui.md:231`, zoom/fit/current | `Pipeline.tsx:145` содержит только стандартные zoom/fit. | **Current stage отсутствует**; полезнее постоянного banner. |
| `webui.md:107`, верхний Story shortcut удалён | `Workspace.tsx:144`, `StoryActivity.tsx:33` вновь показывают прямой reader action в progress. | Документ и новый visibility workaround разошлись; сначала дать ясное review-действие на ноде, затем удалить banner. |
| `story-workspace-preproduction.md:30`, прежний Storytell scope | Текущий `Pipeline.tsx:77` / `web/README.md:20`: прямой START → Model → END → Story. | Обновить as-built описание, не восстанавливать удалённый промежуточный scope. |
| `webui.md:209,233`, без glow/постоянных pulses | `style.css:141–154`, [v30](../../test-results/screenshots/story-workspace/v30-active-glow/) фиксируют новую scoped подсветку работы. | **Документальный drift**; позднюю реализованную итерацию учитывать как baseline. Не удалять её лишь из-за старого текста. При пересмотре ограничить motion реальным work/reduced motion. |
| Wireframe: v10/v11 + rail Final/Montage + старые mock prompts | Исторические макеты смешаны с целевыми правилами; текущий rail содержит Characters. | Отделить исторические примеры от актуальной композиции; не суммировать все пункты всех макетов. |
| Canvas/media/profile/selection/Montage | В prototype есть иллюстрации; production backend ещё не обеспечивает полный cinematic. | **Отложено**, не потерянные готовые функции. Не добавлять пустые navigation/actions ради соответствия mock. |
| Exact refs, budgets, history, frozen prompt, Retry/Cancel | Реализованы в раскрытиях и меню. | Не отсутствуют. Сохранить доступность, убрать повторение в обычном reader. |
| Characters subject ID/revision, Audio/Video | Постоянные IDs и отключённые кнопки предписаны `uiux-wireframe.md:78–79`. | Здесь нужно менять и контракт: revision кратко, ID по запросу; будущие действия не занимают экран. |

Главные evidence paths: `web/src/pages/workspace/Workspace.tsx:138–152,222–230`, `web/src/widgets/pipeline/Pipeline.tsx:91–104,114–145`, `web/src/style.css:23–47,118–125,213–220,236–278`, `web/src/features/commands/useCommands.tsx:55–62`, `web/src/features/story-reader/StoryReader.tsx:36–50`, `web/src/widgets/characters/Characters.tsx:159`.

## 6. Порядок следующей итерации и критерии

1. **Shell:** объединить topbar/управление/breadcrumb, убрать banner и постоянную scope-note, сохранить понятное review-действие на ноде. Desktop canvas начинается сразу под header (ориентир 60–72px); на планшете один компактный fallback; нет постоянного второго ряда обычных действий. Перепроверить authored viewport.
2. **Reader/inspector:** Details вправо, Story content-first и доступный exact footer, общие reader/review handlers с Chat. Панель не блокирует desktop canvas; закрытие сохраняет выбор/viewport/draft и возвращает focus. Historical, unreadable и stale subjects не получают ошибочного Approve.
3. **Copy/forms:** человекочитаемые сообщения доставки, compact Start, убрать будущие кнопки. 202/receipt не объявляет результат или approval; потерянный ответ повторяет тот же payload/key; ошибки не исчезают автоматически.

Focused acceptance: desktop 1440×900 и tablet 820×900 без переноса обычных действий в несколько полос; mobile 390px с доступным Chat/меню; длинная Story с видимым exact decision footer; одна текущая панель; keyboard/focus/Back; прежние exact versions/address-bound drafts/OCC/storage/offline guards. Обновить affected browser assertions, особенно те, что сейчас требуют `dialog` и две одинаковые navigation surfaces. Сохранить семинодовую карту и текущие backend identities.

Браузерные измерения и captures выполнены временным audit runner, сохранённым в `test-results/ux-audit.cjs`; использован owned harness на порту 8783 с замоканным live transport. Owned процесс остановлен, disposable data/character roots удалены. Старый HTML открыт отдельно через `file://`. Для повторного capture нужен новый `SCREENSHOT_DIR`. Проверка не создавала реальных персонажей, не читала credentials и не выполняла платных вызовов.

## 7. Реализованная итерация UX1–UX5

Пять bounded coding assignments выполнены последовательно; отдельный шестой assignment адаптировал старую browser acceptance без удаления проверок exact delivery/recovery. Primary проверил diffs и final desktop evidence. Независимое review выявило два воспроизводимых menu/panel взаимодействия; исправлены локально и добавлены RED→GREEN проверки.

| Шаг | Реализовано / evidence |
|---|---|
| UX1 · Shell | Единый 64px topbar; список в проектном dropdown, status/controls/model в Run, один Pipeline/Chat, Characters отдельным компактным входом. Canvas y=64/h=836 при 1440×900 (**+219px / +35.5%** к audit baseline). Семь нод, Story preview/direct review/маленький drill-in и Current; старые viewports сохраняются. [v32](../../test-results/screenshots/story-workspace/v32-compact-shell/screen-state-desktop.png). |
| UX2 · Details | Неблокирующий inspector 380px; narrow native sheet; один workspace-owned subject, замена вместо stacking, закрытие сохраняет фактический viewport/focus. [v33](../../test-results/screenshots/story-workspace/v33-right-details/screen-state-desktop.png). |
| UX3 · Story | Reader 520px справа, actual hook/story первыми; cast/shots/history доступны ниже, fixed exact footer и раскрываемое обсуждение. Chat использует тот же subject/cache/draft/handlers. Historical read-only, unreadable/stale approval guards сохранены. [v34 Pipeline/Chat](../../test-results/screenshots/story-workspace/v34-story-focus/); synthetic long-body fixture явно проверяет footer. |
| UX4 · Feedback | Явные outcome tags вместо распознавания Receipt строки; scope сообщения по execution/Start. Pending постоянно, same-envelope repeat, successful receipt в Run. Character success toast 340px/4s active time с hover/focus pause; unreadable save остаётся persistent. [v35](../../test-results/screenshots/story-workspace/v35-feedback/). |
| UX5 · Forms | Idea-first Start, compact readiness, optional picker/selected chips, advanced shot IDs. Seconds→integer ms без floating rounding: проверены 1/1250/60000/1001/1007ms/reload/payload. Characters: version видима, ID по запросу, future buttons и empty-field noise убраны. [v36](../../test-results/screenshots/story-workspace/v36-creator-forms/). |
| Review fixes | Открытие Run Details из Characters возвращает execution перед показом панели (раньше hidden modal). Escape сначала закрывает Run/project menu, потом inspector; сохранены cache и opener. [v37](../../test-results/screenshots/story-workspace/v37-panel-menu-fix/screen-state-desktop.png). |

### Проверки и границы

- `npm run typecheck`, `npm run build`, `npm run check:schemas`, `npm run check:commands`, `node character-check.cjs` — PASS. Существующий build warning >500kB сохраняется.
- Primary final checks после review fixes: typecheck/build/command check, `python -B -m unittest tests.test_static_ui -q` (**1 test OK**) и `git diff --check` — PASS. Built assets обновлены.
- Focused checks: `compact-shell-check.cjs`, `details-panel-check.cjs`, `story-focus-check.cjs`, `feedback-check.cjs`, `creator-forms-check.cjs` — RED на старом поведении → GREEN. Проверены 1440/820/390 и границы 1279/1280px, long Story/footer, panel replacement/focus/viewport, uncertainty replay, toast и ms conversion. После review fixes повторены Details/Shell/Story.
- Full fixture `npm run check:browser` на owned 8820 — PASS: **12 command/replay POSTs**, zero navigation mutations; OCC/budgets/retry/cancel/receipt/storage/read failures/restart/drafts/versions сохранены. Pan: **62 frames/25 transforms**, шесть connectors, 0 held writes/1 release write.
- `STORY_VISIBILITY_CHECK=1 node shell-check.cjs` на 8821 — PASS: mocked live graph, generated cast и pinned r1 после library edit/reload/Start/restart/approval. `NAVIGATION_CHECK_ONLY=1` на 8823 — PASS, zero POST.
- `node active-glow-check.cjs --browser` — PASS, 11 состояний и reduced motion; `node characters-browser-check.cjs` на 8822 — PASS save/edit/OCC/lost-response/body recovery. `node shell-check-regression.cjs` — **15/15 PASS**.
- Все перечисленные desktop screenshots просмотрены; индекс обновлён. Данные/библиотеки disposable, процессы stopped/cleaned, credentials/paid calls/user server/library не использовались. Backend/API/journal/dependencies и standalone prototype не менялись. Полный cinematic остаётся неподключённым.

Неиспользуемый ToolNode в request graph оставлен честно отключённым: это baseline-схема инспекции, а не действующий tool loop. Отдельный notification center и новый rendering/media UI для этой итерации не потребовались.

## 8. Правки пользователя после UX1–UX5

Эта итерация заменяет прежние решения о rail, node action buttons, коротком breadcrumb и collapsed character picker; контракты exact delivery/approval/drafts сохранены.

- **Клики нод:** один — информация справа (Storytell/Story output с результатом — exact reader), двойной — существующий scope. Enter/Shift+Enter — keyboard equivalents; footer-кнопок нет ни в одном scope. Первый click может открыть sheet/изменить geometry: второй не исполняет оказавшийся под мышью Approve. Leaf не получает выдуманный graph.
- **Back:** один глобальный right-click handler для любых app targets: menu → panel/editor → parent scope → предыдущая страница; root no-op, contextmenu подавляется. Viewport/drafts сохраняются; браузерная внешняя история не вызывается.
- **Навигация:** rail 72px Pipeline / Canvas / Characters; Canvas самостоятельный, пока пустой. Topbar 64px, имя проекта до 160px с полным tooltip/accessible name и path `проект / Cinematic / Storytell / LangGraph`. Chat альтернативный Pipeline view. Test Start удалён, исторические fixtures остаются читаемыми через existing API.
- **Формы:** picker всегда виден; Character info содержит все pinned изображения/Bio и внутренние параметры. Library/editor ID и версия видимы, у несохранённой карточки ID ещё не назначен. Male/Female toggle вместо текста; прежние произвольные gender и pending bytes не меняются без выбора. «О версиях» и «Что будет создано» удалены.
- **Final review:** исправлены menu-first Escape при focus внутри панели и возврат focus после keyboard Close project picker. Оба воспроизведены RED→GREEN.

### Приёмка

- `node navigation-check.cjs` — PASS (финальный owned port 8840): реальные clicks/dblclick, в том числе второй click на координатах Approve; scopes/leaf, вся Back priority, menu/focus, rail/full path, 1440/820/390; **zero mutation POSTs/errors/foreign requests**.
- `node creator-forms-check.cjs` (8816), `node characters-browser-check.cjs` (8817) — PASS: visible picker/IDs, pinned r1 после r2, images/Bio, gender/unset/старые значения, loading/read errors, OCC/storage/lost receipt, exact ms и replay.
- Полная `npm run check:browser` (8836) — PASS, **12 exact command/replay POSTs**; ordinary Start проверяется через mocked live transport, historical fixture создаётся harness-only через API. Навигация и refetch не отправляют mutations.
- `STORY_VISIBILITY_CHECK=1 node shell-check.cjs` (8828) и `NAVIGATION_CHECK_ONLY=1` (8838) — PASS; navigation zero POSTs. Details (8824), Story focus (8825), feedback (8826), compact shell (8837) — PASS. Сохранены drafts/history/OCC/budgets/Retry/Cancel/restart/receipts/storage denial.
- `node active-glow-check.cjs --browser` — 11 states PASS; `node shell-check-regression.cjs` — 15/15 PASS. Pan: 63 frames, шесть connectors, zero held writes/one release.
- Typecheck/build/schema/command/Character DTO — PASS; final static UI unittest — **1 OK**. После двух menu fixes повторены typecheck/build/navigation. Known >500kB chunk warning сохраняется.
- Captured/inspected: [v38 navigation](../../test-results/screenshots/story-workspace/v38-navigation/), [v39 forms](../../test-results/screenshots/story-workspace/v39-character-forms/), [v40 menu focus](../../test-results/screenshots/story-workspace/v40-menu-focus/screen-state-desktop.png); screenshot index обновлён. Owned processes/roots cleaned, credentials/user data/paid calls не использовались.

## 9. Финальные правки Characters и меню проектов

- Открытие персонажа/создание нового заменяет несохранённый черновик без вопроса. Subtitle и «Карточки · N» удалены. Heading: маленький refresh icon слева от named «Продолжить черновик» и «Новый персонаж», с адаптацией длинных имён/mobile.
- **Удалить черновик / Удалить персонажа** только внутри editor, native Yes/No confirmation. Отмена/right-click не мутируют. Draft reset сбрасывает unsent поля/изображения, не saved card. Character delete скрывает subject из active library, сохраняя exact refs/revisions/images и frozen execution inputs. Pending delivery не выбрасывается как draft.
- Backend `POST /api/characters/delete` с `{mutation_id,subject_id,expected_revision}` → `{mutation_id,ref,deleted:true}`: shared mutation namespace, OCC, atomic manifest tombstone, restart-safe identical replay. Канонический manifest v1 остаётся читаемым; успешный delete переводит в v2. New save не resurrect, old save replay сохраняет original receipt. Selected exact refs остаются valid.
- Меню **Проекты**, refresh icon рядом с heading, без крестика/«На связи». Outside click/right-click/Escape закрывают; refresh сохраняет меню и не запускает generation. Read errors/loading не скрыты.
- Независимый review воспроизвёл потерю focus на pending delete и очистку journal после CSRF403; исправлены RED→GREEN. Locked editor фокусирует доступный heading; permanent401/403 оставляет pending, transient403 делает один bounded exact replay после session renewal.

**Проверки:** Character backend/API/frozen-input suites **41 OK**, Story cast **8 OK**; Character DTO/command/typecheck/build PASS. `characters-browser-check.cjs` **PASS** (final capture owned8842): confirmed/cancelled delete, stale OCC, historical reads, lost response/reload same bytes, storage denial, receipt mismatch, permanent/transient403, enabled focus, compact actions/long names/mobile. `navigation-check.cjs` **PASS** (8843): Projects menu/refresh/dismiss/focus и существующие gesture/Back/viewport checks на 1440/820/390, zero mutations/errors/foreign requests. Full `npm run check:browser` **PASS** (8844): **12 exact command/replay POSTs**, zero navigation POSTs, pan63 frames/six connectors/one release write. Static UI **1 OK**. Known >500kB chunk warning сохраняется.

Captured/inspected [v41 Characters/editor](../../test-results/screenshots/story-workspace/v41-character-delete/) и [v42 Projects menu](../../test-results/screenshots/story-workspace/v42-projects-menu/projects/screen-state-desktop.png); индекс обновлён. Disposable roots/owned processes cleaned; user library/data/credentials/paid calls не использовались.

## 10. Черновик существующего персонажа и компактный editor

- RED: clean open → Back показывал Continue; edited Back/rail/Continue сохранял содержимое, но повторный click той же карточки читал saved latest и перезаписывал правки. Исправлен источник: frozen opened baseline сравнивает Bio и ordered image inputs; clean просмотр и exact revert не создают draft. Continue/тот же subject возобновляют retained изменения и исходную revision для OCC без refetch. Другой subject/New остаётся intentional replace без вопроса. Pending delivery/journal/rejection guards сохранены.
- Видимые «Персонажи» / LOCAL LIBRARY убраны, название в breadcrumb, accessible focus heading сохранён. Compact padding/gaps/metadata, contained thumbnails ≤160×148px, upload ≥44px и native footer positioning. Три footer действия проверены без прокрутки на desktop 1440×900/768 с 1/6 images; tablet/mobile scroll reachability, focus и touch targets сохранены.
- Typecheck/build/Character DTO **PASS**. Character browser **PASS** на owned8846: все Bio fields/images, dirty/revert/Continue/Back/rail/same subject после newer list, original stale OCC, different target/New, pending save/delete/read/storage/401/403. Forms8847 и navigation8848 **PASS**, без платных вызовов; navigation zero mutations/errors/foreign requests. Independent scoped review: no blockers.
- Captured/inspected [v43 library/editor](../../test-results/screenshots/story-workspace/v43-character-draft-layout/), screenshot index обновлён. Owned processes/disposable roots cleaned, user library/credentials untouched. User visual approval новой версии не заявлено; existing >500kB chunk warning остаётся.

**Spacing follow-up по просьбе пользователя:** LOCAL LIBRARY возвращён над editor и в library action row; header min-height28px / bottom gap16px даёт воздух под topbar без повторного «Персонажи». Build и Character browser8849 PASS, включая desktop1440×768/900 footer1/6 images и820/390 reachability. Mobile checker использует native centered scroll вместо nearest edge с subpixel clipping. Captured/inspected [v45 library/editor](../../test-results/screenshots/story-workspace/v45-library-spacing/); v44 — пустая папка неудавшегося pre-capture check, сохранена. Draft/delivery поведение неизменно.

**Alignment follow-up по двум размеченным референсам:** header min-height44px одинаков в library/editor, bottom gap16px сохранён. LOCAL LIBRARY и верхняя граница карточек/editor больше не смещаются при открытии персонажа. Geometry regression RED: editor y128 / library y144; GREEN после CSS-правки. Build/typecheck и Character browser8850 PASS, включая desktop1440×768/900 footer1/6 images и820/390 reachability. [v46 library/editor](../../test-results/screenshots/story-workspace/v46-library-alignment/) captured/inspected.

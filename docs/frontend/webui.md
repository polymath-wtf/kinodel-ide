# Web UI — Kinodel Workspace

**[Standalone HTML-макет](../../web/prototype/index.html) · [Запуск — web/prototype/README.md](../../web/prototype/README.md).** Интерактивный **MOCK, без backend**, HTML/CSS/JS: Pipeline, отдельный Canvas проекта, mock Inputs/Outputs и provider inspection. Отдельный [React workspace](../../web/README.md) читает реальные internal Story executions с FastAPI origin и поддерживает durable команды (6D).

Статус: **production workspace подключён к Story foundation и Story → Wardrobe, с локальными авторскими Characters и сохранённым текстовым планом. Шаг 3/W7 принят по code/browser checks с mocked HTTP; [W8 принят по сокращённому критерию автора](../roadmap-mvp.md#wardrobe-batch-output). Активация/restart пользовательского backend не проверялись. Technical [ComfyUI saved V2-plan handoff/native preparation и durable input pins](../roadmap-comfyui.md#wardrobe-comfyui), [offline 5А portrait job/initial intent](../backend/artifacts.md#offline-portrait-job-intent) (DB16) и [offline 5Б portrait candidate/original import](../backend/artifacts.md#offline-portrait-candidate-import) (DB17) реализованы; NEXT — 6А первый restart-safe portrait; verified parents/reference transport и image activation/group — шаги 6Б/7. Offline technical candidates не означают provider acceptance/successful generation/approval и не доступны через media DTO/API/UI; selection/assets/group ещё pending. UI/media integration не менялись. 6F визуально утверждён пользователем, приёмка 6E пройдена; полный шаг 6 и cinematic/media integration остаются открыты**. `web/prototype/` — отдельный HTML-эксперимент. Макеты и промпты — [UI/UX wireframe](uiux-wireframe.md). Порядок сборки, pins и приёмка — в [Local MVP](../roadmap-mvp.md); media/Canvas/workflow-срезы — в [ComfyUI roadmap](../roadmap-comfyui.md). Эта страница задаёт целевой стек, визуальный язык и правила взаимодействия.

**Текущая композиция, 5 октября:** Topbar 64px: `KINODEL` с разделителем, компактное меню с видимым названием выбранного проекта (текущий заголовок из submitted idea; длинный текст сокращается, полный остаётся в tooltip/accessible name), далее путь `Pipeline → Storyboard` или `Pipeline → Storytell → LangGraph`, Run и новая история. Без выбранного запуска меню подписано «Проекты»; на корневой карте виден `Pipeline`. Canvas, Characters и Новая Story сохраняют название проекта и показывают текущую страницу в пути; Chat — альтернативный вид Pipeline. Слева rail 72px **Pipeline / Canvas / Characters**; Canvas пока честно пустой, генерация медиа не подключена. Один клик ноды открывает информацию справа, double-click — существующий вложенный scope, без кнопок на карточках. Правый клик в любом месте приложения — один шаг Back. Details 380px / Story 520px сохраняют content-first/exact footer и responsive sheets. Персонажи перед Start всегда видны; Character info раскрывает закреплённые изображения/Bio. Исторические captures — в [screenshot index](../../test-results/README.md); самостоятельное визуальное утверждение новой версии не заявлено. Standalone-примеры ниже исторические, не совокупный список обязательных элементов.

## First UI Slice

Ниже описан целевой cinematic UI и отдельный standalone mock, **не полный функционал текущего workspace**. Production 6D/6F/W7: список/URL execution, durable команды и объявленная карта Brief → Storytell → Wardrobe → Storyboard → Filmmaker → Montage → Final без обязательного test run. В новых запусках Wardrobe активен после exact Story approval; до запуска подписан «После approval Story». Исторические Story-only executions не получают Wardrobe. Вложенные scopes показывают точные agent/gen/HITL; Montage — сборку и tool-owned file verification. Config/Inputs/Outputs отделяют контракт от сохранённых данных; внутренний LangGraph — read-only структура `backend/story_graph.py`, не trace. Storytell/Wardrobe показывают frozen inputs/config и сохранённые результаты; у Wardrobe inputs/config доступны после preparation, полный копируемый план — после commit. Provider workflow unavailable вместо выдуманного графа; media generation и дальнейшее исполнение не подключены. Pipeline/Chat используют общие exact readers/cache/черновик; metadata/body ошибки независимы, request revision не равна output version. Точные проверки — [web/README](../../web/README.md).

### Characters: текущая локальная активация

**Characters** в левом rail — отдельная авторская библиотека `CharacterV1`, не stage графа и не future `CharacterChunkV1`. Редактор: 1–6 локальных изображений и Bio (имя обязательно; возраст, гендер, вайб необязательны). Гендер — кнопки **Male / Female**, повторное нажатие снимает выбор; прежнее произвольное значение не меняется без явного выбора. Версия и ID видимы без раскрытия; у новой карточки ID назначается после сохранения. Неактивные Audio/Video и пояснение «О версиях» отсутствуют. **Сохранить персонажа** явно принимает авторскую карточку и создаёт immutable revision; обновление требует `expected_revision`. Current manifest, история и изображения канонически хранятся в [wiki/characters](../../wiki/characters/README.md), без cloud, retrieval index или production-memory gate. Exact mutation сохраняется в browser IndexedDB до POST; это журнал доставки, не каноническая библиотека.

Новая Story выбирает необязательные exact `{subject_id, revision, digest}`. Backend замораживает карточки и narrative Bio в execution до работы модели; технический retry/reopen не читает latest. Storytell получает в OpenRouter только Bio с provenance, не изображения; после exact Story approval Wardrobe также получает закреплённые изображения выбранных Characters. Старый текстовый subjects draft остаётся видимым как неотправляемый; прежние pending commands сохраняют свои payloads. Пустой selection позволяет Storytell создать cast в `StoryV2.generated_characters`; ни результат, ни его approval не публикуют Characters автоматически. Standalone demo picker остаётся отдельным mock. Подробный сценарий — [wireframe](uiux-wireframe.md#1a-characters--локальная-авторская-библиотека).

В Start карточки выбора всегда на виду. **Character info** показывает все изображения и Bio точных выбранных версий; внутренние ID/revision/digest/image metadata раскрываются отдельно. Последующая правка библиотеки не подменяет закреплённую версию. Одна обычная «Начать историю» создаёт Story → Wardrobe V2 через `/api/executions/story-wardrobe/v2`, без отдельной кнопки Wardrobe. Compact result — patch in place текущего V2; исходные graph/config identities, Start/replay и journal не меняются. Исторические fixture/live Story доступны через API; saved envelopes сохраняют endpoint, payload bytes и key. Retired unversioned Wardrobe envelope получает 410 и никогда не retargets в V2.

**Библиотека/проекты:** Другой персонаж/New заменяет несохранённый черновик без вопроса. В action row: icon refresh → «Продолжить черновик · имя» → «Новый персонаж»; subtitle и счётчик «Карточки» удалены. Только внутри редактора — confirmed «Удалить черновик» / «Удалить персонажа». Первое сбрасывает unsent изменения, второе удаляет из active library с OCC/exact replay, сохраняя исторические refs. Неопределённая доставка не удаляется как черновик, в том числе после постоянных 401/403; одна bounded session-renewal попытка повторяет те же bytes/key. Пока delivery блокирует поля, focus остаётся на доступном editor heading. Меню **Проекты**: icon refresh рядом с заголовком, без крестика и «На связи»; outside click/right-click/Escape закрывают его. Ошибки/загрузка остаются видимыми.

**Черновик и компактный editor:** Просмотр saved Character не создаёт unsent draft; он возникает только при отличиях Bio/ordered images от открытой версии, точный откат очищает dirty. Continue и повторный вход в тот же subject возвращают поля/images и исходный OCC, без подмены latest. Видимый повторный заголовок «Персонажи» убран; **LOCAL LIBRARY** в header row библиотеки/редактора имеет min-height 44px и margin-bottom 16px: заголовок и верхняя граница карточек/editor выровнены при переходе между видами, воздух под topbar сохранён. Название страницы остаётся в breadcrumb и accessible heading. Компактные metadata/spacing, bounded contained previews и footer: три действия видны без прокрутки на desktop 1440×768/900 с 1–6 images; narrow/mobile остаются scrollable и клавиатурно доступными.

**Новая история, 5 октября:** одна «Идея истории» и один выбор Characters. Пять отдельных компактных блоков — размеры изображений, размеры видео, количество кадров, «Длительность» с «сек» справа от числа и «Video workflow» с вариантами `img2vid`/`ref2vid` — стоят в одном desktop-ряду; на узком экране переносятся. Поля размеров 72–90px, количества 72px, длительности 84px; блоки количества/длительности не растягиваются (166/136px), интерактивные цели не ниже 44px. Подписи под полями и строка расчёта длительности убраны. Карточки персонажей шириной 300px показывают портрет, имя, exact revision и отметку выбора; заголовок, счётчик и refresh объединены. OpenRouter — отдельный блок с моделью, нейтральным статусом «Настроена» и кнопкой «Изменить модель»: раскрываются текущая серверная модель, инструкции смены `LLM_MODEL`/перезапуска и GET-only обновление статуса. Это не browser model selector и не проверка удалённой доступности. Свежий draft: изображения 1024×1024, видео 480×480; сохранённые размеры не подменяются. Длительность кадра вычисляется как total/count до целых миллисекунд, без округления; отдельного ввода длительности кадра и shot IDs нет. Live text Start принимает 1–8 кадров, 1–60000 ms на кадр и генерирует `shot-001…`; неподдерживаемый ввод блокируется до POST. Невалидный numeric text сохраняется при навигации/reload. Старый Start-only cache переносит count/duration в новые поля, сохраняя остальные черновики и exact pending commands.

Отдельная страница «Настройки фильма», unavailable profile selectors, раскрытие проверки настроек и кнопка «← К карте Cinematic» убраны. Форма не вызывает production catalog/validate; возврат доступен через общую навигацию. Одноразовая cache-миграция меняет прежний default video 1024×1024 на 480×480 и сохраняет `video_defaults_version: 1`; последующий явный выбор 1024×1024 сохраняется. Другие размеры и невалидный numeric text не меняются. Активные idea/refs принадлежат Start, production-параметры — cinematic draft; прежние independent idea/refs/profile pins сохраняются, но не подменяют видимые значения. Обычная кнопка запускает Story и после её exact approval — Wardrobe до сохранённого плана; генерация изображений/видео пока не подключена. [Desktop capture](../../test-results/screenshots/story-workspace/v62-ordinary-pipeline-start/final/start/screen-state-desktop.png).

**Один запуск: Pipeline для производства, Canvas для медиа, Chat как альтернативный вид процесса.** Pipeline — горизонтальная дорожка из семи компактных нод с превью и краткими описаниями; зелёные галочки показывают завершённые Brief/Storytell, оранжевая рамка — текущий Wardrobe review, будущие ноды остаются waiting. Матрёшка раскрывает агента, generation tool и review. Полные изображения/видео собраны в отдельном Canvas. В standalone v10 Canvas ровно три горизонтальные строки **Anchors / Images / Video** без внешних рамок: 3 anchors, 9 start-frame attempts в одну строку, 2 pending clips. Все 14 слотов видны на 1600×1000 и 1440×900 при закрытой панели и Fit (карточки ~150/136px); при открытой панели минимум 120px, Fit сохраняет 100% и дальние Images доступны pan. Полные подписи остаются в aria-label и tooltip при сокращении текста на карточке. Отдельного shot-фильтра нет: S01/S02 подписаны на самих карточках. Единый фон всех рабочих видов — локальный `refs/zbs ref v1/background v2.png` без второй сетки точек; `New shot · coming soon` отключён. Правый клик по asset на Canvas открывает Wardrobe / Storyboard / Filmmaker по категории, по пустому полю — последний Pipeline scope и viewport; rail и breadcrumbs обеспечивают клавиатурный путь. Проект и breadcrumbs объединены в одной верхней строке; Canvas не дублирует заголовок. Левый rail: Pipeline / Canvas / Brief / Review / Final. Правая панель закрыта по умолчанию; выбор материала открывает компактный contained preview, табличные Details / Prompt / Settings / Lineage и кнопку workflow. В standalone Pipeline / Chat показывает хронологию mock-проекта; сообщения — локальные неотправленные черновики, backend не подключён.

UI показывает сохранённое производство и отправляет команды. LangGraph маршрутизирует; агенты создают планы; tools выполняют эффекты; backend хранит результаты и применяет approval. Переключение вида, вход внутрь ноды и закрытие браузера не запускают работу.

**Standalone v11 (после v10, только mock):** Rail теперь Pipeline / Canvas / Brief / Review / **Montage**; Final остаётся output-карточкой в Pipeline. Montage показывает два *планируемых* shot-слота, 6 s каждый, illustrative scrub и выбранный shot; файлов и export нет. Brief — отдельная форма будущего run с idea, explicit refs/context, demo character selection и видимыми примерными output-настройками. Submitted example immutable, `Save local draft` валидирует текст и не отправляет Run. Canvas — галерея без портов/проводов; portrait → sheet виден как lineage, не workflow wire. Inspector начинает с seed/prompt/preview; API-prompt model/size/sampler/steps убраны в Settings с явным «example, not render receipt». Pipeline L0 показывает краткие именованные boundary-порты и отдельно стрелки порядка approval; L1 — exact `brief/story/wardrobe_plan/anchor_frames/storyboard_plan/story_frames/video_plan/shot_videos/final_video` и непроводные context/profile inputs по контрактам [cinematic](../pipelines/cinematic.md) и [JSON](../pipelines/cinematic.v1.json). Provider-порты остались отдельными проверяемыми API mappings. Chat оставляет один текущий review и owner-bound unsent drafts без симуляции ответа.

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

- В `web/prototype/` находится standalone HTML/CSS/JS MOCK; stock-фотографии остаются в `web/assets/` (`../assets/` из прототипа), без включения в runtime. В `web/` установлен React/Vite workspace с exact lockfile, React Flow 12.11.6, Query 5.103.2, Zod 4.6.5, реальным Story API и persist-before-POST command delivery (6D).
- React 19.3.0, React Flow 12.11.6 и Vite 8.0.16 использовались в удалённом эксперименте. Это историческая проверка; текущий Vite baseline остаётся 8.0.10. Pins и проверки connected workspace — в [web/README](../../web/README.md).
- Текущие Tailwind 4.3.3 и Vite plugin 4.3.3 поддерживают Vite 8; Query 5.103.2 поддерживает React 19; Zod 4.6.5 не обнаруживает конфликта в metadata. shadcn CLI 4.21.0 проходит Node requirement.
- React Flow UI официально поддерживает React 19 / Tailwind 4. Интеграция целевого production-стека и его проверки ещё нужны на шаге 6; standalone build и registry metadata их не заменяют.

## 2. Что берём из локальных референсов

Все изображения в `refs/` — визуальные ориентиры; сгенерированные экраны не подтверждают работающие API или правильную топологию.

| Референс | Берём | Уточняем для Kinodel |
|---|---|---|
| [React Flow template](refs/react%20flow%20ui%20workflow%20template.png), [canvas mb](refs/canvas%20mb.png) | Near-black, голубое выделение, фиолетовый и коралловый accents; тонкие рамки, handles, правый инспектор | Формы в инспекторе; Canvas — отдельный пункт навигации |
| [Pipeline zbs](refs/zbs%20ref%20v1/pipeline%20zbs.png), [pipeline kaif](refs/zbs%20ref%20v1/pipiline%20kaif.png) | Короткая дорожка, простор, фон с точками, спокойный левый rail | Без постоянного инспектора и дублирования media; review виден на этапе, подробности открываются отдельно. Живописный фон — необязательный материал проекта при достаточном контрасте |
| [Wardrobe zbs](refs/zbs%20ref%20v1/wardrobe%20zbs.png), [pipeline preview](refs/pipeline%20preview.png) | Три ясных шага, компактные thumbnails внутри generation | Полный набор только в Canvas; portrait → sheet зависит от exact portrait, location независима |
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
| Wardrobe | Цель: `wardrobe → anchor-batch [Batch generation] → anchor-hitl` | План, N последовательных image jobs, выбор полного набора |
| Storyboard | Цель: `storyboard → frames-batch [Batch generation] → frames-hitl` | Batch prompts и начальный кадр каждого shot с объявленными image dependencies |
| Filmmaker | `filmmaker → video-gen → video-hitl` | Motion prompts, videos и review |
| Montage | `montage` | Детерминированная сборка; внутри видны inputs и проверка файла |
| Final | `final` — поверхность результата Montage | Player/download; не новый агент или финальный approval |

Это фиксированная **view-группировка** существующего маршрута. Например, canvas ID `view:wardrobe` не записывается вместо `stage_id=wardrobe` или `anchor-hitl`. У группы нет своего execution, approval, binding или процента выполнения.

Summary берётся из активного вложенного этапа: `Generating · 2/3 units` только при наличии подтверждённых счётчиков; `Review anchors · set 2` при actionable gate. Ошибка/блок вложенного этапа остаётся видимой с его именем. `Complete` появляется после завершения всех обязательных шагов группы, включая применение решения. Завершённый вызов агента не завершает матрёшку.

### Правила раскрытия

- На **каждой** ноде click/Enter открывает соответствующую информацию справа; Storytell с результатом и Story output открывают общий exact reader. Double-click / Shift+Enter раскрывают существующий authored scope; leaf остаётся в информации, без выдуманного графа. На карточках нет `Читать Story`, `Внутрь`, `Подробнее` и других footer-кнопок. Первый клик может изменить размер canvas/открыть modal: второй клик остаётся частью входа в исходную ноду и не активирует оказавшийся под мышью Approve.
- Правый клик **в любом месте приложения**, включая ноды, wires, controls, topbar, формы, панель/backdrop и Characters, выполняет один Back: открытое меню → панель/редактор → родитель scope → предыдущая страница. Корневой Pipeline — no-op; browser context menu подавляется. Единственный workspace-владелец не вызывает внешнюю browser history. Черновики/viewport сохраняются. Escape сначала закрывает shell menu, даже если focus уже в правой панели; следующий Escape — панель. Явное закрытие project menu возвращает focus имени проекта.
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

В L0 карточка компактна: имя, status и превью внутреннего содержимого, без action footer. Brief/Storytell — текстовая выдержка; будущие Wardrobe/Storyboard — strip миниатюр, video — poster при наличии файла либо честный placeholder. В будущем L1 generation показывает краткий preview, полный материал — Canvas, без вложенной галереи. Полные prompts и metadata остаются в Details. Важные labels читаемы на начальном рабочем масштабе; Fit — обзор, а не способ ужать рабочие ноды до микротекста.

Порты снаружи — краткое резюме boundary, не исчерпывающий список зависимостей. Полные exact inputs доступны в Inputs. Линия L0 обозначает порядок этапов, **не соединяет выбранный artifact с произвольным входом следующей группы**; dependency lines внутри scope обозначают конкретные named inputs и имеют подписи. Провод не является командой.

## 5. Инспектор, настройки и действия

**Контекстная правая панель, закрыта по умолчанию:** открывается только для выбранного фото или по `Details` ноды. В ней header и нужный для предмета раздел `Config / Inputs / Outputs`; connected desktop 380px, ниже 1280px — sheet. Story reader — отдельный вариант шириной 520px с текстом первым и доступным exact footer. Одна панель принадлежит workspace: новый предмет заменяет старый; scope/view/execution/Start/library переход закрывает устаревшую панель. Она резервирует ширину canvas, не затемняет desktop; закрытие восстанавливает viewport и focus. Не показываем все три раздела одновременно и не повторяем contact sheet/preview, уже видимые на canvas. Review нескольких фото разворачивается в широкий sheet; кнопка Approve связана с полным точным предметом, а не с выбором одного фото.

Для медиа в standalone Canvas — инспектор 376px: contained preview и вкладки **Details / Prompt / Settings / Lineage**; Details содержит важные seed/prompt и honest status, технический *пример* API-workflow раскрывается в Settings. Размер, модель, steps и sampler не являются metadata stock-файла или job receipt; неизвестный seed подписан `Not recorded`. Open in workflow виден без прокрутки на 1440×900. Mock frame prompt/seed — локальный draft; Regenerate · mock не отправляет job. Смена вкладки/вида сохраняет draft до reload.

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

**Текущий W8 inspection:** double-click / Shift+Enter на Wardrobe в Pipeline открывает `wardrobe` — группу **Wardrobe agent → Batch generation · Anchors → Review**; повторный вход в agent открывает `wardrobe:request` — **START → Model → END → Plan**. Request переиспользует существующий Storytell shell. Это объявленная схема запроса, не trace; anchor generation/review пока не подключены. END означает validation/save ответа, не human approval.

**Inputs / Config:** только сохранённый preparation даёт фактические frozen inputs и Wardrobe model/config. До него модель «Не подготовлена», config ещё не закреплён; текущие env и Storytell model не служат fallback. Inputs показывают approved Story link, исходную идею и выбранные frozen Character name/Bio/images один раз. Generated cast виден из approved Story только при пустом selection, не как дополнительные selected targets. Один закрытый technical disclosure содержит authoritative input V2, refs/digests/provenance/image labels/counts/bytes. Adapter 2 отправляет компактную creative projection без persistent refs/digests/дублирующего canon; config сохраняет полную authority. Изображения передаются в исходном порядке как base64 original bytes без resize/re-encoding/omission; raw media/base64 в инспектор не выводятся.

У остановленного Wardrobe в Pipeline без раскрытия Config видны сохранённая конкретная причина и остаток попыток. Таймаут берётся из exact frozen V2 config (fresh — 180 с); V1 configs не читаются. Полученный HTTP 200 не означает сохранённый ответ модели. Фактическое прошедшее время и фаза сбоя показываются только при наличии этих полей; null не дополняются догадками. Используется общий Diagnostic и существующий Wardrobe query/cache, без отдельного endpoint или изменения polling.

В **Model → Настройки → Вызовы Wardrobe** видны сохранённые reserved/remaining attempts, число исправлений формата и последний HTTP/transport/validation diagnostic, включая доступные elapsed/phase. Исторический null означает «Причина не установлена», отсутствующие счётчики — неизвестный бюджет. Зарезервированная попытка не доказывает получение ответа провайдером. `wardrobe_unavailable` разрешает Retry того же запуска при оставшемся allowance; новый backend после перезапуска сохраняет подробности следующего сбоя, но не восстанавливает утраченную диагностику предыдущего.

**Outputs / Plan:** общий Pipeline/Chat compact V2 exact reader показывает batch count, stable unit_key, use_case/workflow, полный копируемый image prompt и короткие ordered `role → unit_key` refs, без direction/purpose/raw subject IDs/пустых dependency notices. Exact plan/Story refs — в одном закрытом disclosure. План содержит только schema identity/Story pin и `batch_prompt`; все creative detail внутри prompts. Ровно portrait+sheet на каждый selected target и одна общая location; при пустом selection — generated/declared fallback, иначе location-only. Удалённые rich поля строго отклоняются, без compatibility reader или conversion. Dependencies — earlier keys плана, не готовые изображения. V1 retained/isolated без reset; пользовательский prior run не переписан. Активация/restart пользовательского backend и offline reopen его реального артефакта не проверялись.

Wardrobe сохраняет compact V2 `wardrobe_plan`; planned Batch-generation / `anchor-batch` потребляет только exact saved validated V2 и записывает media binding через exact review selection, без повторного LLM. Текущие authored TS scopes — `anchor-batch`/`frames-batch` (**Batch generation · Anchors / Storyboard**), disconnected без job projection/media. Compact V2 reader подключён в [W8](../roadmap-mvp.md#wardrobe-batch-output); исторический `cinematic.v1.json` сохранён неизменным и не совместимый renderer. Нет dual V1 reader/replay/reset; отдельные Story/Brief/video contracts не меняются. W8 принят по сокращённому критерию автора: ручная оценка prompts + focused mocked compact V2/offline recovery. Full discovery и automated real-model/offline harness отложены, не объявлены PASS. Technical [ComfyUI saved V2-plan handoff/native preparation и durable input pins](../roadmap-comfyui.md#wardrobe-comfyui), offline 5А portrait job/initial intent и offline 5Б portrait candidate/original import реализованы; NEXT — 6А первый restart-safe portrait; verified parents/reference transport и image activation/group — шаги 6Б/7. Diagnostic prepare API остаётся read-only (`preparation_only`, `can_submit:false`); public media route/job projection ещё не реализованы, UI не менялся.

**Batch-generation · минималистичная матрёшка (проект):** ориентир — [anchor minimalism](refs/zbs%20ref%20v1/anchor%20minimalism.png).
Один общий image-tool shell для Anchors и Storyboard: заголовок, подпись назначения, один status,
strip до 3 verified thumbnails, `готово X / N`, overflow и View in Canvas. Полный набор — в Canvas,
полный review — в соседней HITL. Ready обозначает complete candidates, не approval. Pending/error
slots не заменяются демонстрационными фотографиями. Внутри N compact `comfyui-gen` карточек из
persisted units/jobs: label/use_case, txt2img/img2img, status, preview; далее attempt → frozen Workflow.
Порядок исполнения и image dependencies различаются: location после face, но без image input от face;
у sheet два image inputs. N/use cases не hardcoded, identity включает execution/stage/activation/unit/job/attempt.
[Общий контракт и storyboard example](../tools/batch-generation.md); реализация/desktop acceptance —
[ComfyUI шаги 9–10](../roadmap-comfyui.md#9-настоящий-canvas-и-media-reads).

Contact sheet показывает, например, `hero_face`, `location`, `hero_sheet`. Это **пример**, не фиксированное число: keys/count приходят из плана. Целевой sheet хранит обе exact dependencies — face и background/location; несовместимый выбор объясняется рядом с parents/child. Генерация последовательная: face → location → sheet, хотя сами parents независимы. Новый face или использованная location требует нового sheet; неизменные parents сохраняются. Исторический standalone mock не является реализацией этого нового binding. Новый Brief выбирает `img2vid/ref2vid` с точными profile pins и показывает различие exact first frame / scene references; [контракт и приёмка](../roadmap-comfyui.md#адаптивные-image-inputs-и-два-video-mode).

Все полные фото/слоты находятся в **Canvas → Anchors / Images / Video**; generation-ноды ведут туда через View in Canvas. S01/S02 остаются у отдельных assets, без shot-групп и ложных рёбер между independent takes. Слот показывает candidate image либо подписанное ожидание/spinner/ошибку. Click/Enter открывает справа один ресурс; Open in workflow в инспекторе ведёт в provider scope с возвратом в тот же Canvas. Отдельный review сверяет и подтверждает полный exact набор.

ComfyUI — **Tool с раскрытием внутри будущего Batch-generation (`anchor-batch` / `frames-batch`) или `video-gen`**, если закреплённый provider именно ComfyUI. Workflow scope относится к выбранному job/unit; разные роли могут использовать разные workflows. В L0 нет обязательной глобальной ноды ComfyUI. Текущие authored batch scopes disconnected и не показывают real render jobs; `anchor-gen`/`frames-gen` остаются только историческими specimen identities.

Целевой drill-down: generation tool → несколько plan units/jobs → конкретный attempt → его Workflow; единственный attempt можно раскрыть напрямую. Здесь компактные status/preview, а полный media-набор находится в Canvas. Scope identity включает execution/stage/unit/job/attempt, а не только имя workflow. Исторический attempt показывает frozen graph/params, даже если registry уже изменился. Canvas строится из committed backend candidate/asset/selection records под managed data root, не из browser storage или сканирования ComfyUI output directory. [Хранение, reads и проверка навигации](../roadmap-comfyui.md#9-настоящий-canvas-и-media-reads).

Сначала показываем читаемый read-only граф/semantic inputs и один output на canvas; inspector закрыт, техническая конфигурация доступна по `Details`. Детальный граф — только из проверенной, sanitised adapter projection; credentials/paths скрыты. Если данных нет, пишем `Workflow details unavailable`, а не генерируем похожую схему. Не нужен встроенный ComfyUI editor/iframe. Параметры sampler/latent/VAE не возникают у workflow, который их не имеет. Decode/Save ещё не означают импорт, выбор или approval результата.

Реальные wires берутся из pinned attempt API graph/node schemas; отдельный editor/layout snapshot сохраняет исходные координаты, когда он есть. API-only graph допускает явно derived display layout, не выдуманную копию ComfyUI editor. Verified import остаётся отдельной границей Kinodel. [Пошаговая реализация viewer](../roadmap-comfyui.md#10-генерации-внутри-tool--настоящий-workflow).

## 6. Chat — второй вид того же запуска

Это спокойная вертикальная **лента производства**, а не новый глобальный агент. В подключённом Story-срезе topbar общий с Pipeline; одна колонка показывает текущую Story первой, версии и закреплённое решение. Brief и история решений раскрываются после результата; техническая activity находится в Model Details. Composer открывается по `Обсудить`, а сохранённый текст раскрывает его автоматически; адрес остаётся exact subject/request. Для будущего cinematic лента содержит результаты других владельцев, а не постоянные polling/status-карточки.

- Текущий review содержит тот же preview, версии и точные действия, что Pipeline. Оба вида используют один query cache, компоненты и mutation handlers.
- Mode `Ask`/`Request changes` выбирается явно. Сообщение «ок» ничего не утверждает. Approve существует только отдельной кнопкой на карточке.
- Пока run выполняется, показываем одну обновляемую activity-строку; не засоряем ленту polling-событиями и не выдаём status за ответ агента.
- Если actionable review нет, composer объясняет, когда станет доступен. Brief до Run редактируется в стартовой форме; полноценный свободный чат/очередь сообщений не заявлены.
- Historical cards read-only, свёрнуты до заголовка и версии; `View in pipeline` открывает связанный предмет. Во время чтения истории новое сообщение не отбирает scroll/focus.
- В connected Story historical reader не отправляет вопрос/правку текущему subject и не утверждает его; старый draft остаётся read-only. При возвращении к текущей версии его адрес не переназначается автоматически.
- Результаты представлены текстом, contact sheet, video player или final download. Чат не должен требовать открыть canvas, чтобы выполнить весь автоматизированный pipeline с обязательными решениями.
- На узком экране Chat — рекомендуемый стартовый вид. Автоматизация между gates не отменяет обязательных human approvals.

## 7. API: реальность и необходимые проекции

По коду `backend/api.py` доступны **Story → Wardrobe V2 Start и исторические internal/live Story routes**: session bootstrap, start, list/projection/execution read, immutable Story/compact V2 plan reads, respond (`approve/revise/clarify`), retry и cancel. Обычный текущий UI Start `/api/executions/story-wardrobe/v2` принимает exact character refs; unversioned Wardrobe Start возвращает 410 до payload work, V1 Wardrobe commands/reads reject. `/api/executions/live-story` сохраняется для прежних envelopes/API. Guarded `/api/characters` даёт list/save, exact revision и изображения. Discussion с typed owner responses реализован; [W8 принят по сокращённому критерию](../roadmap-mvp.md#wardrobe-batch-output), full discovery и automated real-model/offline harness отложены, не объявлены PASS. Полный cinematic ещё pending; активация/restart пользовательского процесса не проверялись ([local startup](../backend/local-startup.md#scoped-story--wardrobe-api)).

| Уже можно проверить локально (fixture/live text) | Ещё требуется для полного экрана |
|---|---|
| Story versions, current review, request digest, work/status, persisted discussion | Cinematic stage projection и public Brief start |
| Exact approve/revise/clarify; retry/cancel | Model/profile readiness и разрешённые настройки |
| Poll/reconnect того же execution | Jobs, assets/previews, candidate manifests/selection, workflow inspection |
| `review.revision` отдельно от `binding_revision`, allowed actions/budgets, ordered review history и exact base/result refs | Cinematic/media review projection, не перенос internal Story DTO без контракта |
| Local `CharacterV1`, exact selected refs/Bio и execution-local generated cast | Generated production memory/`CharacterChunkV1` publication, search/index и visual consumer projections |

Story approval завершает **исторический fixture или live Story-only execution**; в новом `kinodel.story-wardrobe` активирует Wardrobe до сохранённого плана. Ни один маршрут не публикует Characters автоматически. Media и остальные этапы полной production-карты обозначены `Не подключено`: это объявленный контракт, не `Demo data` и не live projection. Только отдельный mock со scripted результатами маркируется как demo. Наличие `cinematic.v1.json` не означает наличие исполняемого frontend/backend compiler.

Минимальная целевая read projection: run identity/status + frozen route; stages с `stage_id/kind/owner/status`; exact input/output refs; current review subject/request/digest/allowed actions; versioned candidates/selection; jobs с достоверным progress; discussion с порядком и subject refs; command/work outcome. Это требования к API, не объявление новых endpoints/готового DTO. Большие media bodies не грузятся в graph nodes; preview загружается по авторизованной ссылке и exact ref.

### Командный цикл

1. Получить localhost session/CSRF, затем authoritative execution read. Dev proxy использует тот же контракт; не отключать Host/Origin/CSRF ради Vite.
2. Валидировать ответ. Преобразовать его в view nodes; UI state не записывать в artifact/graph state.
3. Poll активный/waiting/blocked run, refetch при reconnect/focus; после terminal прекратить interval. Status и connection freshness — отдельные вещи.
4. Зафиксировать command payload + key **до отправки**. Повтор после потерянного ответа использует тот же payload/key; не создавать новую правку автоматически. Минимальный pending envelope хранится до reconciliation, чтобы reload не потерял identity отправки.
5. В текущем Story API `expected_revision = review.binding_revision`, **не** `review.revision`. `request_id` и digest фиксируют конкретный request. У retry — work ID + work version. Не переносить эти DTO на ещё не реализованный media API без контракта.
6. HTTP 202 означает принятие; UI показывает `Applying…`, затем читает committed state. Запретить повторную отправку с той же карточки в обоих видах. Не делать optimistic approval/result.
7. Stale/conflict/budget exhaustion — refetch, сохранить draft и показать причину. Не переназначать старое сообщение новому review автоматически. При offline/reconnecting действия заблокированы; чтение последнего snapshot доступно.

**Подача сообщений:** accepted receipt доступен в Run menu, не занимает постоянную строку canvas и не означает готовую Story/approval. Неизвестная доставка — постоянное короткое сообщение рядом с предметом с `Повторить отправку` того же envelope; подробности раскрываются. Ошибки ввода локальны, offline/storage/read failures не исчезают автоматически. Только успешное подтверждённое сохранение Characters даёт один toast справа снизу (340px, около 4s активного времени, пауза hover/focus, явное закрытие); сохранённый, но нечитаемый результат остаётся persistent warning.

## 8. Визуальная система — Graphite / Sky / Violet / Coral

**Near-black и графит с дозированными голубыми, фиолетовыми и коралловыми акцентами.** Голубой — selection/media/navigation, фиолетовый — agents/video, коралловый — human review; primary button насыщенно-синий. В standalone v10 общая фоновая текстура охватывает рабочее поле Pipeline, Canvas, Chat и вложенных scopes; панели и ноды непрозрачные, без glow. Превью внутри pipeline-ноды помогает узнать содержимое, полноценный media Canvas открывается отдельно.

| Token | Dark (основной концепт) | Light |
|---|---|---|
| Canvas/background | `#101012` | `#F5F6F7` |
| Card / panel | `#171B23` | `#FFFFFF` |
| Secondary surface | `#23272C` | `#E8EBEE` |
| Structural border | `#303846` | `#D0D5DA` |
| Text | `#F1F3F5` | `#171A1E` |
| Muted text | `#A5ADB8` | `#535D68` |
| Selection / media | `#76B9FF` | `#225DA8` |
| Primary button / text | `#366BDC` / `#FFFFFF` | `#285CC4` / `#FFFFFF` |
| Agent / video accent | `#B6A0FF` | `#7053BA` |
| Canvas atmosphere (low-opacity only) | Blue-gray `#647080`, warm stone `#8A8075` | Те же приглушённые оттенки |
| Focus/control outline | `#89939F` | `#63707D` |
| Error text | `#FF9B9B` | `#A51D2D` |
| Review text | `#FF998D` | `#A53E34` |

Primary — главное действие, sky — selection, coral — `Your decision`, red — ошибки; текст и иконки различают состояния без цвета. Completed достаточно check + текста. Нейтральные провода — порядок этапов; sky/violet применяются к media/conditioning связям. Light-значения целевые: текущий standalone проверяется только в dark.

- **Шрифт:** целевой self-hosted `IBM Plex Sans` с реальным Cyrillic subset, если интерфейс русскоязычный; моноширинный для refs/revisions при необходимости. Основной текст 14/20, вторичный не меньше 12/16 при рабочем масштабе, node title 14/20 semibold, section title 18/24. В текущем standalone `styles.css` используется `Segoe UI`, system-ui, sans-serif, без font imports; IBM Plex пока не подключён.
- **Геометрия:** 4px spacing grid; 10–12px node radius, 6–8px controls. Connected shell: header 64px с полным breadcrumb, rail 72px, без второй постоянной полосы; обычный inspector 380px, Story 520px. Standalone historical: rail 84px, header 60px, media node 260px, inspector 376px. Основные controls не меньше 44px на touch.
- **Workspace:** в standalone одна готовая texture `background v2.png` уже содержит точки и blue/coral grain; повторный dot overlay не нужен. Она покрывает все рабочие виды, но не непрозрачные панели и ноды. Edges 1.5px нейтральные, named handles 8px. Нет декоративных пунктирных потоков по всему экрану. MiniMap только по запросу, controls — zoom / fit / current stage.
- **Media:** `object-fit: contain` на review, ratio box без обрезки важных частей; маленький cover-thumbnail допустим на внешней карточке. Video не autoplay; сеть не перегружается десятками mounted players.
- **Motion:** не анимировать layout нод при polling. Принятая scoped v30-подсветка только actual claimed work: active glow/pulse, review coral и blocked amber статичны; не-connected/source-only ноды не пульсируют. Reduced motion отключает pulse; saved result не изображает продолжающийся provider call. Историческое правило standalone «без glow» не отменяет эту позднюю connected-итерацию.
- **Responsive:** ≥1280 canvas/chat и неблокирующая панель по запросу; 768–1279 details/review как native sheet; <768 Chat по умолчанию, детали full-screen, Pipeline доступен с pan/zoom. Rail с тремя страницами остаётся доступен; topbar адаптируется, сохраняя полный путь, модель/редкие действия в Run. Ниже 1280 не сжимать одновременно ноды и панель до нечитаемости.
- **Accessibility:** текст у каждого статуса; видимый focus, подписи icon buttons, Enter для информации / Shift+Enter для входа на реальных focusable Flow-нодах. Offscreen-нода раскрывается через keyboard auto-pan; отдельного списка этапов рядом с controls нет. Не требуется мышь или различение только цвета; breadcrumbs дают клавиатурный возврат. Sheet возвращает focus к исходной ноде/кнопке; toast не единственное место ошибки.

## 9. React Flow UI: публичный код и Kinodel shell

Ниже **reference для целевой production-реализации** с Tailwind/shadcn. Текущий HTML-макет не использует React BaseNode; адаптация из предыдущего React-эксперимента удалена. Пример опирается на exports публичного [Base Node registry](https://ui.reactflow.dev/base-node): `BaseNode`, `BaseNodeHeader`, `BaseNodeHeaderTitle`, `BaseNodeContent`, `BaseNodeFooter`. Варианты Kinodel и callbacks — пример нашей адаптации, не код платного шаблона.

После настройки Vite, `@/*`, Tailwind и shadcn в `web/`:

```sh
npx shadcn@4.21.0 add https://ui.reactflow.dev/base-node
```

Registry source коммитится вместе с приложением и сохраняет applicable notices. CLI command сам по себе не pin содержимого registry. Остальные packages устанавливаются exact из roadmap; это не команда установки в текущей documentation-задаче.

### `KinodelNode.tsx` — один shell для всех ролей

Пример визуального shell; gestures принадлежат родительскому Flow. Реальная click/double-click/modal защита — в `web/src/widgets/pipeline/Pipeline.tsx`, не в footer карточки.

```tsx
import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import {
  BaseNode, BaseNodeHeader, BaseNodeHeaderTitle,
  BaseNodeContent,
} from "@/components/base-node";

type NodeData = {
  title: string;
  kind: "Input" | "Agent" | "Tool" | "Review" | "Output";
  status: string; // human-readable label from the validated projection
  summary: string;
  input?: string;
  output?: string;
  nested: boolean;
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

Workspace задаёт canvas реальную высоту через `100dvh` и `min-height: 0`. Controlled nodes сохраняют actual `dimensions`/`measured` из `onNodesChange`, включая keyboard selection; потеря measured сбрасывает handle bounds и вызывает мигание edges. Click/Enter явно выбирает предмет и открывает inspector; selection из polling не открывает панель. Adapter задаёт accessible `ariaLabel` и keyboard shortcuts каждой ноде. `colorMode` разрешён workspace; controls не остаются светлыми в dark UI. Fit не вызывается при каждом polling update. Flow владеет live viewport, приложение сохраняет его по scope на `onMoveEnd`, а не на каждом pointer update. Inspector сохраняет viewport до изменения ширины и восстанавливает при закрытии. Навигация/Back не запускают работу. Pan не заменяет клавиатурную навигацию.

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
  --primary: #285cc4;
  --primary-foreground: #ffffff;
  --ring: #225da8;
  --control-outline: #63707d;
}
.dark {
  --background: #101012;
  --foreground: #f1f3f5;
  --card: #171b23;
  --card-foreground: #f1f3f5;
  --muted: #23272c;
  --muted-foreground: #a5adb8;
  --border: #303846;
  --primary: #366bdc;
  --primary-foreground: #ffffff;
  --ring: #76b9ff;
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
.kinodel-node[data-selected="true"] { border-color: var(--ring); }
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

Актуальное дерево, правила импортов, state/persistence и размещение checks/assets определяет [FSD-контракт](fsd.md). Page/widget сохраняют локальное поведение; нижние срезы выделяются по реальному владельцу и повторному использованию, без пустых слоёв. `web/prototype` остаётся standalone mock, не шаблоном production-структуры.

## 11. Граница следующей сборки

Компактный React workspace в `web/` уже подключён к fixture/live Story reads и durable commands, с отдельной локальной Characters-библиотекой. Mock-данные и локальные scripted действия не являются production-контрактом. Дальше расширять тот же workspace по мере готовности Wardrobe, cinematic/media projection. Фиксированные матрёшки — view navigation первого концепта; произвольная упаковка, graph editor, palette, общий project chat и ComfyUI editor не нужны для этого прохода.

[Препродакшн Story workspace](story-workspace-preproduction.md) от 2 октября — согласованные границы первого подключённого среза, минимальные read projections, recovery и сохранение mock; 6A–6E и визуальный каркас 6F приняты по [bounded заданиям](story-workspace-tasks.md). Dark-first/system-font — принятый вариант первой приёмки, не реализация всех целевых тем/типографики выше. Live text/Characters имеют отдельную scoped evidence; она не закрывает полный cinematic frontend.

Все рабочие задачи/критерии находятся в [шаге 6 и приёмке roadmap](../roadmap-mvp.md#remaining-steps). Здесь не ведём второй checklist. Минимальные browser checks должны подтвердить одинаковый exact review в двух видах, сохранение scope при навигации, отсутствие duplicate command при reconnect, явное отличие candidate/selected/approved и доступность на узком экране.

## Источники

Проверено 25 сентября 2026 по официальным страницам, публичному registry и npm metadata:

- [React Flow UI](https://reactflow.dev/ui), [AI Workflow Editor](https://reactflow.dev/ui/templates/ai-workflow-editor), [Base Node](https://reactflow.dev/ui/components/base-node).
- [Custom nodes](https://reactflow.dev/learn/customization/custom-nodes), [Handles](https://reactflow.dev/learn/customization/handles), [SSR](https://reactflow.dev/learn/advanced-use/ssr-ssg-configuration).
- [shadcn + Vite](https://ui.shadcn.com/docs/installation/vite), [Vite](https://vite.dev/guide/), [Pro license](https://xyflow.com/pro-license).
- Контракты Kinodel: [node](../backend/node.md), [cinematic](../pipelines/cinematic.md), [HITL](../hilp/hilp.md), [ComfyUI](../backend/comfyui.md), [текущий API source](../../backend/api.py).

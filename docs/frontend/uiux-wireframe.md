# UI/UX Wireframe — Pipeline / Chat

**[Открыть standalone-прототип](prototype/index.html) · [Запуск и сборка — web/README.md](../../web/README.md).** Живой интерактивный **MOCK, без backend**: настоящий React Flow, публичный BaseNode адаптирован под semantic CSS, без полного установленного shadcn/Tailwind app. 22 scope с per-stage mock Inputs/Outputs, внутренними схемами агентов в стиле LangGraph и путями раскрытия ComfyUI; исполнения нет.

Статус: **v0-прототип собран, дизайн пересматривается до production UI**. Ниже целевые wireframe/промпты для следующей итерации, а не описание уже реализованного HTML. Стек, tokens и backend-границы — [webui.md](webui.md). Все названия фильма, версии и счётчики ниже — **mock data** для одного согласованного примера.

## Дизайн в одной строке

Тихий графитовый инструмент для режиссёра: короткая дорожка матрёшек, фото там, где они появляются, подробности только по запросу, тот же процесс в виде чата.

Палитра — [React Flow template](refs/react%20flow%20ui%20workflow%20template.png): near-black `#101012`, поверхности `#19191c`, серо-белые controls и selection. Только canvas получает рассеянный grainy gradient в приглушённых blue-gray / warm stone тонах, как colour-field graphic art; атмосфера регулируется до отключения. Ноды без свечения, панели и Chat без декоративного градиента.

**Основная композиция:** header → узкий rail + широкая рабочая область. Правая панель закрыта по умолчанию; выбранная фотография или явное `Details` открывают её. Canvas без постоянной левой палитры, таблицы логов и второго списка всех 14 этапов. `Pipeline / Chat` переключаются в header, не дублируясь в rail. Results и Review открываются в контексте этапа. Глобальные Assets/Team/Library не занимают места до появления функций.

### Сравнение изображений и приоритеты

| Экран | Что оставить из [v0](refs/v0/) | Что изменить по новым референсам |
|---|---|---|
| Project | Честные настройки и явный Start ещё предстоит показать | [project hz](refs/zbs%20ref%20v1/project%20hz.png) слишком похож на тяжёлую административную форму: один фокус на идее, только необходимые настройки перед Run, остальные по раскрытию |
| Pipeline | Рабочий canvas и настоящие ноды | [pipeline zbs](refs/zbs%20ref%20v1/pipeline%20zbs.png) — компактная дорожка, [pipiline kaif](refs/zbs%20ref%20v1/pipiline%20kaif.png) — точки и атмосфера. Убрать обязательную правую панель и повтор медиа |
| Wardrobe | Связь portrait → sheet и отдельная location | [wardrobe zbs](refs/zbs%20ref%20v1/wardrobe%20zbs.png): фото прямо под Anchor generation, после импорта; справа только подробности выбранного фото, не копия галереи |
| ComfyUI | Проверяемая read-only схема и отдельный verified import | [comfyui zbs](refs/zbs%20ref%20v1/comfyui%20zbs.png) — меньше шума, [comfyui zbss](refs/zbs%20ref%20v1/comfyui%20zbss.png) — читаемые связи. Не показывать таблицу параметров постоянно |
| Chat | Тот же review, что и в Pipeline | [chat zbs](refs/zbs%20ref%20v1/chat%20zbs.png): крупные фото и одна задача; меньше вводного текста, никаких дублирующих панелей/карточек |

Сгенерированные изображения дают композицию, а не контракт: нарисованные model IDs, недоступные Assets/Team, размеры, fake ready/approved и графические порты не копируются в продукт. Фон с точками — базовый; живописный берег из `pipiline kaif.png` может служить необязательной атмосферой проекта, если не мешает чтению.

## 1. Project — начать производство

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│ KINODEL                           New cinematic                      Local   ◐  │
├──────┬──────────────────────────────────────────────────────────────────────────┤
│ Proj │                                                                          │
│ Work │   What are we making?                                                    │
│      │   ┌──────────────────────────────────────────────────────────────────┐   │
│      │   │ A traveller returns to a quiet island before the last ferry.  │   │
│      │   └──────────────────────────────────────────────────────────────────┘   │
│      │   Subjects   [ traveller ] [ island ] [+ Add]                            │
│      │                                                                          │
│      │   Essentials  [ 2 shots ] [ 16:9 ] [ 6s ]                             │
│      │   ▸ Generation profiles / effective settings                            │
│      │                                                                          │
│      │   Requirements and effective defaults are visible before Run.            │
│ ⚙    │                                                        [ Start run ]     │
└──────┴──────────────────────────────────────────────────────────────────────────┘
```

- В отличие от [project hz](refs/zbs%20ref%20v1/project%20hz.png) это старт идеи, а не dashboard настроек: одна читаемая textarea и один ясный Start; убираем декоративную галерею проектов, крупные карточки из одних полей и недоступные функции. Subjects задаются явно при поддержанном brief contract; не обещаем работающий library picker.
- Перед Start видны необходимые resolved settings и readiness, полные profiles/version раскрываются при желании. Числа примера не являются универсальными preset defaults.
- Внутри Brief creator явно выбирает персонажей из библиотеки `CharacterChunkV1`: один checkbox/чип на один конкретный subject; при реализации бекенда selection включает exact approved revision и разрешённую проекцию, а не поиск по строке имени. В standalone `web/` виден только локальный demo picker без канонических записей и отправки.
- Model/profile selectors похожи на React Flow AI template, но предлагают только совместимые backend-варианты. Missing profile — конкретная причина блокировки, не молчаливая подстановка модели.
- Start фиксирует конфигурацию; повторный click использует тот же key. Reopen открывает сохранённый execution.

### Txt2img — Project

```text
Create a high-fidelity 1600x1000 flat desktop screenshot of KINODEL's New Run
screen. This is an idea-first creation surface, NOT a settings dashboard.
Quiet graphite #101012, near-black #19191c, white-gray typography, crisp
14px-or-larger readable body text. A narrow rail and restrained top bar.
In a single central readable column: heading “What are we making?”, a large
film-idea textarea, optional small “Traveller” and “Island” subject chips,
one compact row of essential output choices, collapsed “Generation profiles”
disclosure, one clear “Start run” action. Show readiness only when known.
Generous empty space and deliberate hierarchy, no decorative preview images,
fake model names, redundant labels, extra sections, glow or gradients.
```

## 2. Pipeline — внешний вид матрёшек

```text
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ KINODEL  The Magic begin         [ Pipeline | Chat ]     Your decision       Run ⋯    │
├──────┬────────────────────────────────────────────────────────────────────────────────┤
│ Proj │ Cinematic / Run 04                                               Synced        │
│ Work │                                                                                │
│      │         [Brief] → [Storytell ↗] → [Wardrobe ↗] → [Storyboard ↗] → …           │
│      │          Done       Done              Review             Pending              │
│      │                         [Filmmaker ↗] → [Montage] → [Final]                   │
│      │                                                                                │
│      │        Wardrobe · Anchor set 2 · needs your decision     [Open review]          │
│      │                                                                                │
│ ⚙    │ [−] [100%] [+] [Fit] [Current]                                           [⋯]  │
└──────┴────────────────────────────────────────────────────────────────────────────────┘
```

В ASCII маршрут перенесён для читаемости. **В приложении одна горизонтальная дорожка из семи карточек:** Brief → Storytell → Wardrobe → Storyboard → Filmmaker → Montage → Final. Это view над полными 14 этапами, а не новый маршрут backend. Фон — точечная сетка поверх приглушённого grainy поля; вариант с берегом из `pipiline kaif.png` только как опция при сохранении контраста.

- В обычном состоянии **inspector закрыт**; pan/`Current` держат рабочий этап в доступе. Fit даёт overview, не пытается уместить семь форм с микрошрифтом.
- Внешняя карточка: имя, один status, стрелка раскрытия; результат и exact request доступны по `Open review`, не в каждой карточке повторно. Нет inline model selector, длинного prompt и неразборчивой metadata.
- Активный review виден даже в закрытой матрёшке. Нельзя показывать Wardrobe завершённым только потому, что агент сохранил план.
- Rail `Workspace` остаётся выбранным при входе внутрь; не появляются дополнительные глобальные меню Workflow/Review/Assets.

### Txt2img — Pipeline

```text
Design a realistic 1600x1000 desktop UI screenshot of KINODEL, an AI filmmaking
application. Neutral graphite surfaces #101012 and #19191c, readable white-gray
IBM Plex Sans-like text, precise thin borders, restrained white-gray #E4E4E7 selection.
Canvas only: subtle diffused blue-gray and warm stone colour fields with fine grain,
adjustable atmosphere; opaque nodes and panels, no node glow.
Top bar: KINODEL, “The Magic begin”, segmented “Pipeline / Chat”, review status.
Narrow icon rail on the left. Spacious dotted canvas in the center with one
horizontal production path of seven compact nodes: Brief, Storytell, Wardrobe,
Storyboard, Filmmaker, Montage, Final. Small expand arrows on nested stages.
Wardrobe has thin white-gray selection, one “Review anchors” status. An unobtrusive
“Anchor set 2 · Open review” action appears near the current stage. The right
inspector is CLOSED; do not place the same images beside the graph. All meaningful
node titles and states are readable at default zoom; no tiny embedded summaries.
Crisp product screenshot, quiet hierarchy, no neon glow, glass, analytics or
extra branches. Fine dots are more important than a decorative scenic photograph.
```

## 3. Внутри Wardrobe — агент, генерация, решение

```text
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ KINODEL  The Magic begin          [ Pipeline | Chat ]                  Your decision │
├──────┬────────────────────────────────────────────────────────────────────────────────┤
│ Proj │ ‹ Pipeline / Wardrobe                                                         │
│ Work │                                                                                │
│      │       [ Wardrobe agent ↗ ] → [ Anchor generation ↗ ] → [ Review ]             │
│      │         Plan ready             Rendering               Waiting                │
│      │                                     │                                          │
│      │         [Portrait  ↻ Generating…] → [Sheet  Waiting on portrait]             │
│      │         [Location  ↻ Queued…]        independent                             │
│      │                                                                                │
│      │         After import: [Portrait photo] → [Wardrobe sheet photo]              │
│      │                       [Location photo]       [Review complete set]           │
│ ⚙    │ [−] [Fit] [+]                                                     [⋯]         │
└──────┴────────────────────────────────────────────────────────────────────────────────┘
```

Верхняя линия — три реальные production stages. Слоты **под Anchor generation** — candidate outputs выбранного `anchor-gen`, а не второй исполняемый граф. Фото появляются только после проверенного импорта: placeholder со spinner и короткой подписью во время работы, явная причина при ошибке, никаких фиктивных процентов. Portrait → sheet — exact dependency; location независима. Число слотов задаёт план.

**Внутри самого агента:** общий shell `llm-agent` для всех четырёх ролей; меняются system prompt и входной контекст. Standalone показывает минимальную демонстрационную топологию LangGraph: `START → Model → END`, условную ветку по `AIMessage.tool_calls` в `ToolNode` и возврат `ToolMessage` в Model. Один предложенный read-only tool `read_selected_reference(alias)` читает только подготовленный разрешённый reference. SystemMessage добавляется к каждому вызову модели, не дублируется в истории; model/settings и инструкции — конфигурация, не отдельные исполняемые ноды. После END результат отдельно валидируется/сохраняется Kinodel. Это иллюстрация возможной упаковки, не trace и не утверждение о подключённом backend tool-loop. Соседний `anchor-gen` остаётся отдельным production stage. [Официальный пример](https://docs.langchain.com/langsmith/trace-with-langgraph#3-log-a-trace).

Click/Enter на **одну** готовую фотографию открывает справа только её увеличенный кадр, exact ref/parent и краткие действия. Там **нет второго ряда тех же фото**. Review полного набора — отдельный этап: выбор кандидатов и Approve в контексте набора (при необходимости широкий sheet), не в панели одиночного кадра. Нажатие на spinner не показывает несуществующий результат.

### Txt2img — Wardrobe / agent interior

```text
Create a polished 1600x1000 desktop application screenshot for KINODEL using
neutral graphite #101012, raised panels #19191c, muted gray borders, readable
white sans-serif text and restrained white-gray selection. Canvas only: subtle
diffused blue-gray and warm stone grainy gradient, adjustable atmosphere,
opaque cards without node glow. Top breadcrumb:
“The Magic begin / Wardrobe”. Keep the same narrow icon rail and top bar as
a professional node workspace. Center canvas shows only three clear Base Node
style cards: “Wardrobe agent”, “Anchor generation”, “Review”. Each card has a
small role icon, concise status and named connection, no giant embedded forms.
Immediately BELOW “Anchor generation”, show three clearly labeled output slots:
portrait with a small spinner “Generating…”, wardrobe sheet “Waiting on portrait”,
location “Queued”. A second state shows actual candidate photos replacing these
slots, with portrait → sheet exact dependency and independent location.
The right inspector is CLOSED by default, no duplicated photos. Clicking one
finished photo would open its enlarged preview and details on the right.
Full-set review remains a separate card/action. Large readable node titles and
slot labels, almost no descriptive copy, no fake completed render or parallel branches.
```

## 4. Внутри ComfyUI — tool scope

```text
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ KINODEL  The Magic begin          [ Pipeline | Chat ]                          Run ⋯ │
├──────┬────────────────────────────────────────────────────────────────────────────────┤
│ Proj │ ‹ Wardrobe / Anchor generation / hero_face / Workflow    Read-only   [Details] │
│ Work │                                                                                │
│      │ [Prompt] → [Text encode] ──┐                                                   │
│      │ [Model/CLIP/VAE] ───────────┼→ [Sampler] → [Decode] → [Save]                    │
│      │ [Size] → [Empty latent] ────┤                         │                         │
│      │ [Seed] ─────────────────────┘                         ↓                         │
│      │                                          [Verified import]                     │
│      │                                                           [Portrait photo]    │
│      │                                                                                │
│ ⚙    │ [−] [Fit] [+]                                                     [⋯]         │
└──────┴────────────────────────────────────────────────────────────────────────────────┘
```

**Схема выше концептуальная, не карта зарегистрированного workflow.** Стрелки в ASCII передают читаемый порядок, **не** точные ComfyUI sockets. Реальный экран строится из проверенного adapter mapping: positive/negative conditioning, loaders и дополнительные inputs показываются только если они действительно есть. Model loader выдаёт model/CLIP/VAE, sampler выдаёт latent, decoder — image; width/height относятся к размерам latent, а не к text encoder. Нельзя копировать неверные типы проводов из сгенерированного референса.

- Input cards — semantic parameters существующего job, read-only после preparation. `hero_sheet` использует image-conditioned workflow с exact face input; этот txt2img пример его не заменяет.
- У каждой показанной ноды отдельная подписанная дырка для каждого используемого входа/выхода. Кабель идёт от конкретного output index к конкретному `inputs.<name>` исходного API-prompt JSON; одни и те же output sockets могут питать несколько входов. Literal prompt/seed/size видны отдельными неподключёнными полями, а не вымышленными связями. Цвет приглушённо кодирует роль; названия типов в standalone — UI-подсказки, не подтверждённая ComfyUI-схема socket types. Текст остаётся различимым без цвета.
- Save — provider output. **Verified import** показан отдельно как Kinodel boundary; он не является выдуманной ComfyUI-нодой. Затем candidate попадает в полный anchor review.
- При отсутствии подробной projection остаются Inputs/Outputs и сообщение `Workflow details unavailable`. Не заявляем Krea2/v1.4 или Ready только потому, что это написано на референсе.
- Нет кнопки «запустить sampler» или повторно Run посередине active job. Retry относится к backend work, Regenerate — к текущему review, раскрытие workflow — к инспекции.
- Панель закрыта, пока не выбран конкретный output или `Details`; не дублируем превью verified import и его таблицу параметров справа постоянно. В графе ключевые ноды и типы связей читаемы без микрошрифта; технические значения — в раскрытии.

### Txt2img — ComfyUI interior

```text
Create a realistic 1600x1000 KINODEL desktop UI screenshot, matching a quiet
graphite #101012 node-based film production workspace, #19191c panels,
restrained white-gray selection, thin gray wires. Canvas only: subtle diffused
blue-gray and warm stone grainy colour fields, adjustable atmosphere, no node glow.
IBM Plex Sans-like readable labels and narrow icon rail. Breadcrumb
“Wardrobe / Anchor generation / hero_face / Workflow” and a subtle
“Read-only workflow” caption. Center graph is an illustrative text-to-image tool:
Prompt feeds Text encode; Model supplies CLIP to Text encode and model to Sampler;
Size feeds Empty latent; latent plus conditioning and Seed feed Sampler;
Sampler sends latent to Decode with VAE input; Decode sends image to Save.
After Save show a visually separate “Verified import” boundary and one portrait
candidate thumbnail ON THE CANVAS. Right inspector CLOSED; one “Details” action
could reveal selected-node config or selected-photo lineage on demand. Favor the
minimalism of comfyui zbs.png, preserve the legible connections of comfyui zbss.png.
Readable text at default zoom, no fake provider models, glowing cables, parameter
walls, floating windows, duplicated previews or approval at the decoder.
```

## 4a. Canvas — единая поверхность для кадра и клипа

Один визуальный компонент для `anchor-gen`, `frames-gen` и `video-gen`: меняются **тип ресурса** (image/video), число слотов, способ группировки и inspector, но навигация, стрелки/порты и выбор остаются прежними. Имя `Batch generation` — только UI-лейбл `frames-gen`, а не изменение маршрута [cinematic](../pipelines/cinematic.md). На телефоне сетка доступна панорамированием, детали открываются отдельным sheet; превью сохраняет порядок слотов, а не сжимается до нечитаемой миниатюры.

```text
 Wardrobe       [Anchor generation ↗] ─────→ [Anchor review ✓]
                            ↓ output
                ┌ Anchor set · 3 slots ───────────────────────────┐
                │ [Portrait] → [Sheet · parent portrait] [Location]│
                └─────────────────────────────────────────────────┘

 Storyboard     [Batch generation ↗] ──────→ [Frame review ✓]
                            ↓ output
                ┌ Batch · 2 ready · 1 generating ─────────────────┐
                │ [S01/1] [S01/2] [S01/3 ↻]  · preview only       │
                └─────────────────────────────────────────────────┘
 Inside batch   [S01/1] [S01/2] [S01/3 ↻]   Click → one inspector
                [S01/4] [S01/5] [S02/1]   Double-click → t2i graph
                [S02/2] [S02/3] [S02/4]

 Filmmaker      [Video generation ↗] ──────→ [Video review ✓]
                            ↓ output
                ┌ Clip set · one per story shot ───────────────────┐
                │ [S01 poster / player] [S02 poster / player]      │
                └─────────────────────────────────────────────────┘
 Inside video   [S01 clip] [S02 clip]       Double-click → i2v graph
```

- Карточка слота: thumbnail **или** честный placeholder/spinner, короткий shot/key + статус; video с poster/play только при наличии проверенного клипа. Nine-tile board — варианты **двух** shot keys, не девять новых сюжетных кадров; утверждение по-прежнему требует один exact start frame на shot и отдельное human review. На внешнем экране один общий contact sheet непосредственно под generation tool, не три независимые таблицы и не второй исполняемый граф.
- Click/Enter открывает справа **один** выбранный ресурс: крупный media, prompt, seed/settings, exact input refs, lineage. Для будущего video: player + duration/fps и start-image ref; никаких фальшивых клипов. Draft-поля доступны только в разрешённом состоянии; `Regenerate` отправляет версионированную команду через review/tool boundary, а не запускает ComfyUI из браузера. В standalone HTML это только локальная демонстрация состояния.
- Double-click/Shift+Enter у image/video слота ведёт в его **собственный** provider workflow: Qwen i2i для листа с parent portrait, Krea2 t2i для portrait/location и примеров start-frame, MiniMax i2v для каждого клипа. `Anchor generation` открывает t2i-схему portrait по умолчанию; другие схемы выбираются из конкретного слота. JSON-файлы — API prompt без UI-координат; экран отображает реальный `class_type`, ID и существующие связи, но не выдумывает подтверждённую установку моделей или проведённый рендер. Применимость workflow к точным approved refs проверяется отдельно адаптером.
- Коннектор верхних стадий имеет стрелку, видимые входной и выходной порты. Линия вниз от generation — **output preview**, не новый исполняемый stage. Левая кнопка выбирает, двойная входит, ПКМ по canvas поднимается к родительскому scope; колесо масштабирует, пустой canvas/средняя кнопка панорамируют. На touch есть breadcrumbs/кнопка закрытия панели, без зависимости от ПКМ.
- Preview window — один подвижный контейнер: drag за заголовок или пустую поверхность перемещает рамку **вместе** со всеми image/video слотами; drag за заголовок слота двигает только слот. Слоты позиционируются относительно окна, и перемещение не меняет approved refs, порядок shots или исполнение графа. На телефоне окно доступно pan/zoom, не ужимает плитки до микрошрифта.

### Txt2img — универсальный Image / Video Canvas

```text
Create a crisp 1600x1000 product screenshot of KINODEL's nested generation
canvas. Quiet near-black graphite #101012, opaque #19191c cards, cool-white
type, fine dotted blue-gray field, no neon or glowing wires. Top breadcrumb
Pipeline / Storyboard / Batch generation. A 3-by-3 board of start-frame
attempts for ONLY TWO shots: S01 takes 1–5 and S02 takes 1–4. Two illustrative
photo tiles, one pending tile with a small spinner, the rest queued
placeholders; each has a readable short label, no fabricated progress percent.
Select S01 take 1: show exactly one larger image and concise editable mock
prompt/seed/settings in the right inspector, one restrained Regenerate action.
Each tile can be opened into its own text-to-image workflow. Top-left small
scope navigation, zoom controls below. Thin arrowed links and small input/output
ports on workflow cards. The same board component in video mode becomes a
two-clip canvas: S01 and S02 with poster placeholders, planned duration and
start-frame references; no fabricated playable video. Calm spacing and legible
labels, no duplicated media sheet, no approval on a single tile.
```

## 5. Review sheet и детали выбранного фото

Это **два разных раскрытия**: при клике на фото — узкая панель для **одного** кадра; при `Open review` — широкий sheet для полного набора и решения. Ни одно не висит справа на каждом экране.

```text
┌────────────────────────────────────────────┐
│ Review complete anchor set           [×]   │
│ Your decision · set 2 / request r4         │
├────────────────────────────────────────────┤
│ [Face A2 ✓] [Sheet B2 ✓] [Place C1 ✓]       │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │                                        │ │
│ │     Selected candidate: hero_sheet     │ │
│ │     Full image, contained not cropped  │ │
│ │                                        │ │
│ └────────────────────────────────────────┘ │
│ hero_sheet · B2     parent: hero_face A2    │
│ [‹ Previous candidate] [Next candidate ›]  │
│ 3 / 3 selected · not approved yet          │
│ ▸ Exact versions / lineage                  │
│                                            │
│ Discuss with Wardrobe                   ▾  │
│ [Ask | Request changes]                    │
│ [Keep the coat, make its fabric rougher…]  │
│                                [Send]      │
├────────────────────────────────────────────┤
│ [Approve anchor set 2]        [More ▾]      │
│ Next: Storyboard                           │
└────────────────────────────────────────────┘
```

Этот sheet открывается только для review: скроллится body, action footer закреплён. `More` может содержать поддерживаемый Regenerate; Cancel run остаётся в Run menu. При клике по конкретному фото из Wardrobe отдельно открывается узкая панель **без повторного contact sheet**: крупный кадр, его статус, exact ref/parent, disclosure для технических деталей. Selecting candidate не равно approval.

**Три раздельных состояния:** candidate существует; candidate выбран локально; backend применил approval. В примере галочки обозначают выбор, подпись `Not approved` остаётся до committed decision. Новый subject сбрасывает применимость прежнего выбора; UI не переносит его молча.

Config не становится редактором frozen prompt. Просьба поменять ткань идёт в `revise` Wardrobe. Ask сохраняет output, но может открыть новый request — рядом отдельно показываем `set 2` и `r5`. Просмотр старого set заменяет footer на `Historical version / Return to current review`.

### Txt2img — Inspector / review

```text
Design a close-up 1200x1000 product UI screenshot of KINODEL after an explicit
“Open review” action. Show a wide focused REVIEW SHEET, not a permanent inspector.
Neutral graphite #101012, #19191c surfaces, readable white-gray type, minimal
copy and unclipped media. Header “Anchor set 2”, separate “Request r4”. Three
candidate images: traveller portrait, clothing sheet, empty coastal location;
clearly show selection vs approval. One enlarged image for comparison, concise
exact parent/lineage in a collapsed disclosure. Sticky footer: explicit
“Approve anchor set 2”; small “Ask / Request changes” action. The canvas remains
visible behind the sheet, with subtle dots and grain only there. Do not repeat
the same contact sheet in another panel; no giant config form, glow or fake state.
```

## 6. Chat — работа без canvas

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│ KINODEL  The Magic begin           [ Pipeline | Chat ]     Your decision       │
├──────┬──────────────────────────────────────────────────────────────────────────┤
│ Proj │ Storytell ✓  ·  Wardrobe: review  ·  Storyboard  ·  Filmmaker  ·  Final   │
│ Work │                                                                          │
│      │       You                                                                │
│      │       A traveller returns to a quiet island before the last ferry.       │
│      │                                                                          │
│      │       ▸ Storytell · Story v2 · Approved                                   │
│      │                                                                          │
│      │       Wardrobe                                                           │
│      │       [Persisted owner response, when available]                         │
│      │       ┌──────────────────────────────────────────────────────────────┐   │
│      │       │ Anchor set 2 · Request r4                  View in pipeline │   │
│      │       │ [Portrait A2]    [Wardrobe B2]    [Coastline C1]             │   │
│      │       │ Selected 3 / 3 · not approved                                │   │
│      │       │ [Review larger]                    [Approve anchor set 2]   │   │
│      │       └──────────────────────────────────────────────────────────────┘   │
│      │                                                                          │
│      │       To Wardrobe · Anchor set 2 · Request r4                             │
│      │       [ Ask | Request changes ]                                          │
│      │       ┌──────────────────────────────────────────────────────────────┐   │
│      │       │ Keep the coat, make its fabric rougher…                Send │   │
│ ⚙    │       └──────────────────────────────────────────────────────────────┘   │
└──────┴──────────────────────────────────────────────────────────────────────────┘
```

Лента 760–880px max-width; inspector закрыт. `Review larger` использует тот же review sheet. Когда run работает, над composer одна компактная activity-строка, а отправка недоступна до actionable review. Пустые «агент думает…» сообщения не сохраняются как разговор. Крупные кадры из [chat zbs](refs/zbs%20ref%20v1/chat%20zbs.png) — главный контент; убираем второй заголовок, длинную вводную речь и повтор статусов в каждом блоке. Один result = одна карточка, раскрывается только нужное.

**Сценарий целиком в Chat:** Start из формы → Story card → Request changes → Story v2 → Approve → anchor contact sheet → frame sheet → video review → Final player/download. Только текущая карточка интерактивна, старые доступны для чтения. Автоматизация не включает auto-approve.

Ни reply, ни статус не сочиняется интерфейсом: если backend вернул только artifact, показываем artifact card. Внутренний Story fixture может проверить начальный текстовый участок; media-карточки требуют соответствующего API.

### Txt2img — Chat mode

```text
Create a high-fidelity 1600x1000 desktop screenshot of KINODEL in Chat mode.
Use the same neutral graphite #101012 background, #19191c cards, thin gray borders,
white IBM Plex Sans-like typography and restrained white-gray #E4E4E7 actions as a
minimal node editor. Top bar has project “The Magic begin” and Pipeline / Chat
switch with Chat selected. Narrow icon rail on the left. No node canvas in this
view; no decorative gradient or grain outside the canvas. Center a spacious 800px
conversation column. At the top a compact production step strip, then a short
user film brief, a collapsed “Story v2 · Approved” item, and exactly one large
Wardrobe result card containing three prominent cinematic anchor images:
traveller portrait, clothing sheet, empty island coast. Card shows “Anchor set 2”,
“Request r4”, “View in pipeline” and “Approve anchor set 2”. Bottom composer has
explicit recipient Wardrobe and Ask / Request changes toggle. Use short labels and
readable body text, no duplicated overview, imaginary agent responses/avatars,
colorful bubbles, right inspector, code console, glow or glass.
```

## 7. Состояния, финал и адаптивность

| Ситуация | Что видит пользователь | Доступное действие |
|---|---|---|
| Empty draft | Форма идеи с видимыми defaults/subjects | Start после валидации |
| Loading | Skeleton нужного preview, неизменный layout | Навигация без мутирующих действий |
| Running | Имя действующего stage/unit; progress только если известен | Inspect, Cancel run |
| Waiting review | Точный subject, request, выбор/полнота | Разрешённые Approve / Ask / Request changes |
| Command accepted | `Applying…` на той же карточке в обоих видах | Дождаться authoritative outcome |
| Reconnecting | Последний snapshot + `Connection lost · checking run` | Читать; refetch, без повторного Run |
| Stale review | `This review has changed` и переход к текущему | Перепроверить subject; draft не теряется |
| Blocked | Причина у реального этапа, например unavailable profile | Только объявленное восстановление/Cancel |
| Unknown provider acceptance | `Checking submission`, не «Generate again» | Reconcile; без blind retry |
| Cancelling / Cancelled | Различимые промежуточное/терминальное состояния | Сохранённые outputs доступны |
| Complete | Final player, silent output summary, provenance, Download | Смотреть/скачать; не фиктивный Approve final |

Final использует Output card и тот же player как в Pipeline, так и в Chat. У ноды Montage внутри — ordered approved clips → assembly → verification; у Final — файл. Это не дополнительный LLM-монтажёр.

### Узкий экран

```text
┌────────────────────────────────┐
│ KINODEL   Silent Shore    [⋯]  │
│ [ Pipeline | Chat ]            │
│ Wardrobe · Your decision       │
├────────────────────────────────┤
│ ▸ Story v2 · Approved          │
│ Anchor set 2 · r4              │
│ [portrait] [sheet] [location]  │
│ [Review larger]                │
│ [Approve anchor set 2]         │
├────────────────────────────────┤
│ To Wardrobe · set 2            │
│ [Ask | Request changes]        │
│ [Message…              Send]  │
└────────────────────────────────┘
```

≥1280px — панель деталей только по запросу; 768–1279px — overlay sheet; <768px — Chat как начальный вид, полный review отдельным sheet и компактное меню вместо rail. Canvas доступен с touch pan/zoom; desktop-нодам не задаём ширину `100vw` в world coordinates. На каждом размере main action, версия и предмет решения видимы без горизонтального скролла панели.

## 8. Как проверять концепт

Промпты выше самостоятельные: одинаковые palette, chrome и шрифт позволяют сравнивать изображения. Текст внутри txt2img может искажаться — результат оценивает композицию и стиль, а источником UI copy и маршрута остаётся этот документ. Не переносить придуманные генератором кнопки, model IDs и связи в приложение.

При walkthrough последовательно проверить: понятен ли текущий этап с закрытой матрёшкой; открывается ли точный review за один переход; различимы ли конфигурация/inputs/outputs; виден ли parent sheet; можно ли пройти те же решения в Chat; сохраняются ли scope и draft при переключении. Исполняемая приёмка и порядок работ — в [Local MVP](../roadmap-mvp.md#remaining-steps).

# UI/UX Wireframe — Pipeline / Canvas / Chat

**[Standalone HTML-макет](../../web/prototype/index.html) · [Запуск — web/prototype/README.md](../../web/prototype/README.md).** Интерактивный **MOCK, без backend**, на HTML/CSS/JS. Отдельный [React Flow эксперимент](prototype/index.html) — предыдущая ветка дизайна, не production shell `web/`.

Статус: **v0-прототип собран, дизайн пересматривается до production UI**. Ниже целевые wireframe/промпты для следующей итерации, а не описание уже реализованного HTML. Стек, tokens и backend-границы — [webui.md](webui.md). Все названия фильма, версии и счётчики ниже — **mock data** для одного согласованного примера.

## Дизайн в одной строке

Графитовый инструмент для режиссёра: Pipeline показывает путь и компактные превью, отдельный Canvas собирает все изображения и видео проекта, инспектор раскрывает выбранный материал. Chat — альтернативный вид процесса, доступный в standalone как локальный mock.

**Текущий standalone v10:** одна горизонтальная дорожка из семи нод по [pipeline zbs nodes kaif](refs/zbs%20ref%20v1/pipeline%20zbs%20nodes%20kaif.png), но завершённые Brief/Storytell обозначены зелёными галочками (не точками), оранжевая рамка относится только к текущему Wardrobe review. Краткие описания и действие Review anchors доступны без открытия инспектора. Точный [background v2](refs/zbs%20ref%20v1/background%20v2.png) уже содержит точки и лежит на всех рабочих поверхностях, включая Chat и вложенные scopes; вторую сетку не добавляем. Правый клик по Canvas asset открывает production stage его категории, по пустому полю — последний Pipeline scope с прежним viewport; левый клик по-прежнему открывает инспектор, workflow доступен отдельно. Rail/breadcrumbs и Shift+Enter остаются клавиатурной альтернативой. Ни один переход не исполняет граф.

**Текущий standalone v11:** v10 — историческая база; rail вместо Final содержит Montage (Final — output в Pipeline). На Canvas остаются 14 медиа-карточек, но нет ports/wires; lineage portrait → sheet показывается в инспекторе. В Pipeline L0 именованные границы групп не притворяются связями artifact→следующая группа: стрелки показывают approval order, внутри L1 реальные plan/current-set handoffs и отдельно contextual refs/profiles. Новые отдельные поверхности Brief (immutable submitted fixture + validated unsent draft) и Montage (2 planned clips, silent cuts, no output) используют background v2. Chat имеет один owner-bound unsent composer и компактный current review. Скриншоты — [v11](../../test-results/screenshots/standalone-html/v11-workspace-clarity/).

Палитра — **Graphite / Sky / Violet / Coral**: near-black `#101012`, рабочее поле `#10141B`, поверхности `#171B23`, borders `#303846`, текст `#F1F3F5`. Голубой `#76B9FF` — selection, media и навигация; насыщенный синий `#366BDC` — primary button; фиолетовый `#B6A0FF` — агенты и video; коралловый `#FF998D` — human review. Цветные акценты дозированы, статусы всегда подписаны. Тонкие точки и слабая синяя/фиолетовая атмосфера только на рабочем поле, без свечения нод и проводов.

**Основная композиция:** header → левый rail 84px с иконками и подписями **Pipeline / Canvas / Brief / Review / Final** → рабочая область. Canvas — самостоятельный пункт, не слой внутри generation. Review ведёт к текущему точному предмету, Final — к выходу Montage. Справа по выбору материала открывается инспектор 376px как в [canvas mb](refs/canvas%20mb.png): крупное превью, Open in workflow, вкладки Prompt / Settings / Metadata, доступное действие. На телефоне rail становится нижней навигацией, inspector — full-screen sheet. Header Pipeline / Chat переключает workspace и хронологию, сохраняя scope, viewport и локальный текст сообщения.

### Сравнение изображений и приоритеты

| Экран | Что оставить из [v0](refs/v0/) | Что изменить по новым референсам |
|---|---|---|
| Project | Честные настройки и явный Start ещё предстоит показать | [project hz](refs/zbs%20ref%20v1/project%20hz.png) слишком похож на тяжёлую административную форму: один фокус на идее, только необходимые настройки перед Run, остальные по раскрытию |
| Pipeline | Короткая дорожка и настоящие ноды | [pipeline preview](refs/pipeline%20preview.png): текстовые выдержки и миниатюры внутри карточек, голубое выделение, коралловый review |
| Canvas | Связь portrait → sheet и отдельная location | [canvas mb](refs/canvas%20mb.png): крупные media-ноды, фильтры, правый инспектор. Полные наборы живут только здесь; в Wardrobe остаётся компактное превью и ссылка |
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
Graphite #101012, #171B23 panels, white typography; sky #76B9FF selection,
violet #B6A0FF subject chips, restrained coral #FF998D review accents.
Readable 14px body text. Rail: Pipeline, Canvas, Brief, Review, Final.
In a single central readable column: heading “What are we making?”, a large
film-idea textarea, optional small “Traveller” and “Island” subject chips,
one compact row of essential output choices, collapsed “Generation profiles”
disclosure, one blue #366BDC “Start run” action. Show readiness only when known.
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
- Внешняя карточка: имя, один status, компактное превью содержимого и Open inside. Brief/Storytell — короткий текст; Wardrobe/Storyboard — миниатюры; Filmmaker/Montage/Final — video poster только при наличии файла, иначе подписанный placeholder. Это summary, не вложенная доска и не отдельный player в каждой карточке.
- Активный review виден даже в закрытой матрёшке. Нельзя показывать Wardrobe завершённым только потому, что агент сохранил план.
- Rail `Pipeline` остаётся выбранным внутри production stage; `Canvas` — внутри media и его workflow. Переход между ними сохраняет рабочий scope и viewport; Brief, Review, Final дают прямые shortcuts.

### Txt2img — Pipeline

```text
Design a realistic 1600x1000 desktop UI screenshot of KINODEL, an AI filmmaking
application. Graphite #101012 and #171B23 surfaces, readable white IBM Plex Sans-like
text, borders #303846. Sky #76B9FF selection and media accents, violet #B6A0FF
agent/video accents, coral #FF998D review. Subtle dotted blue-gray work surface,
opaque nodes, no glow. Top bar: KINODEL, “The Magic begin”, “Demo data”.
Left icon-and-label rail: Pipeline (selected), Canvas, Brief, Review, Final.
Spacious work surface in the center with one
horizontal production path of seven compact nodes: Brief, Storytell, Wardrobe,
Storyboard, Filmmaker, Montage, Final. Small expand arrows on nested stages.
Inside the nodes show short text excerpts for Brief/Storytell, three anchor thumbnails
for Wardrobe, a two-frame strip for Storyboard. Video stages show labeled waiting
placeholders unless a real output exists. Never embed another canvas inside a node.
Wardrobe has a thin sky-blue selection, one coral “Review anchors” status. An unobtrusive
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
│      │                              [small thumbnail strip]                        │
│      │                              [View in Canvas ↗]                             │
│      │                                                                                │
│ ⚙    │ [−] [Fit] [+]                                                     [⋯]         │
└──────┴────────────────────────────────────────────────────────────────────────────────┘
```

Три реальные production stages; внутри generation только небольшое превью и **View in Canvas → Anchors**. Полные медиа-слоты не повторяются ни под нодой, ни внутри дополнительного batch scope. На Canvas portrait → sheet показывает exact dependency, location независима; число слотов задаёт план. Фото появляются после проверенного импорта, ожидание и ошибки подписаны.

**Внутри самого агента:** общий shell `llm-agent` для всех четырёх ролей; меняются system prompt и входной контекст. Standalone показывает минимальную демонстрационную топологию LangGraph: `START → Model → END`, условную ветку по `AIMessage.tool_calls` в `ToolNode` и возврат `ToolMessage` в Model. Один предложенный read-only tool `read_selected_reference(alias)` читает только подготовленный разрешённый reference. SystemMessage добавляется к каждому вызову модели, не дублируется в истории; model/settings и инструкции — конфигурация, не отдельные исполняемые ноды. После END результат отдельно валидируется/сохраняется Kinodel. Это иллюстрация возможной упаковки, не trace и не утверждение о подключённом backend tool-loop. Соседний `anchor-gen` остаётся отдельным production stage. [Официальный пример](https://docs.langchain.com/langsmith/trace-with-langgraph#3-log-a-trace).

Click/Enter на **одну** готовую фотографию открывает справа только её увеличенный кадр, exact ref/parent и краткие действия. Там **нет второго ряда тех же фото**. Review полного набора — отдельный этап: выбор кандидатов и Approve в контексте набора (при необходимости широкий sheet), не в панели одиночного кадра. Нажатие на spinner не показывает несуществующий результат.

### Txt2img — Wardrobe / agent interior

```text
Create a polished 1600x1000 desktop application screenshot for KINODEL using
graphite #101012, raised panels #171B23, readable white sans-serif text,
sky #76B9FF selection, violet #B6A0FF agent accents and coral #FF998D review.
Subtle blue-gray dots on the work surface,
opaque cards without node glow. Top breadcrumb:
“The Magic begin / Wardrobe”. Keep the same narrow icon rail and top bar as
a professional node workspace: Pipeline, Canvas, Brief, Review, Final. Center shows three Base Node
style cards: “Wardrobe agent”, “Anchor generation”, “Review”. Each card has a
small role icon, concise status and named connection, no giant embedded forms.
INSIDE “Anchor generation”, show a small three-thumbnail summary and “View in Canvas”.
Do not put a second media board below it. Full portrait, wardrobe and location
nodes belong to the separate Canvas destination, reached with the Anchors filter.
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
graphite #101012 node-based film production workspace, #171B23 panels,
sky #76B9FF selection/media wires, violet #B6A0FF conditioning accents,
coral #FF998D reserved for human review. Other wires neutral, no glow.
IBM Plex Sans-like readable labels; rail Pipeline, Canvas, Brief, Review, Final.
Canvas selected. Breadcrumb “Canvas / hero_face / Workflow” and a subtle
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

**Один самостоятельный Canvas всего проекта**, открываемый из rail. Фильтры All media / Anchors / Images / Video — представления тех же объектов, не копии досок. Generation-ноды ведут сюда с нужным фильтром. `Batch generation` остаётся UI-именем `frames-gen`, без изменения backend route. Standalone v10 показывает ровно три физические строки без внешних рамок: 3 anchors, 9 frame attempts в одну линию, 2 pending clips. S01/S02 на самих карточках. На desktop 1600×1000 и 1440×900 все 14 слотов видны при закрытом inspector; с панелью карточка не уже 120px, конец ряда доступен pan (Fit не сжимает текст). Фон — общий `refs/zbs ref v1/background v2.png` без дополнительной сетки. Верхняя строка объединяет проект, breadcrumbs, контекст и переключатель вида; повторного заголовка Canvas нет. На мобильном Canvas карточки панорамируются, inspector раскрывается full-screen. `New shot · coming soon` отключён.

```text
  Header        The Magic begin / Canvas                         Demo · Pipeline / Chat
  Rail          [All media | Anchors | Images | Video]           Inspector (on selection)
  Pipeline      ANCHORS                                          S01 · take 1 [×]
  Canvas ●      [Portrait] → [Sheet]  [Location]                 [landscape preview]
  Brief         IMAGES                                           [Details | Prompt | Settings | Lineage]
  Review        [S01 takes 1–5][S02 takes 1–4] — same line      [state / seed / example workflow values]
  Final                                                          [Open in workflow ↗]
                VIDEO
                [S01 waiting] [S02 waiting] [+ New shot · soon]  No approval on one tile
                [− 100% + Fit]
```

- Карточка текущего standalone Canvas адаптирует ширину по доступному desktop-полю: thumbnail или честный placeholder/spinner, shot/key, статус и подписанные порты. Workflow открывается из инспектора выбранного media, не кнопкой на каждом tile. Девять frame attempts — варианты двух shots, не девять сюжетных кадров. Video без файла не имеет Play. Между независимыми takes нет декоративных проводов; единственная media-зависимость — Portrait → Wardrobe sheet, Location независима.
- Click/Enter открывает справа **один** выбранный ресурс: крупный media, prompt, seed/settings, exact input refs, lineage. Для будущего video: player + duration/fps и start-image ref; никаких фальшивых клипов. Draft-поля доступны только в разрешённом состоянии; `Regenerate` отправляет версионированную команду через review/tool boundary, а не запускает ComfyUI из браузера. В standalone HTML это только локальная демонстрация состояния.
- Workflow / double-click / Shift+Enter ведут в собственный provider scope выбранного материала: Qwen i2i для sheet, Krea2 t2i для image-примеров, MiniMax i2v для clips. Breadcrumb возвращает в Canvas с прежним фильтром и viewport. JSON projections — исследовательские примеры, не обещание установленного provider.
- Нет вложенной рамки preview window. Каждый материал — самостоятельная нода на одном поле. Drag заголовка двигает карточку; пустая поверхность/средняя кнопка панорамируют; колесо масштабирует. Связи показывают только имеющиеся зависимости, например portrait → sheet; между независимыми takes не рисуем вымышленное исполнение.
- Inspector: компактное preview; по умолчанию Details с табличными state/ID и фактически известным локальным seed, моделью/размером/steps/sampler **примерного API-prompt**, не фактического рендера. Неизвестный seed — `Not recorded`. Prompt / Settings / Lineage сохраняют черновик frame prompt/seed при навигации; Regenerate · mock лишь переводит слот в Queued. Open in workflow доступен без прокрутки desktop-панели, approval остаётся в полном exact review.

### Txt2img — универсальный Image / Video Canvas

```text
Create a 1600x1000 KINODEL Canvas screenshot: the supplied blue/coral background
with subtle dots behind individual dark cards, sky selection and coral review.
Left 84px rail with Canvas selected. One header row: project / scope breadcrumb
on the left, demo / context / Pipeline–Chat switch on the right. No duplicate
Canvas heading. Category filters All media / Anchors / Images / Video only.
Show three unboxed category sections on one surface: 3 Anchors (Portrait → Sheet;
Location independent), 9 Images (S01 takes 1–5 and S02 takes 1–4 on one
horizontal row), 2 pending Video slots and disabled New shot. No wires
between independent takes. No Workflow footer buttons on cards. S01 take 1
selected with a blue outline. Right 376px inspector: compact contained landscape
preview, default Details as dense labeled rows (state, known local seed and clearly
marked example-workflow model/size/sampler/steps), Prompt / Settings / Lineage,
one Open in workflow action visible without scrolling. Never claim example API
settings describe the stock image; unknown values say not recorded. No fake video
or per-tile approval. Bottom-left zoom / fit controls.
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
Graphite #101012, #171B23 surfaces, readable white type, sky #76B9FF selection,
blue #366BDC approve action, violet #B6A0FF owner accent, coral #FF998D decision
badge. Same rail: Pipeline, Canvas, Brief, Review, Final. Minimal copy and unclipped
media. Header “Anchor set 2”, separate “Request r4”. Three
candidate images: traveller portrait, clothing sheet, empty coastal location;
clearly show selection vs approval. One enlarged image for comparison, concise
exact parent/lineage in a collapsed disclosure. Sticky footer: explicit
“Approve anchor set 2”; small “Ask / Request changes” action. The canvas remains
visible behind the sheet, with subtle dots and grain only there. Do not repeat
the same contact sheet in another panel; no giant config form, glow or fake state.
```

## 6. Chat — работа без canvas

**Standalone v07:** одна колонка до 920px, тихая полоса этапов, brief без пузыря, свёрнутый Story, одна карточка anchor set. `Production steps` и `Creative decisions` свёрнуты по умолчанию; внутри — иллюстративные шаги и короткое объяснение плана, не скрытый reasoning и не live trace. Материалы открывают общий Canvas inspector, `Review anchor set` — существующие exact review details. Composer адресован Wardrobe / set 2 / r4, различает вопрос и правку; `Save draft` честно сохраняет неотправленное сообщение до reload. Ниже — целевой подключённый сценарий с настоящими approval/send.

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
Use graphite #101012, #171B23 cards, #303846 borders, white IBM Plex Sans-like type,
sky #76B9FF selection, blue #366BDC primary actions, violet #B6A0FF owner labels
and coral #FF998D review badges. Top bar has project “The Magic begin” and a
Pipeline / Chat switch with Chat selected. Rail: Pipeline, Canvas, Brief, Review,
Final; Pipeline owns this alternate process view. No node canvas in this
view; no decorative gradient or grain outside the canvas. Center a spacious 920px
conversation column. At the top a compact production step strip, then a short
user film brief, a collapsed “Story v2 · Approved” item, and exactly one large
Wardrobe result card with collapsed “Production steps” and “Creative decisions”
disclosures (short plan explanation, never a fabricated hidden reasoning trace),
containing three prominent cinematic anchor images:
traveller portrait, clothing sheet, empty island coast. Card shows “Anchor set 2”,
“Request r4”, “View in pipeline” and one “Review anchor set” action. Bottom composer has
explicit recipient Wardrobe and Ask / Request changes control. For the offline mock,
label its action “Save draft” and identify unsent local messages; use Send/Approve
only for the connected product. Use short labels and
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

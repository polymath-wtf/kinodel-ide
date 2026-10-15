# Артефакты: structured input/output, связи данных и версии

**Статус: целевое поведение MVP.** Физический формат хранения выбирается при сборке плагина; это не готовая схема Hermes.

Ниже зафиксирован логический контракт для реализации. JSON-примеры — проектируемые структуры Kinodel, не существующие API Hermes. Имена schema и версии условны; конкретные host APIs и физическое хранилище уточняются в целевом Hermes.

## Три разных контракта

| Контракт | Что содержит | Кто отвечает |
|---|---|---|
| Stage definition | Роль исполнителя, input/output schemas, bindings, допустимые tools и условие перехода | Автор фиксированного workflow |
| Prepared input | Разрешённые в точные версии значения входов, refs, инструкции и feedback одного задания | Plugin перед dispatch |
| Artifact revision | Полный валидный результат с происхождением; для media — ссылки на originals | Plugin после проверки ответа/tool result |

Worker получает смысловые данные, а не только пути и IDs. Prompt объясняет поля и задачу; backend проверяет schema и подставляет данные по явным bindings. Ни модель, ни UI не вычисляют следующий этап.

## Structured input/output этапов

Поля ниже задают минимальный смысловой состав; окончательные JSON Schemas оформляются вместе с реализацией. Все обязательные поля, единицы измерения и допустимые значения должны быть определены до вызова.

| Этап | Structured input | Structured output |
|---|---|---|
| Producer / preproduction | `idea`, `answers`, `selected_references`; текущий `brief`, если уже сохранён | Пока опрос не завершён — вопросы; после опроса — полный `brief.json`. Изменения создают новую Brief revision |
| Storytell | Полный подтверждённый `brief`: `idea`, `characters`, `locations`, `visual_direction`, `shot_count`, `duration_seconds`, настройки и выбранный narrative context | `title`, `logline`, `narrative`, `characters`, `locations`, `shots[]` с `shot_id`, `subject_ids`, `location_id`, `state_before`, `action`, `state_after`, `duration_seconds` |
| Wardrobe | Полный `brief`, **полный approved `story`**, его `characters`/`locations`, `visual_direction`, выбранные visual refs и возможности image profile | `anchors[]`: ровно `portrait`, `location`, `character_sheet`, по одному logical unit; `unit_id`, `role`, subject/location binding, `prompt`, `references[]` и зависимости |
| Storyboard | Полный `brief`, **полный approved `story`**, его `shots`, approved anchor selections, `visual_direction`, image profile guidance | `frames[]`: `shot_id`, opening-frame `prompt`, точные anchor refs и объявленные earlier-frame dependencies |
| Filmmaker | Полный `brief`, **полный approved `story`**, его `shots`, approved frame selections, согласованные durations и video profile guidance | `clips[]`: `shot_id`, motion/camera `prompt`, точный frame ref, `duration_seconds` |
| Render / tool | Конкретный plan item, exact media refs, frozen supported settings | Candidate refs, receipt и проверенные media metadata; не creative approval |
| Montage / tool | Approved clips в порядке `shots`, output settings | Final media ref, source clip refs и результат технической проверки |

Количество/порядок шотов согласуются с brief, IDs не переиспользуются для другого смысла. `references` указывают роли данных, а не произвольные provider payloads. Ответ сохраняется полностью, не как patch к тексту в чате.

**Полная Story — обязательный вход всех трёх визуальных специалистов.** Это весь утверждённый объект, включая narrative и все shots, не summary и не одна ссылка. `characters`, `locations`, `shots` — удобные field bindings той же revision; они не заменяют Story и не выбираются независимо из другой версии. Producer тоже видит полную текущую Story. Render/Montage — tools: им достаточно точного плана и media inputs, творческое чтение сценария не требуется.

## Brief: один документ, последовательные версии

До завершения опроса идея и ответы живут в беседе Producer. После опроса он собирает **Brief** с актуальными параметрами проекта; отдельного артефакта предварительного брифа нет. Автор проверяет конкретную версию и подтверждает запуск.

`brief.json` — представление текущей выбранной версии того же документа. История сохраняет неизменяемые `brief_v1.json → brief_v2.json → brief_v3.json`; это версии, а не разные виды brief. Точное устройство current-ссылки/экспорта определим с Hermes. Производство и подготовленные операции всегда ссылаются на revision/digest, не на изменяемый путь `brief.json`.

Пример сохранённого Brief; значения творческих и размерных параметров иллюстративны, не доказательство поддержки на сервере:

```json
{
  "artifact_id": "brief-r1",
  "schema": "Brief@1",
  "project_id": "lighthouse",
  "revision": 1,
  "digest": "<sha256 canonical content>",
  "created_by": {
    "kind": "agent",
    "agent_id": "producer",
    "profile": "kinodel-producer",
    "operation_id": "op-brief-1",
    "worker_session_id": "session-producer"
  },
  "content": {
    "idea": "Мира замечает первый свет на заброшенном острове.",
    "characters": [{"id": "mira", "name": "Мира", "description": "Смотрительница маяка в тёмном плаще"}],
    "locations": [{"id": "shore", "name": "Берег", "description": "Каменистый берег напротив острова, сумерки"}],
    "visual_direction": "Сдержанный кинореализм, холодный свет, спокойная камера",
    "visual_references": [],
    "duration_seconds": 5,
    "shot_count": 1,
    "generation": {
      "image": {
        "provider": "comfyui",
        "txt2img_workflow": "krea2-txt2img",
        "img2img_workflow": "qwen21-multi-img2img",
        "width": 1024,
        "height": 1024,
        "aspect_ratio": "1:1"
      },
      "video": {
        "provider": "comfyui",
        "workflow": "minimax-h3-img2vid",
        "mode": "img2vid",
        "quality": "480p",
        "width": 480,
        "height": 480,
        "aspect_ratio": "1:1"
      }
    }
  }
}
```

Здесь один герой и одна локация соответствуют трём anchor units MVP. Конкретные размеры видео, соответствие quality и длительности проверяются с выбранным workflow до запуска; неподдержанные параметры обсуждаются с автором, не подменяются. Workflow IDs ссылаются на конфигурацию; точные версии/digests файлов фиксирует подготовка операции. API payloads, endpoint и credentials не входят в Brief. Brief может быть создан до production/task, поэтому их IDs не выдумываются; запуск позже закрепляет точную Brief revision.

### Полнота настроек Brief

Пример выше сокращён: перед запуском Brief содержит все пользовательские настройки выбранного render profile, включая согласованные defaults. MVP допускает ровно одного героя и одну локацию во всём Story.

| Поля / группа | Что фиксирует Producer |
|---|---|
| `shot_count`, `duration_seconds`, `shot_durations_seconds` | Число шотов, общую длительность и упорядоченный список длительностей; длина списка и сумма совпадают с первыми двумя полями |
| `generation.image` | Provider, txt2img/img2img workflow, width/height/aspect; default 1024×1024, 1:1 (1K) |
| `generation.video` | Provider, workflow, mode, quality, width/height/aspect; default img2vid, 480p, 480×480, 1:1 |
| `generation.image.workflow_settings`, `generation.video.workflow_settings` | Настройки по выбранному workflow: seed policy (`random_per_candidate` или `fixed` с seed), steps/CFG, FPS и прочие exposed controls только при подтверждённой поддержке. Для random seed конкретное число выбирает backend один раз перед submit и сохраняет в заказе |
| `generation.video.frame_fit` | Явная политика подготовки image input к video geometry; для квадратных defaults — resize 1024×1024 → 480×480 без crop. Поддержка проверяется adapter |
| `output` | MP4, согласованные width/height/FPS, `audio: none`, полные клипы в порядке Story без творческой обрезки |

Producer получает перечень поддержанных полей, значений и defaults от backend/profile, не придумывает параметры workflow. Нужное, но неизвестное значение блокирует подтверждение. Настройки workflow выбираются до запуска; prompts и exact media refs добавляются позже из планов/selection. Технические node IDs, credentials, template digest и фактические receipts принадлежат adapter/операции, а не творческому Brief. В подготовленном заказе сохраняются все effective settings; скрытых изменяемых defaults после подтверждения нет.

При изменении параметров Producer сохраняет новую полную версию Brief. Уже подготовленные операции используют прежнюю revision; последствия изменения определяет [граница правок](#граница-правки-фиксация-входов-следующей-операции).

## Декларативные связи: что куда передаётся

Пример части фиксированного `cinematic.pipeline`; пути — ограниченная нотация доступа к полям, не исполняемые выражения или произвольный код:

```json
{
  "stage_id": "wardrobe",
  "assignee": "kinodel-wardrobe",
  "input_schema": "WardrobeInput@1",
  "output_schema": "AnchorPlan@1",
  "required_input": {
    "brief": "brief.output",
    "story": "storytell.output",
    "characters": "storytell.output.characters",
    "locations": "storytell.output.locations",
    "visual_direction": "brief.output.visual_direction",
    "visual_references": "brief.output.visual_references"
  },
  "required_approval": ["brief.output", "storytell.output"],
  "next": "anchor_generation"
}
```

`kinodel-wardrobe` — предлагаемое имя профиля, не утверждение о наличии в установке. Связи заданы шаблоном и доступны для просмотра на нодах. UI показывает «Полная история ← Story v2» и «Персонажи ← та же Story v2 / characters», позволяет раскрыть содержимое и происхождение. Storyboard и Filmmaker также имеют обязательный binding `story: storytell.output`, а не только `shots`. Редактор произвольных маршрутов для этого не нужен.

`required_input` — карта обязательных входов и их источников. Schema проверяет структуру значений. Field bindings вроде `characters` — проекции той же Story revision. Допустимый пустой список references считается переданным значением.

`required_approval` — источники из карты входов, требующие **решения человека** на точную revision/selection. Валидный AnchorPlan передаётся render tool без отдельного согласования плана.

До dispatch backend разрешает `required_input` в точные версии, проверяет schema и решения из `required_approval`, затем сохраняет prepared input с `resolved_bindings`. При отсутствии входа или approval этап ожидает без вызова LLM.

Пример части **подготовленного задания**, где binding уже разрешён:

```json
{
  "operation_id": "op-wardrobe-1",
  "production_id": "production-1",
  "stage_id": "wardrobe",
  "input_schema": "WardrobeInput@1",
  "resolved_bindings": {
    "story": {
      "artifact_id": "story-r2",
      "revision": 2,
      "digest": "<sha256>",
      "pointer": "/content",
      "approval_id": "approval-story-r2"
    },
    "characters": {
      "artifact_id": "story-r2",
      "revision": 2,
      "digest": "<sha256>",
      "pointer": "/content/characters",
      "approval_id": "approval-story-r2"
    }
  },
  "input": {
    "story": {
      "title": "Последний свет",
      "logline": "Мира замечает сигнал с острова.",
      "narrative": "На тёмном острове вспыхивает свет; Мира замечает его.",
      "characters": [{"id": "mira", "name": "Мира"}],
      "locations": [{"id": "shore", "name": "Берег"}],
      "shots": [{
        "shot_id": "shot-01",
        "subject_ids": ["mira"],
        "location_id": "shore",
        "state_before": "Мира смотрит на тёмный остров",
        "action": "На острове вспыхивает свет",
        "state_after": "Мира замечает сигнал",
        "duration_seconds": 5
      }]
    },
    "characters": [{"id": "mira", "name": "Мира"}]
  }
}
```

Показана часть prepared input: полная Story и один field binding из неё. Brief и остальные поля таблицы также обязательны в реальном задании. Разрешённые refs фиксируются до работы; technical retry не подставляет новую Story v3. При повторной подготовке body читается та же неизменяемая версия и проверяется digest. Недоступное обязательное поле блокирует dispatch, а не заменяется предположением агента.

## Ответ специалиста и приём результата

```json
{
  "status": "completed",
  "created_by": {
    "kind": "agent",
    "agent_id": "storytell",
    "profile": "kinodel-storytell",
    "stage_id": "storytell",
    "operation_id": "op-story-revise-2",
    "task_id": "task-storytell",
    "run_id": "run-2",
    "worker_session_id": "session-storytell"
  },
  "output": {
    "title": "Последний свет",
    "logline": "Мира замечает сигнал с заброшенного острова.",
    "narrative": "На тёмном острове вспыхивает свет; Мира замечает его.",
    "characters": [{"id": "mira", "name": "Мира"}],
    "locations": [{"id": "shore", "name": "Берег"}],
    "shots": [{
      "shot_id": "shot-01",
      "subject_ids": ["mira"],
      "location_id": "shore",
      "state_before": "Мира смотрит на тёмный остров",
      "action": "На острове вспыхивает свет",
      "state_after": "Мира замечает сигнал",
      "duration_seconds": 5
    }]
  }
}
```

Выходы образуют tagged union: `completed` с полным `output`; `question` с `questions`; `failed` с `error.code`, `message` и при необходимости ссылкой на проблемный вход. `completed` означает полный ответ попытки; backend отдельно проверяет результат, человек утверждает его. Worker не выбирает retry или следующий этап. Ошибка инфраструктуры может формироваться host/plugin без ответа модели.

`question` — вопрос автору по смыслу переданных материалов, например о противоречии между Story и каноническим референсом. Попытка завершается без новой revision; ответ автора передаётся через feedback/rework той же task. Технические ошибки возвращаются как `failed`. Producer собирает сведения для Brief в обычной беседе.

`created_by` присутствует в ответе и сохраняемом артефакте для любого исхода. Служебную часть заполняет/проверяет plugin по фактическому запуску; модель не придумывает свою task/session identity. У агентного результата обязательны `kind: agent`, `agent_id` и фактический профиль, плюс доступные IDs операции/task/run/session. Для tool-артефакта — `kind: tool`, `tool_id`, операция и ссылки на входной агентный план; для прямого авторского изменения — `kind: user` и actor. Отсутствующие host IDs обозначаются явно, а не выдумываются. Так видно, кто создал каждый результат: Storytell, Producer, render tool или автор.

Plugin проверяет schema, coverage/order, ссылки, принадлежность заданию и разрешённую область результата. Только после этого публикует новую revision. Невалидный JSON или частичный ответ сохраняется как диагностика попытки, не как готовая история. Для невалидного output разрешены **до трёх дополнительных schema-repair попыток после первой** (максимум четыре ответа): тот же input, ошибка валидатора и полный исправленный output. Лимит сохраняется для логической работы и не сбрасывается restart. Host-лимиты могут остановить раньше. После исчерпания — остановка и явное решение автора; без ремонта кода/окружения. Эти retries не разрешают повторные render submits и не подменяют творческие правки. Самостоятельный ремонт кода/окружения агентом запрещён, в случае чего он должен дать ошибку, а не идти править баг.

## Физические связи и владельцы хранения

```text
project_id
  └─ production_id + workflow version + submitted brief ref
       └─ stage_id → board_id + task_id
            ├─ operation_id → prepared input + exact refs
            ├─ Kanban run/attempt → worker session_id (если host предоставляет)
            └─ artifact_id/revision → JSON + digest
                 ├─ approval_id → точная revision/selection
                 └─ candidate_id → request/receipt → original media + digest
```

Kanban владеет task, attempt/run и своей историей; Hermes sessions — беседами. Plugin хранит недостающие производственные связи, решения и результаты. `operation_id`, `task_id`, `run_id` и `session_id` не взаимозаменяемы. Особо различаем session создателя карточки (например Producer) и фактическую worker session: поле с происхождением task не доказывает связь с чатом исполнителя.

Иллюстративная раскладка, не обязательные пути Hermes:

```text
<project-root>/<project-id>/
  artifacts/brief_v1.json             # до создания production
  artifacts/brief_v2.json             # новая неизменяемая версия того же Brief
  brief.json                         # current-представление; не pinned input
  productions/<production-id>/
    inputs/<operation-id>.json
    artifacts/<artifact-id>.json
    originals/<candidate-id>.<ext>
```

Сопоставления IDs с путями, approvals и reservations должны иметь атомарные записи; пригодный host storage выбираем при реализации, иначе добавляем только недостающие metadata. Не имитируем транзакционность набором произвольно переписываемых JSON-файлов. UI получает refs и разрешённые media URLs, не читает файловую систему напрямую.

Kanban attachments могут хранить input snapshot и опубликованный JSON либо служить ссылками на материалы проекта. Для каждого original выбирается один canonical storage owner; scratch и временный URL не являются архивом. `kanban_request_review(artifacts=...)` документирует сохранение объявленных scratch deliverables перед cleanup, но не заменяет наши версии и approvals.

Пример публикуемого envelope — служебной оболочки сохранённого результата:

```json
{
  "artifact_id": "story-r2",
  "schema": "Story@1",
  "project_id": "lighthouse",
  "production_id": "production-1",
  "stage_id": "storytell",
  "revision": 2,
  "digest": "<sha256 canonical content>",
  "created_by": {
    "kind": "agent",
    "agent_id": "storytell",
    "profile": "kinodel-storytell",
    "stage_id": "storytell",
    "operation_id": "op-story-revise-2",
    "task_id": "task-storytell",
    "run_id": "run-2",
    "worker_session_id": "session-storytell"
  },
  "input_snapshot_id": "input-story-revise-2",
  "input_refs": [{"artifact_id": "brief-r1", "revision": 1, "digest": "<sha256>"}],
  "supersedes": "story-r1",
  "content": {
    "title": "Последний свет",
    "logline": "Мира замечает сигнал с острова.",
    "narrative": "На тёмном острове вспыхивает свет; Мира замечает его.",
    "characters": [{"id": "mira", "name": "Мира"}],
    "locations": [{"id": "shore", "name": "Берег"}],
    "shots": [{
      "shot_id": "shot-01",
      "subject_ids": ["mira"],
      "location_id": "shore",
      "state_before": "Мира смотрит на тёмный остров",
      "action": "На острове вспыхивает свет",
      "state_after": "Мира замечает сигнал",
      "duration_seconds": 5
    }]
  }
}
```

`content` содержит полный проверенный `output`. Digest вычисляется системой по определённой канонической сериализации content, не включает сам себя. Происхождение и IDs добавляет plugin из фактической попытки, не из догадки модели; недоступный worker session ID явно отсутствует. Approval — отдельная запись с actor, target ref/digest и expected revision, не изменяемый флаг внутри immutable артефакта.

## Сквозной input/output flow

```text
Подтверждённый brief
→ schema/binding resolution + freeze exact input
→ Kanban task / dispatcher / ограниченный worker
→ structured output
→ schema + domain validation
→ immutable artifact + task handoff refs
→ human review точной версии
→ durable approval
→ подготовка следующего input по bindings
```

Публикация и approval должны предшествовать допуску downstream. При сбое между сохранением результата и обновлением Kanban повтор использует ту же operation/artifact, а не вызывает модель заново. Событие служит сигналом перечитать состояние; `done` без валидного approval не выпускает следующую работу. Контракт общий для действий из Producer, панели специалиста и UI-кнопок.

## Что сохраняется

Автор может открыть прошлую историю, увидеть точный prompt картинки и понять, из каких кадров собран фильм. Для этого сохраняем полные версии brief, story и планов, originals изображений/видео, настройки и seed каждого заказа, его входы, выбранные дубли и решения автора. Ответ в чате или временный provider URL не заменяет материал проекта.

| Понятие | Простое правило |
|---|---|
| Проект | Общая папка замысла и всех его запусков |
| Производство / запуск | Один проход cinematic с зафиксированным brief; имеет собственный ID |
| Версия результата | Новая сохранённая история или план внутри этапа, предыдущая не перезаписывается |
| Дубль | Отдельная генерация одной картинки/клипа со своим request и точными входами |
| Выбор | Какой дубль автор хочет использовать для каждого образа/шота |
| Approval | Автор принял конкретную версию или полный набор выбранных дублей |

Связь материала содержит проект, производство, этап, revision/candidate ID и digest содержимого. Номера вроде «Story v3» — подписи внутри производства, не глобальные идентификаторы. Историю сообщений хранит Hermes; plugin связывает её с производством и результатами, не заводит второй transcript store.

## Правки текущего этапа

Producer передаёт специалисту замечание, предыдущий полный результат и точные входы. Специалист возвращает новую полную версию на review. «Почему герой ушёл?» — обсуждение; «измени финал» — задание на правку. Старое approval не переносится на новую версию.

### Напрямую специалисту и в его рабочий чат

Автор может адресовать замечание Storytell непосредственно из панели Storytell, без пересказа через Producer. Адресат определяется `production_id + stage_id + task_id + artifact_ref`, не свободным выбором модели. Панель показывает историю карточки и доступные worker transcripts; фактические attempts остаются различимыми.

| Ситуация | Поведение |
|---|---|
| Текущая task ожидает review | Сохранить feedback к точной версии и вернуть ту же карточку исходному implementer через поддержанный human rework lifecycle. Новая попытка возвращает новую полную revision |
| Worker ещё работает | Не открывать параллельный turn в его session. Live steering допустим только при проверенной поддержке; иначе замечание сохраняется для явной доработки после результата |
| Task уже завершена | Не использовать произвольный chat turn как скрытый reopen. Новое задание/производство по правилам изменения использованных результатов |
| Продолжение прежней worker session | Пользователь проверил такую возможность в Hermes. Используем её для rework; точный вызов, связь с claim/attempt и ограничения требуется выяснить в целевой установке |
| Host создаёт свежую session для rework | Сохраняем ту же task и профиль, передаём предыдущий полный результат, замечания и входы. UI не выдаёт это за продолжение одного transcript |

Документировано **same-card rework к исходному implementer**; пользователь дополнительно сообщил о проверенном продолжении прежней worker session внутри Kanban lifecycle. Наличие возможности принято как пользовательское свидетельство; способ подключения к плагину ещё не установлен. Уточнение сохранено в [вопросах к Hermes](hermes-questions.md). Generic session chat API сам по себе не обеспечивает Kanban ownership, tools и запись результата в нужный attempt; не запускаем его параллельно dispatcher.

На human-only board `kanban_request_changes` из reviewer-run и human `reopen-review` — разные входы lifecycle; точное plugin-действие выбираем по установленному контракту. Простой `kanban_comment` не является командой revise. Источник: [worker lanes](../hermes-docs/kanban/kanban-worker-lanes.md):79–93; [Kanban](../hermes-docs/kanban/kanban-big-context.md):1124–1131, 1174, 1354.

### Граница правки: фиксация входов следующей операции

Решающая граница — **сохранённый prepared input зависимой операции**, а не её статус «running» и не появление готового файла. До этой границы можно явно переоткрыть текущий review и создать новую revision/selection в том же производстве. Если следующая task создана без подготовленных входов, она должна остаться недоступной до нового approval; точный Kanban lifecycle уточним у Hermes.

После фиксации ссылки в следующей операции изменение использованного результата требует **нового связанного производства**, даже если worker ещё не стартовал. Уже подготовленные inputs не переписываются. Это относится и к Brief после подготовки Storytell, и к кадру после подготовки video request. Старые результаты и approvals сохраняются. Запрос правки и подготовка следующего этапа должны проверять эту границу согласованно, без race между двумя действиями.

Это граница замены принятого входа следующего этапа, а не запрет дополнительных дублей на текущем неутверждённом review. Например, новый portrait и новый sheet от него можно создать в том же anchor review: это новые render requests, старый sheet и его parents не изменяются. После approval набора и фиксации входов Storyboard замена набора уже требует нового производства.

Поздний дубль не меняет утверждённый selection автоматически. Просмотр старых материалов не создаёт новую работу; остановка старого производства и запуск нового — явные действия.

## Поздняя редакторская правка Story

После фиксации входов следующей операции отредактированный полный текст сохраняется как следующая Story revision с `supersedes` и автором, без применения к уже подготовленному производству. Например, фильм сделан по Story v2, а Story v3 — редакторская версия, не применённая к фильму. UI показывает обе роли явно; Producer получает производственную Story и редакторскую версию только при её обсуждении.

Сохранение такой версии не снимает approvals с прежних материалов, не вызывает LLM/render и не объявляет старые кадры совместимыми с новым текстом. Старые inputs остаются ссылками на v2. Если автор хочет применить изменение к производству, действует прежнее правило нового связанного запуска. Автоматическое определение «пара слов ничего не меняет» и выборочная пересборка вне MVP.

При изменении плана на текущем review прежние планы/candidates сохраняются с прежними refs; готовые units одного неизменённого плана не повторяются при техническом восстановлении. **Предложение для MVP:** новая revision плана создаёт новый набор, без автоматического переноса candidates между планами. Для изменения одного prompt без полного нового плана есть manual Generate конкретной unit; зависимые candidates должны соответствовать новым exact parents. Это проще автоматического сравнения влияния правок.

## Выбор из нескольких дублей

1. Агент подготовил план, tool создал дубль A. Он доступен, но не утверждён.
2. Автор сделал ещё B, C, D в [render-инспекторе](hermes-webui.md). Все четыре остаются в истории.
3. Автор выбирает C. Последний полученный D не вытесняет этот выбор.
4. Когда для каждого обязательного элемента выбран один совместимый дубль, автор утверждает набор этапа.

Совместимость проверяется по точным входам: зависимая картинка от образа A не становится картинкой от образа B при смене выбора. Новые зависимые дубли создаются явно. Выбор из устаревшего окна не перезаписывает более новое решение.

## История и новый запуск старого проекта

В истории производства доступны brief, версии истории/планов, запросы, настройки, дубли, выбранные наборы и финал. Просмотр не вызывает модель или провайдера. Сохранённые оригиналы читаются локально; повреждённый или отсутствующий файл показывается как недоступный.

**«Создать новый запуск из этого»** берёт выбранную историческую Brief revision и явные refs за основу, сохраняет `based_on` исходного производства/версии. Если автор меняет параметры, Producer выпускает следующую полную Brief revision; автор подтверждает точную версию для нового запуска. Отдельного draft-документа не появляется. Старый фильм остаётся нетронутым, новый проходит весь маршрут и получает новые approvals.

Так можно повторить старую идею и настройки, но нельзя обещать побайтово тот же результат генерации. В MVP не копируем старые approvals, не делаем автоматический reuse downstream и не строим дерево merge/fork. Для интерфейса достаточно списка запусков с подписью «на основе…». Hermes session fork ветвит **разговор**, а не материалы и платные заказы; он не требуется для этой функции.

## Хранение и операции

Неизменяемые JSON-результаты и original media принадлежат проекту, не scratch/cache плагина. Навигационный индекс можно перестроить. Решения автора и состояние операций сохраняются отдельно от чатового summary; конкретное atomic storage сначала ищем у host.

До работы фиксируем точные входы, версию инструкций, параметры и logical operation ID. Повтор доставки той же операции возвращает сохранённый статус/результат; новая творческая правка или **Generate** создаёт новую операцию. Approval проверяет ожидаемую версию и полноту выбранного набора перед открытием следующего этапа.

Для render сохраняем provider receipt и originals. После неопределённого submit выясняем исход, а не отправляем новый заказ автоматически. Разрешение запуска и дополнительных генераций явно; используем доступные лимиты host, без нового универсального budget engine. Перезапуск и Continue не расширяют разрешённую работу. Детали провайдеров и повторов — [render](hermes-kinodel-render.md); состояния — [ноды](hermes-nodes.md); точный контекст — [контекст](hermes-kinodel-context.md).

## Что уточнить перед исполняемыми JSON Schemas

- Какие поля обязательны, какие допускают отсутствие/null, какие enum и единицы измерения используются? Brief создаётся после опроса; неполные ответы остаются беседой, не альтернативной schema.
- Как проверять связи `subject_ids`/`location_id`, уникальность и порядок shot/unit IDs, сумму длительностей и соответствие Brief?
- Какие изменения разрешены в revise одного шота? Рекомендация: не менять shot count, IDs других шотов и согласованные параметры без отдельного изменения Brief и оценки границы prepared input.
- Как сериализовать и версионировать полный `story` и его field bindings без независимых расходящихся копий? Все поля должны разрешаться из одной approved revision.
- Проверять ровно одного героя и одну локацию во всём Brief/Story; более широкий замысел Producer сужает с автором до запуска. Не оставлять дополнительных действующих лиц без anchor-покрытия.
- Как отображать отсутствующие host IDs в `created_by`, принимать file/tool output и отклонять лишние/невалидные поля? Рекомендация: единый валидатор публикации, независимо от Kanban `completed/done`.

Сначала оформляем и проверяем Brief → StoryInput → StoryOutput → approval, затем остальные schemas. Примеры в этом документе не заменяют эти проверки.

Основания: [исходные правила артефактов](../../backend/artifacts.md) — продуктовые принципы, не перенос их storage; [Hermes sessions](../hermes-docs/backend/api-server.md):603–619 — история и session fork; [delegation](../hermes-docs/backend/delegation.md):55–59 — завершение child не заменяет валидацию результата.

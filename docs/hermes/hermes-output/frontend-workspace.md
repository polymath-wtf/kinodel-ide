---
title: "Frontend — творческое рабочее пространство"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, frontend, artifacts]
sources: [raw/kinodel-plugin-raw/hermes-webui.md, raw/kinodel-plugin-raw/pipeline reference.png, raw/kinodel-plugin-raw/canvas reference.png]
confidence: medium
status: preproduction
---

# Frontend — творческое рабочее пространство

**Целевой UX, не макет работающего приложения.** React Flow отвечает за обзор и навигацию, а не за исполнение workflow. Producer находится в чате, не отдельной исполнительной ноде. ^[raw/kinodel-plugin-raw/hermes-webui.md]

## Представления одного проекта
| Представление | Вопрос автора | Содержимое |
|---|---|---|
| Producer chat | Что мы делаем и что нужно уточнить? | Диалог, Brief, вопросы, карточки версий и адресный feedback |
| Pipeline | Где производство и чего оно ждёт? | Brief → Storytell → Wardrobe → Storyboard → Filmmaker → Montage → Final |
| Canvas | Какие образы, кадры и клипы составляют фильм? | Anchors, группы shots в Story-порядке, соседние candidates, selections и реальные зависимости |
| Библиотека/история | Что уже создано и откуда это взялось? | Originals, revisions, планы, prompts, прошлые productions; не отдельная копия данных |
| Inspector | Что именно выбрано и что с ним можно сделать? | Preview, inputs/output, instructions, settings, lineage и разрешённые действия |

Библиотека обязательна как пользовательская возможность просмотра материалов; нужна ли ей отдельная вкладка или достаточно фильтров Canvas/History — вопрос UX, не повод строить второй asset store.

## Что действительно видно на Pipeline-референсе
Тёмная рабочая область, узкая левая навигация Pipeline/Canvas/Brief/Review/Final, верхний контекст проекта и переключатель Pipeline/Chat. В центре горизонтальный ряд семи равных карточек со связями, статусами, миниатюрами и действием. Wardrobe выделен янтарной рамкой и Needs review; внизу zoom, Fit и Current stage. **Правый инспектор на этом скриншоте не открыт.** ^[raw/kinodel-plugin-raw/pipeline reference.png]

![[raw/kinodel-plugin-raw/pipeline reference.png]]

Берём композицию, визуальную иерархию и акцент текущего review. Не считаем текст Submitted/Approved доказательством готового backend. Brief — документ; не переносим Producer из чата в граф.

## Что действительно видно на Canvas-референсе
Сверху фильтры All media/Anchors/Frames/Videos и выбор shot; есть Flow/Grid. В центре группа Anchors и две строки shots с изображениями, пустыми generating/queued карточками и видео. Справа инспектор выбранного дубля с Details/Prompt/Settings/Lineage, inputs и действиями. Выбранная карточка выделена синим. ^[raw/kinodel-plugin-raw/canvas reference.png]

![[raw/kinodel-plugin-raw/canvas reference.png]]

**Не переносим буквально:** на скриншоте дубли соединены цепочкой, а anchors изображены линейно. В продукте альтернативные takes — соседи, не последовательные операции. Настоящая зависимость sheet — от portrait **и** location. Демонстрационные размеры 1920×1080, названия моделей, числа assets, дата и Regenerate/Open workflow не становятся контрактами MVP. Обязательность Grid также ещё не выбрана.

## Inspector: два уровня
**Этап:** исполнитель/profile, подготовленная версия role instructions/skills, полные structured inputs/output, typed bindings с точными revisions, task/run links, validation и approval отдельно. Нельзя назвать `SKILL.md` всем системным prompt или обещать скрытые внутренние данные.

**Материал:** image/video preview и playback, unit/shot/candidate, parent refs, prompt, seed и только поддержанные settings, requested/measured metadata, автор и история. Полный original открывается без генерации.

Рабочая цепочка: изменить prompt/settings → **Generate candidate** → сравнить → **Select** → **Approve stage**. Generate создаёт новый дубль без обязательного LLM, Select ничего не рендерит, Approve относится к полному совместимому набору. ^[raw/kinodel-plugin-raw/hermes-webui.md]

## Действия и состояния
- «Вопрос специалисту» и «Запросить правку» различаются; адресат привязан к task/stage/version, не свободному выбору модели.
- Нельзя открыть конкурентный turn в работающей worker session; точный rework API пока неизвестен.
- Частичный набор доступен для просмотра, но не approval.
- Ошибка показывает причину и разрешённое действие; unknown submit не предлагает слепой retry.
- Stop не обещает отмену уже принятого provider job.
- История явно различает «фильм по Story v2» и «редакторская v3, не применена».
- Новый запуск из старого — явное действие, не побочный эффект просмотра. ^[raw/kinodel-plugin-raw/hermes-webui.md]

## Состояние и доступность
Backend владеет фактами производства и разрешениями; UI — viewport, focus, открытым inspector, фильтрами и несохранёнными полями формы. Навигация сохраняет project/production/stage/material. После команды и reconnect перечитываются факты; потеря событий не создаёт новую генерацию.

Панорамирование, zoom, Fit и фокус этапа доступны видимо. Граф фиксирован: пользователь не переподключает edges. Нужны клавиатура/focus, текстовые статусы наряду с цветом и list/scroll-представление для узкого экрана. Предложенные компоненты: оболочка, StageCard, CanvasView, MediaCandidateCard, Inspector, ProducerChat, ReviewActions, HistoryView; окончательные названия не зафиксированы. ^[raw/kinodel-plugin-raw/hermes-webui.md]

Связи: [[kinodel-preproduction/pipeline-and-gates]], [[kinodel-preproduction/agents-and-context]], [[kinodel-preproduction/artifacts-and-revisions]].

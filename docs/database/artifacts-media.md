# Артефакты и медиа

Статус: **существующие invariants; рекомендуемая физическая детализация**. Источники: [Artifact Store](../backend/artifacts.md), [Render](../agents/render.md), [cinematic units](../pipelines/cinematic.md#unit-contracts), [ComfyUI](../backend/comfyui.md). Открытые решения: [Q2/Q7/Q8/Q13](open-questions.md).

## Идентичность и связи

| Сущность | Canonical содержание | Связи/ограничения |
|---|---|---|
| `artifacts` | Метаданные immutable revision: schema/version, digest, internal URI, project/execution, stage/operation | `artifact_id` означает ревизию, не документ со сменяемым телом; commit owner задан graph |
| `execution_bindings` | Текущий exact artifact и slot revision | Новый artifact + OCC replacement; старые версии не меняются |
| `assets`, с media | Digest, managed URI, kind/MIME и измеренные properties выбранного/imported файла | Метаданные согласованы с байтами; public URL не identity. Нужен project/access owner, даже если компактный AssetRef его не содержит |
| `jobs`, с renderer | Intent, request identity, endpoint/profile/workflow versions, owned attempts, provider ID и restricted audit | Separate job claim/fence; никакого исполнения из незаписанного request |
| Group/wait, с renderer | Stage/activation, immutable wait ID/request digest, ordered required units, terminal receipt | Один stage-level wait; mutable job version не identity ожидания |
| Candidates, с renderer | Candidate ID, job/unit, URI/digest, technical metadata | Inspectable, но не assets/artifact bindings; rejected остаются history по retention |
| Candidate manifest, с renderer | Immutable полный упорядоченный набор unit/candidate/job refs и dependency provenance | Join отвергает missing/duplicate/extra/wrong-request units; selection ровно одна на required unit |

Названия group/candidate tables ещё не определены: #question Q13. Рекомендуем минимальные дочерние записи к jobs и immutable group manifest; не invent `render_requests` artifact и не хранить всю группу как изменяемый provider JSON без identity. Поддерживающие frame/motion/montage plans валидируются, но не получают независимое approval от утверждения результата.

## Dependencies и provenance

Каждый commit хранит exact source IDs/digests, stage/capability version, operation, creation time, selected assets и context source/resource revisions. Рекомендуем проверяемые dependency entries при artifact metadata: source kind/ref, mode, для `current_execution` source execution/slot/binding revision и requires_approval. Вынесение в relation rows полезно для reverse lookup/GC; точные columns и FK остаются #question Q7, не новый универсальный графовый движок.

- `current_execution`: source slot и вся транзитивная production closure должны совпадать. Старый FramePlan делает потребляющий его RenderResult stale даже до замены slot FramePlan.
- `pinned_revision`: exact внешняя/shared revision, не latest binding. Supersede/archive при сохранённых данных не меняет вход старого execution; rights withdrawal/purge блокирует.
- Provenance не может иметь циклов. Право читать artifact не автоматически разрешает использовать все его закрытые sources/media.

Не превращать каждый shot/frame/beat в таблицу только ради ER-модели. Первый `i2v` использует Story shot keys и порядок в frame/clip plans/results. `main` является отдельным anchor unit; выбранный `source_shot_id` принадлежит FramePlan. Downstream selector `{render_result_ref, unit_key}` разрешает точный AssetRef; новая независимая frame identity не нужна.

## Managed storage

Действующий локальный layout:

```text
projects/<project_id>/
  artifacts/<artifact_id>.<digest>.json
  assets/<asset_id>.<digest>.<ext>
  attempts/<job_id>/<candidate_id>.<digest>.<ext>
  runtime-audit/<job_id>/...
```

Это server-generated logical prefix, не пользовательский путь и не per-chat каталог. При remote deployment object keys сохраняют ту же семантику; backend root/bucket выбирается отдельно. Экспорт `/outputs/` может быть удобным представлением, но не вторым writable canonical store. Сканирование каталогов никогда не выбирает текущий результат.

### Открыть, переместить, экспортировать

Автор открывает проект по имени, видит запуски, текущие результаты и историю версий; ему не требуется искать JSON по hash или помнить старый chat. Рекомендуем сохранить один stable `project_id` и корень проекта независимо от имени, разговоров и executions. Абсолютный путь установки не должен определять identity в сохранённых refs: logical URI разрешается относительно выбранного storage root. Точное кодирование URI ещё относится к Q7.

`artifacts/` и `assets/` содержат производственные оригиналы; `attempts/` содержит кандидаты, а `runtime-audit/` закрыт от обычного экспорта. Наличие `assets/` не означает human approval каждого файла. Предлагаемый `outputs/` показывает выбранные для выдачи результаты с понятными именами, execution и revision, но правка экспортной копии не меняет оригинал. Импорт такой правки создаёт новый source/candidate и следует разрешённому review пути, не перезаписывает approved artifact.

Рекомендуем производный index/manifest (оглавление с ID, версиями и digest) для просмотра и экспорта, не ещё один writable реестр. Live UI получает актуальные bindings/approvals из БД; stale index можно перестроить. Export manifest фиксирует конкретный снимок, но не выдаёт локальным импортёрам права исходного сервера. Отдельные manifest и index таблицы до функции экспорта не нужны.

| Действие автора | Минимальный рекомендуемый смысл | Ограничение |
|---|---|---|
| Перенести каталог на другой диск в той же установке | Остановить запись/GC, проверить полную копию и digest, переключить storage root, затем возобновить | IDs и DB records сохраняются; ручной rename при работающем worker не поддерживаем |
| Скачать результаты / импортировать на другой установке | Выдать выбранные материалы и manifest; импорт валидирует файлы, типы, права и provenance в новом project | Это reuse, не перенос live execution или доверие чужим approvals/ACL. Не импортировать checkpoints из непроверенного архива |
| Перенести незавершённую работу / восстановить после потери диска | Согласованный перенос DB + checkpoints + bytes + нужных версий кода/resources по [restore protocol](operations-security.md#backup-и-restore) | Одна папка без БД не возобновляет производство; не запускать две writable копии |

#question Q20: полный локальный backup DB + files и перенос на другую машину нужны; открыты формат и UI с различием экспорта результатов и резервной копии. Минимум: maintenance backup всей установки. Выборочный live import одного проекта требует отдельного протокола и пока не обещается.

- #todo Перед выпуском переноса проверить root change без смены refs, missing/changed bytes, stale manifest, конфликт импортируемых IDs и запрет путей вне import root; архив не может назначать ACL, выполнять код или активировать worker.

### Запись байтов

1. Подготовленная операция фиксирует intended objects/pins, exact inputs и expected bindings до внешнего эффекта.
2. Валидированные байты stage/sync/publish без overwrite. Существующий destination допустим только при совпадении digest.
3. Одна DB transaction проверяет fence/cancel/activation/closure/OCC и фиксирует metadata, assets, provenance, binding, result и next activation.
4. Только committed metadata делает объект видимым читателям. Crash между publication и commit оставляет orphan, не половину принятого artifact.
5. Replay committed operation возвращает recorded result; missing/corrupt committed bytes означает integrity block, не новую генерацию под старым ID.

Filesystem и DB не имеют общей атомарной транзакции. Rename сам по себе не доказывает power-loss durability на любой ОС. [Storage contract](../backend/artifacts.md#managed-project-storage) требует испытать file sync, no-overwrite и directory durability на фактическом носителе.

#question Q8: до start transaction обычной execution operation ещё нет, а исходные bytes уже публикуются. Рекомендуем долговечное start reservation по project/client key с payload digest и intended object pin, финализируемое той же start transaction. Это недостающая конкретизация общего pin-протокола; не добавлять незаписанную «достаточно свежую» папку как замену. Согласовать поля/abandonment до миграции.

## Возврат к раннему этапу

**Принято:** автор возвращается к раннему этапу того же проекта через новую execution/ветку исполнения из exact prefix, сохраняет старые immutable outputs и сравнивает варианты. Это не rewind старой Project DB, не произвольный checkpoint jump и не отдельная система branch pointers. Текущий `revise` ограничен своим gate: Critic разбирает замечание, владелец результата создаёт новую полную версию. «Критик исправляет» описывает пользовательский процесс, не владение всеми artifacts.

1. Автор выбирает source execution, target stage и exact prefix до него. [Физическое предложение](../backend/rework.md) рекомендует для первого включения только terminal source: незавершённую E1 явно отменяют и ждут worker finalization. Прежний вариант stable pause отложен, поскольку пауза может гоняться с другой decision/wake. Snapshot/receipts проверяются при start; E1 не стирается, E2 получает собственный thread. Это рекомендация narrowing, не уже испытанная реализация.
2. Start payload E2 фиксирует parent execution, target, замечание, exact refs/digests, dependency closure, source approval/promotion receipts и pipeline/settings/context versions. Stable client key с изменённым payload конфликтует. Entry stage только из allowlist authored graph, не произвольный checkpoint клиента.
3. Reuse operation E2 проверяет graph/schema/profile compatibility, целостность, права всей closure и approvals там, где они требуются. Supporting plans требуют validation, не выдуманного approval. Человек явно подтверждает reuse показанного prefix; receipt E2 фиксирует заимствование неизменных результатов, не approval изменённого текста. Неполный prefix блокирует start.
4. Исторические artifacts не переписываются и не получают подменённый `execution_id`. Предлагаются E2 bindings на исходные exact refs плюс reuse receipt операции. Это требует явного validator contract: внутреннюю историческую closure imported prefix проверять как frozen `pinned_revision` snapshot, не сравнивать с будущими bindings E1. Просто копировать старые `current_execution` dependencies нельзя. Новые результаты E2 используют `current_execution` относительно bindings E2, включая reused inputs; смена binding делает новые descendants stale. Для imported entry нужен matching reuse receipt, не blanket exemption для чужих refs.
5. Target и всё после него не копируются в текущие bindings E2. Старый target остаётся exact reference для Critic/owner и сравнения. Отдельная authored rework-entry операция передаёт feedback Critic, затем фиксированному owner; новый candidate получает новый gate. При изменении Brief prefix не содержит approved Brief; при изменении Story неизменный Brief может быть reused. Новая Story не наследует approval и совместимость старых clips.
6. UI сравнивает E1/E2 по refs; вкладка не меняет approvals/bindings. Старые callbacks адресованы только E1. GC учитывает reuse closure E2. General merge, selective shot reuse и перенос старых interrupts/checkpoints не нужны.

Это принятый архитектурный контракт, не уже работающая возможность resolver. [Rework DTO/protocol](../backend/rework.md) конкретизирует receipts, start pins/transaction, foundation entry allowlist и non-ready Critic без текущего E2 subject; [physical DTOs](../backend/physical-dtos.md) задают refs/closure. Q21 сохраняет проверку/утверждение этих предложений. До включения проверенного rework-entry обычный start проходит Brief review с историческими sources. UI не предлагает пропуск этапов до реализации и проверки.

- #todo Проверить unchanged Brief reuse -> новая Story, missing approval/closure/rights, изоляцию E1/E2, old callback, duplicate start, crash вокруг reuse commit и отсутствие генерации prefix. Изменение E1 не меняет frozen E2, withdrawal блокирует E2.

## Promotion и очистка

Candidate selection сохраняется как exact unit-to-candidate mapping в decision. Promotion повторно проверяет manifest, activation, dependencies, права и OCC; публикует выбранные media + `RenderResultV1`, затем атомарно коммитит metadata/selection receipt/binding/result/next activation. Candidate ID сохраняется как provenance, не downstream input.

Обычная генерация и техническая валидность не approval. Final montage service может импортировать финальный asset до final review; сам film ещё не human-approved. Memory publication имеет отдельный gate.

GC удаляет только unreferenced eligible bytes без live pins, после выбранной retention задержки и с сериализацией против publication/promotion finalization. Нужен обход всех retained artifact/context/chunk/source ссылок, а не только current bindings. Физическую дедупликацию между проектами пока не вводить: совпадающий hash не объединяет права. Удаление одного chunk не удаляет общий asset другого сохранённого результата.

- #todo Проверить crash на каждой file/DB границе, concurrent same destination с разными bytes и replay без rebinding.
- #todo С renderer проверить partial group, selection другого job, duplicate callback, ambiguous submission и late result после cancel.
- #todo Проверить очистку orphan при живом pin и purge одного chunk при retained shared media; сроки не назначены, см. [эксплуатацию](operations-security.md).

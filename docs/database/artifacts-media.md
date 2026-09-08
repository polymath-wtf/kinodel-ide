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

1. Подготовленная операция фиксирует intended objects/pins, exact inputs и expected bindings до внешнего эффекта.
2. Валидированные байты stage/sync/publish без overwrite. Существующий destination допустим только при совпадении digest.
3. Одна DB transaction проверяет fence/cancel/activation/closure/OCC и фиксирует metadata, assets, provenance, binding, result и next activation.
4. Только committed metadata делает объект видимым читателям. Crash между publication и commit оставляет orphan, не половину принятого artifact.
5. Replay committed operation возвращает recorded result; missing/corrupt committed bytes означает integrity block, не новую генерацию под старым ID.

Filesystem и DB не имеют общей атомарной транзакции. Rename сам по себе не доказывает power-loss durability на любой ОС. [Storage contract](../backend/artifacts.md#managed-project-storage) требует испытать file sync, no-overwrite и directory durability на фактическом носителе.

#question Q8: до start transaction обычной execution operation ещё нет, а исходные bytes уже публикуются. Рекомендуем долговечное start reservation по project/client key с payload digest и intended object pin, финализируемое той же start transaction. Это недостающая конкретизация общего pin-протокола; не добавлять незаписанную «достаточно свежую» папку как замену. Согласовать поля/abandonment до миграции.

## Promotion и очистка

Candidate selection сохраняется как exact unit-to-candidate mapping в decision. Promotion повторно проверяет manifest, activation, dependencies, права и OCC; публикует выбранные media + `RenderResultV1`, затем атомарно коммитит metadata/selection receipt/binding/result/next activation. Candidate ID сохраняется как provenance, не downstream input.

Обычная генерация и техническая валидность не approval. Final montage service может импортировать финальный asset до final review; сам film ещё не human-approved. Memory publication имеет отдельный gate.

GC удаляет только unreferenced eligible bytes без live pins, после выбранной retention задержки и с сериализацией против publication/promotion finalization. Нужен обход всех retained artifact/context/chunk/source ссылок, а не только current bindings. Физическую дедупликацию между проектами пока не вводить: совпадающий hash не объединяет права. Удаление одного chunk не удаляет общий asset другого сохранённого результата.

- #todo Проверить crash на каждой file/DB границе, concurrent same destination с разными bytes и replay без rebinding.
- #todo С renderer проверить partial group, selection другого job, duplicate callback, ambiguous submission и late result после cancel.
- #todo Проверить очистку orphan при живом pin и purge одного chunk при retained shared media; сроки не назначены, см. [эксплуатацию](operations-security.md).

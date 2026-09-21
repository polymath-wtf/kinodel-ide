# Артефакты и медиа

**Прикладные результаты храним отдельно от состояния графа.** [Artifact contract](../backend/artifacts.md) владеет refs, commit, approval и dependency semantics; здесь размещение и правила данных.

## Размещение Записей

| Project DB | Назначение |
|---|---|
| `artifacts`, `execution_bindings` | Metadata/provenance immutable revisions и текущие slot bindings |
| `assets` | Metadata managed media, измеренные properties и access owner |
| `jobs`, attempts, group/wait, candidates/manifest | Provider work, frozen inputs, lineage и результаты до выбора автором |

Физические group/attempt/candidate records уточняются вместе с renderer. Их поля принадлежат [DTO](../backend/dto.md#cinematic-extension), lineage и reuse — [cinematic](../pipelines/cinematic.md#anchor-regeneration).

Не превращаем каждый shot/frame/beat в таблицу: порядок и ключи остаются в typed plans/results. Для очистки/reverse lookup допустимы дочерние relation rows при metadata, если нужны реальные выборки; FK/columns уточняются с миграцией. JSON ref сам по себе не FK. Семантика dependencies и freshness принадлежит [invalidation](../backend/artifacts.md#invalidation); отдельная graph DB не нужна.

## Managed Storage

[Canonical layout](../backend/artifacts.md#managed-project-storage): project-scoped `artifacts/`, `assets/`, `attempts/`, `runtime-audit/` под backend-managed root. Путь генерирует backend; имя проекта, chat и абсолютный путь установки не определяют identity. Hosted storage сохраняет те же exact-ref/visibility правила.

Автор открывает проект по имени и видит текущие результаты/версии из БД. Экспорт с понятными именами и manifest — производный снимок, не второй writable original. Изменённый экспорт импортируется как новый source/candidate, не перезаписывает approved bytes. Preview/index можно пересобрать; архив не назначает права и не запускает worker.

Запись выполняется по [commit protocol](../backend/artifacts.md#commit-protocol) и [managed publication](../backend/artifacts.md#managed-project-storage); для первых двух входных тел — [start pins](../backend/dto.md#commits-and-start-pins). Файлы, application DB и checkpointer не имеют общей атомарной транзакции; проверки crash durability принадлежат [Local MVP](../roadmap-mvp.md#acceptance).

## Promotion И Очистка

Сохранение выбранных media следует [promotion protocol](../backend/artifacts.md#candidates-and-promotion); final asset — контракту [Montage](../agents/montage.md). Существование файла не меняет статус approval или memory publication.

GC удаляет только eligible unreferenced bytes без live pins, с сериализацией против publication/promotion. Учитываются все retained revisions, contexts, chunks, source refs и будущие child executions, не только current bindings. Rejected attempts остаются историей по retention. Пока pin/GC races не испытаны, автоматическую orphan cleanup не включаем. Межпроектную физическую дедупликацию не вводим: одинаковый hash не объединяет права.

Перемещение root требует остановки writers/GC и проверки полной копии без смены IDs. Перенос незавершённой работы включает DB + checkpoints + files + совместимые версии; экспорт фильма этого не делает. Формат/UI переноса остаются будущими; [backup protocol](operations-security.md#backup-и-restore) задаёт границы. Проверки crash, lineage, stale selections, cancel и imports — [Local MVP](../roadmap-mvp.md#acceptance).

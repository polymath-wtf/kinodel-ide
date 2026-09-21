# Артефакты и медиа

**Прикладные результаты храним отдельно от состояния графа.** [Artifact contract](../backend/artifacts.md) владеет refs, commit, approval и dependency semantics; здесь размещение и правила данных.

## Идентичность И Связи

| Запись | Что сохраняет | Ограничение |
|---|---|---|
| `artifacts` | Immutable revision: schema/version, digest, URI, project/execution/stage/operation и provenance | Artifact ID означает одну версию, не перезаписываемый документ |
| `execution_bindings` | Current exact artifact по execution/slot и optimistic revision | Замена создаёт новый artifact, не меняет старое тело |
| `assets` | Managed URI/digest, MIME и измеренные properties selected/imported файла, access owner | URL не identity; наличие asset не универсальное approval |
| `jobs` и attempts | Prepared request/profile/workflow/seeds, provider identity/status, correlation и restricted audit | Intent записан до submit; неизвестный исход сверяется |
| Group/wait | Stage/activation, immutable wait identity/request digest, required units, terminal receipt | Mutable provider status не identity ожидания |
| Candidates и manifest | Exact unit/candidate/job refs, digests, technical data и parent/input lineage | Complete ordered review subject; не current creative binding |

Физические group/attempt/candidate records уточняются вместе с renderer, не как универсальный новый artifact. Кандидат может питать зависимый render unit до approval только по exact frozen lineage: sheet от лица A нельзя утвердить с лицом B. Частичная группа не полный результат; unchanged candidates при anchor repair сохраняют исходную lineage. [Cinematic](../pipelines/cinematic.md#anchor-regeneration) владеет этим правилом.

Не превращаем каждый shot/frame/beat в таблицу: порядок и ключи остаются в typed plans/results. Downstream выбирает `{render_result_ref, unit_key}` из точного утверждённого набора, а не из candidate directory. Plans валидируются, но не получают отдельное approval от утверждения media.

## Dependencies И Provenance

Commit сохраняет exact source refs/digests, источник операции, capability/resource/projection versions и выбранные assets. `current_execution` проверяет slot/binding и всю транзитивную freshness closure; `pinned_revision` сохраняет исторический источник при обычном supersede/archive. Withdrawal, отсутствие прав или bytes блокирует оба пути.

Зависимости не имеют циклов. Для очистки/reverse lookup допустимы дочерние relation rows при metadata, если нужны реальные выборки; формат FK/columns уточняется с миграцией. Строка внутри JSON сама по себе не FK. Отдельная graph DB не нужна.

## Managed Storage

[Canonical layout](../backend/artifacts.md#managed-project-storage): project-scoped `artifacts/`, `assets/`, `attempts/`, `runtime-audit/` под backend-managed root. Путь генерирует backend; имя проекта, chat и абсолютный путь установки не определяют identity. Hosted storage сохраняет те же exact-ref/visibility правила.

Автор открывает проект по имени и видит текущие результаты/версии из БД. Экспорт с понятными именами и manifest — производный снимок, не второй writable original. Изменённый экспорт импортируется как новый source/candidate, не перезаписывает approved bytes. Preview/index можно пересобрать; архив не назначает права и не запускает worker.

### Запись Байтов

1. До effect сохранить prepared operation и pins intended objects. Для start до существования обычной operation требуется эквивалентная защита обоих входных тел; минимальное предложение — durable start reservation по project/client key и digest. Поля/abandonment определить в storage implementation.
2. Валидировать, stage/sync и опубликовать без overwrite. Existing destination допустим только с тем же digest.
3. Одной DB transaction проверить activation/fence/cancel/closure/OCC и записать metadata, assets, provenance, binding, result и next activation.
4. Читатели видят только committed metadata. Crash до commit оставляет orphan; retry committed operation возвращает прежний result без rebinding или повторной генерации.

Файлы, application DB и checkpointer **не имеют общей атомарной транзакции**. Rename не доказывает power-loss durability: нужны испытания фактической file/directory sync и no-overwrite семантики. Missing/corrupt committed bytes блокируют работу, а не пересоздаются под старым ID.

## Promotion И Очистка

Для media promotion означает сохранение утверждённого выбора: exact unit-to-candidate decision → проверка полного совместимого manifest → publish выбранных bytes и `RenderResultV1` → atomic DB commit selection receipt/binding/result/transition. Это операция применения решения, не дополнительная творческая стадия.

MVP montage создаёт final asset из утверждённых видеошотов. Финал технически проверен, но не помечается human-approved: отдельного final gate нет. Memory publication — будущий отдельный review, не побочный эффект завершения фильма.

GC удаляет только eligible unreferenced bytes без live pins, с сериализацией против publication/promotion. Учитываются все retained revisions, contexts, chunks, source refs и будущие child executions, не только current bindings. Rejected attempts остаются историей по retention. Пока pin/GC races не испытаны, автоматическую orphan cleanup не включаем. Межпроектную физическую дедупликацию не вводим: одинаковый hash не объединяет права.

Перемещение root требует остановки writers/GC и проверки полной копии без смены IDs. Перенос незавершённой работы включает DB + checkpoints + files + совместимые версии; экспорт фильма этого не делает. Формат/UI переноса остаются будущими; [backup protocol](operations-security.md#backup-и-restore) задаёт границы. Проверки crash, lineage, stale selections, cancel и imports — [Local MVP](../roadmap-mvp.md#acceptance).

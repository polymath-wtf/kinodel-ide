# Fork

Статус: **после MVP; продуктовый контракт, не реализованная функция**.

Fork позволяет попробовать другое продолжение с выбранного этапа, сохранив исходный вариант. Дерево образуют executions одного проекта; схема pipeline от этого не меняется.

```text
Run A: Brief → Story → Anchors → Storyboard → Frames → Filmmaker → Videos → Final A
                            └─ Fork B: Storyboard → Frames → Filmmaker → Videos → Final B
                                                       └─ Fork C: Filmmaker → Videos → Final C
```

## Минимальный контракт

1. Пользователь выбирает существующий execution и этап, который хочет попробовать иначе.
2. Kinodel создаёт новый child execution в том же проекте.
3. Child переиспользует точные утверждённые результаты до выбранного этапа. Submitted Brief и поддерживающие планы сохраняются как точные валидированные входы: дополнительных approvals для них не появляется.
4. Результат выбранного этапа и все последующие результаты создаются заново по маршруту pipeline. Старые outputs этих этапов не становятся outputs child.
5. Parent не меняется и существует независимо; завершать или отменять его ради fork не требуется. Достаточно доступных зафиксированных входов выбранного этапа.
6. Новые результаты проходят предусмотренные pipeline HITL-gates. Старые approvals не утверждают новые outputs; дополнительных gates, включая final HITL, Fork не добавляет.
7. Fork можно создать от другого fork: executions образуют дерево.
8. Merge веток, выбор отдельных шотов из разных веток и автоматическое сравнение не входят в первую версию.

## Фундамент

При реализации child сохраняет `parent_execution_id`, `fork_stage_id` и exact artifact refs переиспользованных входов через execution bindings. Отдельные `fork_id`, `fork_receipt`, таблица веток и копии медиа не нужны.

Immutable artifacts, digests, provenance и approvals сохраняют происхождение входов. Child фиксирует согласованный снимок зависимостей, а не следует за будущими bindings родителя. Доступность, права и совместимость входов проверяются по общим правилам хранения; ссылки child учитываются при очистке.

Child получает собственный execution/thread и идемпотентный start; checkpoints, interrupts и активные jobs родителя не копируются. Это новое производство, не rewind старого запуска.

В MVP достаточно существующих границ хранения и исполнения. Поля lineage, entry routes, API и дерево в UI добавляются вместе с Fork, без предварительного scaffolding. Обычный старт MVP начинается с Brief; `revise` на текущем HITL остаётся правкой внутри того же execution.

[HITL](hilp.md) · [Artifacts](../backend/artifacts.md) · [Pipeline](../backend/pipeline.md)

Топовая оффициальная документация https://docs.langchain.com/oss/python/langgraph/use-time-travel
# Внешний orchestration: только условный fallback

**Статус:** отложенная альтернатива, **не часть базовой реализации**. Hermes-native first; установка LangGraph и перенос backend Kinodel этим пакетом не разрешены.

## Когда можно вернуться к вопросу

Только если [installed audit](hermes-questions.md) выявил **конкретный воспроизводимый сбой обязательного MVP-поведения**, который нельзя устранить native tasks/claims/runs и тонкой plugin validation/action boundary.

Возможный критерий: после restart штатный stage lifecycle не позволяет безопасно восстановить exact approved-input handoff, а supported plugin mechanisms не позволяют добавить недостающую reservation/проверку. Это гипотетический пример, не установленный недостаток Hermes.

Не являются основанием сами по себе: нодовый UI, human review, отсутствие удобной доски/полных SDK docs, несовершенный `/goal`, недолговечный transient child или необходимость narrow metadata storage. Auth contradiction требует исправления/проверки control surface, а не добавления orchestration framework. Media crash ambiguity без provider reconciliation тоже не исчезнет от смены framework.

## Что принести автору до выбора

1. Exact installed version, source `path:line` и минимальный failing scenario обязательного поведения.
2. Какие штатные surfaces проверены, почему typed function/task/узкая persistence не закрывают gap.
3. Самую маленькую native альтернативу и её ограничение; затем стоимость внешнего решения: новые зависимости, storage, deployment и интеграционные риски.
4. Кто единолично владеет progression/dispatch, как не получить два независимых владельца одной production stage.
5. Один bounded эксперимент и критерии приёмки; **отдельное согласование автора до реализации**.

Если внешний orchestration всё-таки выбран, это новый план, не инструкция «скопировать весь текущий Kinodel». Сохраняются [контракты артефактов и операций](hermes-artifact.md): exact inputs, approvals, immutable originals, convergent commands и blocked reconciliation. Framework сам по себе не доказывает approval конкретной ревизии, provider exactly-once или отмену уже принятого заказа.

## Основания

- Native tasks/dispatcher/runs документированы в [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):131–138, 1344–1354; проверка установки ещё необходима.
- Ограничение running child recovery — [delegation.md](../hermes-docs/backend/delegation.md):557–564, не доказательство недостаточности Kanban.
- HTTP run dedup — [api-server.md](../hermes-docs/backend/api-server.md):448–461; не переносить его ограниченные гарантии на media tools или другие delivery keys.

Текущий план: [native composition](hermes-kinodel-architecture.md), [полный cinematic MVP](hermes-mvp.md). Здесь намеренно нет второго runtime-дизайна и framework API recipes до доказанной необходимости.

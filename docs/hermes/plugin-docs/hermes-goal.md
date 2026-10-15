# `/goal`: необязательная итерация внутри этапа

**Статус:** ограничение использования в Kinodel. Наличие/семантика команд и plugin access проверяются в установленном Hermes; этот файл не инструкция запуска полного производства.

## Что документировано в снимке

- Kanban worker по умолчанию выполняет одну попытку карточки. `--goal` / `goal_mode=True` включают judge loop по title/body в **той же worker session**, с ограниченным turn budget; недостижимая цель или исчерпание бюджета блокируют карточку.
- Goal-mode Kanban и `/goal` в чате используют общий engine, но **не общее состояние**. Chat goal не создаёт/claim/move task; `/goal status` не показывает loop карточки.
- Judge verdict не творческое human approval. При ошибке judge lifecycle handoff допускается с warning, поэтому judge не является надёжной validation boundary.

Источник: [kanban-big-context.md](../hermes-docs/kanban/kanban-big-context.md):718–735. Это documented snapshot, не runtime evidence целевой версии.

## Правило Kinodel

В выбранном MVP используется обычное ограниченное Kanban-задание; `/goal` и judge loops отключены. Возможность stage-local итерации оставлена только для отдельного будущего решения после измеренной необходимости. Этот справочник не разрешает worker самостоятельно включать её.

В задании фиксируются: один владелец/этап, exact inputs/context, один полный typed output contract, turn/cost budget, разрешённые tools и условия остановки. Schema/domain validation и publication делает plugin независимо от judge. После результата specialist не выбирает следующий этап, не утверждает медиа и не отправляет новые paid renders через скрытый loop.

Иллюстративная постановка, **не готовый API вызов**:

```text
Этап: Storytell. Используй переданный immutable brief и bounded character context.
Верни полный Story с выданными shot keys/order, hook, narrative, before/action/after
и generated cast. Не меняй brief, не вызывай render, не создавай downstream tasks.
При смысловом конфликте переданных inputs верни question с вопросом автору.
Отсутствие обязательного input блокирует запуск на backend; out-of-scope объясни.
Работай только в заранее согласованном бюджете, затем остановись для exact review.
```

Не задавать «сделай весь фильм, пока не получится»: это смешивает routing, стоимость и human gates. Technical retry, regenerate и Continue используют сохранённые операции/разрешения, а не новый неограниченный goal.

## Чего не гарантирует goal

Durable recovery running child, однократный provider submit, полную корректность JSON, сохранность originals и approval artifact revision. Running child после process restart становится unknown ([delegation.md](../hermes-docs/backend/delegation.md):557–564); public child API хранит metadata/results in-process ([subagent-lifecycle-api.md](../hermes-docs/backend/subagent-lifecycle-api.md):51–55). Эти ограничения не устраняются хорошим текстом цели.

Выбор lifecycle и проверка действий — [архитектура](hermes-kinodel-architecture.md); версии/reviews — [артефакты](hermes-artifact.md). `/goal` остаётся справочной возможностью вне обязательного MVP. Ближайшие работы — [roadmap](hermes-kinodel-roadmap.md); к целевой установке обращаемся с [вопросами реализации](hermes-questions.md) после продуктового препродакшна.

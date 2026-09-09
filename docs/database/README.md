# Архитектура данных Kinodel

Обновлено: 9 сентября 2026 года. Статус: **принятые архитектурные решения и логический план сущностей**. SQL, миграции, backend и развёртывание здесь не реализованы; гарантии ещё требуют испытаний.

## Статусы и границы

- **Контракт:** уже принятое правило из профильных документов. Этот раздел описывает его хранение, не назначает новые маршруты графа.
- **Рекомендация:** конкретная предлагаемая модель данных. Её имена и поля ещё не утверждённые SQL-контракты.
- **#question:** необходимое решение или неполный стык; идентификатор Q ведёт в [единый реестр](open-questions.md).
- **#todo:** отложенная реализация или проверка. Наличие описания не означает её выполнения.

Принято 9 сентября: [SQLite local / PostgreSQL server](local-vs-hosted.md). Windows и Linux local-first без аккаунта, одна application и один active graph runner на data directory; macOS не сейчас. Сервер допускает multi-worker concurrency с одним writer на execution. Supabase email/password, login как mutable display label без обязательной уникальности; auth UUID profile, без custom password table. GCS только для private hosted endpoint outputs с 365-day lifecycle, не local-direct ComfyUI. Общая модель не требует transparent compatibility abstraction.

Одна логическая модель имеет разные размещения. Регистрация локального пользователя не загружает чаты или проекты; browser hosted хранит их на сервере. Endpoint хранит входы/выходы и audit своего заказа, не весь фильм клиента. Это подтверждённая граница данных, не обещание готового installer или local/cloud sync.

## Карта раздела

| Страница | Какие решения о хранении содержит |
|---|---|
| [Локально и на сервере](local-vs-hosted.md) | Принятые SQLite local / PostgreSQL server, runtime boundaries и перечень логических planned tables |
| [Аудит и решения](audit-and-decisions.md) | Замечания по важности, минимальная общая модель, что исправлено и что требует выбора |
| [Проекты, личность, чаты](projects-identity-chat.md) | Владение проектом, связь разговоров и запусков, открытие старого фильма |
| [Исполнение и согласования](execution-reviews.md) | Существующие таблицы, ключи, транзакции команд, операции, checkpoint и отмена |
| [Артефакты и медиа](artifacts-media.md) | Неизменяемые байты, зависимости, выбранные результаты, кандидаты и очистка |
| [Знания и wiki](knowledge-wiki.md) | Исходники, Markdown-версии, происхождение утверждений, публикация chunks |
| [Поиск и контекст](retrieval-context.md) | Замороженный выбор операции, проекции, производный индекс и права |
| [Подключения и кредиты](credits-billing.md) | Бесплатный local/BYOK, MVP placeholder credits/signup 100 и резервы; product daily limits и final retention #todo финального релиза, реальные платежи #future |
| [Эксплуатация и безопасность](operations-security.md) | Доступ, миграции, резервирование, удаление и восстановление |
| [Открытые решения](open-questions.md) | Вопросы с последствиями и критериями закрытия |
| [Покрытие источников](source-coverage.md) | Все просмотренные файлы `docs`, их статус и реальные расхождения |
| [Установка и lock](../backend/local-startup.md) | Автоматический venv bootstrap, версии SQLite, OS ownership и crash/shutdown gate |
| [Физические DTO](../backend/physical-dtos.md) | Конкретные foundation bodies, trusted refs, review/commit и endpoint wire proposal |
| [Rework](../backend/rework.md) | Exact prefix receipts, новый thread и безопасные authored entry routes |

## Один владелец факта

| Факт | Источник истины | Не является заменой |
|---|---|---|
| Кто вошёл | Выбранная система аутентификации | Клиентский `user_id`, имя профиля |
| Кому доступен проект и что разрешено | Project DB и серверная политика | Путь папки, чат, сам факт знания ID |
| Запуск, принятое решение, работа, отмена, окончательный исход | Project DB | HTTP-ответ, event stream, текст агента |
| Позиция графа, pending tasks и resume values | Checkpointer | Самодельный `stage_status` как второй граф |
| Точная версия творческого результата | Immutable JSON в managed storage + метаданные Project DB | Перезаписываемый `story.json`, копия тела в checkpoint |
| Текущий результат этапа | `execution_bindings` | Последний файл в папке |
| Утверждение результата | Точное решение и apply/promotion receipt | Наличие файла, успешная валидация |
| Повторно используемая память | Типизированный artifact + `chunk_bindings` после memory review | Пересказ чата, embedding |
| Знание wiki | Утверждённая Markdown-ревизия с источниками; предлагаемая модель реестра | Неутверждённая рабочая копия |
| Выбор контекста | Подготовленная `operations` с `ContextSelectionV1` | Новый поиск при retry |
| История разговора | Прикладная БД: SQLite local / PostgreSQL hosted; форма immutable events ещё предлагается | UI-пересказ, checkpoint или производственное состояние |
| Кредиты и расчёты | Серверный транзакционный журнал MVP, ещё не реализован | Баланс в браузере, себестоимость provider как пользовательский тариф |

Логические хранилища не требуют отдельных серверов: server Project DB и LangGraph могут делить PostgreSQL с раздельными схемами и владельцами миграций. Local использует SQLite с отдельно управляемыми application/saver tables или files. Managed storage содержит JSON, медиа, исходники и Markdown-снимки. Индекс перестраивается и не является ещё одним каноническим хранилищем. Обе checkpointer integration остаются #todo.

## Связи первого среза

```text
projects 1 -> N executions N -> 1 pipeline_snapshots
executions 1 -> N operations / review_requests / execution_work / execution_controls
executions 1 -> N execution_bindings -> artifacts -> immutable JSON bytes
operations -> exact prepared inputs/context -> committed results + next activation
review_requests -> exact subject + decision -> apply operation -> resume segment
execution_id = thread_id -> separately owned LangGraph checkpoints
```

Для первого текстового выпуска достаточно этих связей, проверки доступа и прямого контекста. Полный [целевой перечень таблиц](../backend/implementation.md#project-db-tables) не означает миграцию jobs, assets, chunks, chat, wiki, billing и outbox заранее. Регистры графов, capabilities, profiles и ресурсов сначала версионируются в deployment-коде, не превращаются в динамический marketplace БД.

## Порядок согласования

1. Подтвердить среду, доступ, сохранность и допустимые расходы: Q1-Q6.
2. Закрыть точные foundation-стыки и формы: Q7-Q9; предметные DTO остаются у backend/agents.
3. Включать rendering, chat, библиотеку и MVP credits по их функциям, не ради ER-диаграммы. Автоматические backups/RPO/RTO и реальные платежи/подписки #future production; полный ручной перенос остаётся Q20. Rework через новую execution из exact prefix принят; Q21 проверяет предложенные DTO/entry routes.
4. #todo Превратить критерии соответствующего этапа в runnable checks и выполнить их на выбранной среде до объявления готовности.

Отдельная база пользователей, graph DB, универсальный revision engine, постоянные context-pack artifacts и синхронизация двух рабочих баз не нужны. Новый чат не перезапускает фильм; новая творческая задача создаёт новый execution с точными разрешёнными источниками.

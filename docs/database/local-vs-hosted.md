# Локальная установка и сервер

Дата: 9 сентября 2026 года. **Принято: SQLite local / PostgreSQL server.** Локально одна application и один active graph runner на data directory; сервер поддерживает конкурентных workers при одном writer на execution. Реализация и испытания обоих профилей остаются #todo; это не два готовых взаимозаменяемых backend.

## Подтверждённые требования

| Сценарий | Владелец данных | Граница аккаунта и сети |
|---|---|---|
| Локальная установка из GitHub | Локальная Project DB, checkpoints, сообщения, wiki и managed files | Первый запуск без аккаунта Kinodel и отдельного сложного обслуживания БД. Цель установки: clone, установка Python dependencies, запуск/кнопка; это ещё не работающая команда |
| Локальный пользователь с аккаунтом Kinodel | Проект и разговоры остаются локальными | Supabase email/password даёт сервисный доступ и MVP credits/signup 100; login есть display label. Не включает загрузку чатов, wiki или синхронизацию проекта |
| Браузерное hosted-приложение | Серверная Project DB, история сообщений и files/object storage | Аккаунт и авторизация серверных данных обязательны; браузерный cache не единственная копия проекта |
| Заказ Kinodel render endpoint | Сервис хранит заказ, workflow, переданные inputs, outputs и restricted job audit | Только payload заказа, не весь локальный проект. Возвращённый результат становится candidate у владельца проекта; не автоматическим approval |

Бесплатное приложение не означает, что облачная модель или GPU доступны бесплатно. Без аккаунта Kinodel работают локальные возможности и прямой BYOK; для внешнего provider может требоваться его собственный аккаунт. Бесплатный LLM proxy зависит от доступности/upstream limits и technical safety, без product daily limits MVP. #todo финального релиза: 5M input + 1M output/account/day, reset midnight Europe/Chisinau с DST. Local direct ComfyUI импортирует разрешённый file или `/view` без hosted order auth/bucket; remote signed download проверяется и сохраняется у владельца проекта, browser-hosted file остаётся на сервере. Подробности: [подключения и privacy](credits-billing.md#текстовый-proxy-и-конфиденциальность).

## Почему SQL и почему SQLite

История разговоров, список проектов, уникальная отправка команды, точное согласование и атомарная запись результата с переходом являются реальными потребностями. SQL здесь проще самодельных связанных JSON-журналов: транзакции, уникальные ключи и выборки уже есть. История сообщений не требует PostgreSQL, vector DB или общего event-sourcing framework.

**Принято:** SQLite + локальные файлы для single-user установки; PostgreSQL для hosted-приложения и сервисного учёта. SQL нужен для связей проектов/сообщений/запусков, уникальности команд, OCC и атомарных решений/результатов, а не ради vector search. SQLite не требует отдельно обслуживаемого DB server; PostgreSQL выбран для конкурентных серверных workers. Общая логическая схема не означает общий DDL или прозрачную подмену драйвера.

| Проверенный текущий стык | Цена локального SQLite профиля |
|---|---|
| [Runtime](../backend/runtime.md#single-writer-ownership): session advisory lock и saver на той же PostgreSQL connection | Local: один application process, один active graph runner и OS-held exclusive ownership локального data root на весь срок работы, включая saver tasks; второй процесс отказывает в старте, живого владельца не вытесняет TTL |
| Короткие execution-row locks для API decisions/cancel и commits | В SQLite короткие сериализованные write transactions с OCC, проверкой cancel/fence и bounded busy handling. Не удерживать DB write lock на время HTTP/LLM. Процессный ownership не заменяет транзакции |
| Durable claim selection | `SKIP LOCKED` не найден как текущий SQL-контракт в docs: SQL ещё нет. Если его выберут для PostgreSQL multi-worker, локальная очередь одного runner не должна его эмулировать |
| `AsyncPostgresSaver`, pending writes, exact interrupt classifier | Отдельный `langgraph-checkpoint-sqlite` / `AsyncSqliteSaver`; одинаковый saver interface не доказывает Kinodel recovery. Нужны pinned versions и реальные checkpoint tuples |
| Схемы, типы, FK, JSON, partial uniqueness, миграции | Проверить SQL обоих профилей отдельно; SQLite FK enforcement на каждом соединении, типизацию/JSON validation и ограничения. Не обещать перенос PostgreSQL DDL без изменений |
| DB + files publication и backup | Сохраняется двухшаговый commit. Backup включает Project DB, saver DB, если отдельная, и файлы. Нельзя копировать только live `.db`, игнорируя WAL/pending writes |

Это принятый минимальный ownership contract, не готовый SQLite adapter. Локальный API живёт в том же application process, что background runner, не вызывая граф из HTTP handler. Один active runner не блокирует интерфейс на весь model call. DB error прекращает effects; restart сначала получает ownership, затем сверяет durable work/checkpoints. Network share не поддерживается. [Запуск](../backend/local-startup.md): Windows `.bat` и Linux shell используют общий Python core, разные OS locks/dependencies; macOS не сейчас. Venv, version-gated SQLite и busy/shutdown protocol предложены; версии/архитектуры и испытания Q1, launcher не реализован.

Не нужны универсальный DB compatibility layer, собственный saver или синхронизация двух Project DB без доказанной необходимости. Общими остаются domain validation, exact refs и критерии исходов; transaction/ownership и saver setup реализуются отдельно для принятых профилей. Перенос live PostgreSQL БД в SQLite не входит в решение. Полный backup переносит совместимую установку того же профиля, не конвертирует engines.

## Реальный перечень таблиц

Источник имён: [implementation](../backend/implementation.md#project-db-tables), не существующая SQL schema.

| Когда | Имена из плана | Зачем |
|---|---|---|
| Текстовый foundation | `projects`, `pipeline_snapshots`, `executions` | Проект, версия маршрута, отдельные производственные попытки |
| Текстовый foundation | `artifacts`, `execution_bindings`, `operations` | Версии результатов, текущий выбор, подготовленный вход и сохранённый исход работы |
| Текстовый foundation | `review_requests`, `execution_work`, `execution_controls` | Решения человека, долговечная работа и отмена |
| С рендером | `assets`, `jobs` | Выбранные файлы и внешние задания; физические group/candidate records ещё Q13 |
| С памятью | `chunk_bindings` | Активная утверждённая память |
| Позднее streaming | `event_outbox` | Доставка UI событий, не очередь производства |

Итого в плане 13 логических Project DB tables, из них 9 относятся к текстовому foundation, для SQLite local / PostgreSQL server при включении соответствующей функции. Физическая схема ещё не реализована. Checkpointer имеет отдельное migration ownership; обе интеграции #todo. Хранение chat принято, но имена/форма chat events/attachments ещё Q10, не утверждённые дополнительные SQL tables. Wiki registry, connections и billing остаются логическими сущностями будущих функций. База пользователей отдельно на каждый проект не нужна.

## Перенос и приёмка

**Подтверждено:** полный ручной перенос остановленной установки включает DB + checkpoints + files и совместимые версии, проверку refs/digests и remote-order reconciliation до effects. Автоматическая backup-система, RPO/RTO и disk-loss restore отложены до production (#future); это не MVP blocker. Без копии потеря диска может уничтожить работу. Hosted-проект остаётся на сервере; регистрация ничего не переносит. Per-project live import и local/cloud sync не включены. Подробности: [backup](operations-security.md#backup-и-restore), Q5/Q20.

- #question Q1: версии/архитектуры Windows/Linux, installer и проверенный local ownership/shutdown mechanism. ОС, движки и один local active runner приняты; macOS не текущая цель.
- #todo На чистой машине без PostgreSQL и аккаунта Kinodel проверить установку, открытие локального проекта и persistence; зависимости модели/GPU проверять отдельно от запуска UI.
- #todo Для SQLite проверить второй процесс, process death, DB busy/error, pending writes, cancel/commit race, stale decision, replay после business commit без повторной генерации и restore на другой машине. PostgreSQL проходит собственные session-loss/takeover tests; результаты одного профиля не заменяют другой.

## Проверенные источники

Сверка 9 сентября 2026 года, не запуск API или DB integration:

- [SQLite: appropriate uses](https://www.sqlite.org/whentouse.html): application-local storage без DB administration, один writer на файл, ограничения network filesystem.
- [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers): отдельные SQLite/Postgres пакеты, async savers, pending writes и synchronous durability. SQLite указан для local workflows; это не сертификат restart safety нашего runtime.
- [LangGraph time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel): replay повторяет последующие nodes/effects и не является переносом Project DB approvals. Предложение rework находится в [артефактах](artifacts-media.md#возврат-к-раннему-этапу).

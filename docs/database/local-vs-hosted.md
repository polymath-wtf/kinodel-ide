# Локальная установка и сервер

**Принято: SQLite local / PostgreSQL hosted.** Рекомендуем отдельные application/saver SQLite-файлы в одном managed data root. Конкретные имена, настройки и миграции фиксируются при реализации; это не готовые взаимозаменяемые backend.

## Размещение

| Сценарий | Где оригиналы | Что уходит в сеть |
|---|---|---|
| Локальная установка Windows/Linux без аккаунта | SQLite, checkpoints, managed files; позднее личная библиотека | Только выбранные входы внешней модели/генератора при таком подключении |
| Та же установка с аккаунтом Kinodel, позднее | Проекты и разговоры остаются локальными | Сервисные запросы; регистрация не запускает upload/sync |
| Hosted-приложение, позднее | PostgreSQL, checkpoints и private server storage | Разрешённые provider payloads; browser cache не оригинал |
| Kinodel render endpoint, позднее | Собственные order records в PostgreSQL, inputs/outputs/audit в private GCS | Результат конкретного заказа, не доступ ко всему проекту клиента |

Local direct ComfyUI импортирует разрешённый файл или `/view` без hosted bucket. BYOK означает собственный ключ провайдера; локальный путь не требует аккаунта Kinodel. Hosted backend не получает доступ к ComfyUI на компьютере пользователя лишь от знания `localhost`: transport решается при включении подключения.

## Почему Эти Движки

Транзакции нужны для принятой команды, точной версии решения, выбранного результата и защиты от повторного выполнения. SQLite даёт это без установки DB-сервера. PostgreSQL нужен серверному профилю с конкурентными workers. История чата или библиотека знаний сами по себе не требуют нового движка.

| Гарантия | Local | Hosted |
|---|---|---|
| Единственный writer графа | Один application process и один active runner под OS-held data-directory lock | Один invocation на execution под session advisory lock |
| Прикладной commit | Короткая сериализованная write transaction, OCC, cancel/fence checks | Короткая transaction с соответствующими row locks и теми же проверками |
| Checkpoint writes | `AsyncSqliteSaver` под ownership приложения | `AsyncPostgresSaver` на той же lock-owning session |
| Миграции | Application и saver управляются отдельно | То же; schemas могут делить один deployment |
| Проверка | FK на каждом соединении, durability/busy/shutdown и process-death tests | Session loss, takeover, concurrent writers и saver integration |

Ни model call, ни HTTP не держат прикладную write transaction. Lease timeout не вытесняет живого владельца. Локальные network-share directories и две writable восстановленные копии не поддерживаются. Полный ownership/recovery протокол — [runtime](../backend/runtime.md#single-writer-ownership), запуск — [local startup](../backend/local-startup.md).

## Реальный Перечень Таблиц

Источник — [implementation](../backend/implementation.md#project-db-tables), не отдельный database checklist. Текстовая проверка начинает с executions/operations/results/reviews/work; пользовательский MVP добавляет media jobs, attempts/groups и assets. Обсуждение результата сохраняется в review/operation records. Library bindings, общий чат, wiki и billing добавляются с соответствующими функциями.

Не фиксируем число таблиц до физической схемы: record может быть bounded JSON либо дочерней строкой в зависимости от запроса, ограничения и собственного lifecycle. Не вводим ORM, универсальную совместимость SQL или SQLite-эмуляцию серверных locks.

## Перенос И Приёмка

Перенос незавершённой работы — согласованная копия остановленной установки: application DB, saver DB/pending writes, referenced files и совместимые версии графа/ресурсов. Это перенос того же engine profile, не конвертация PostgreSQL в SQLite. Секреты подключаются отдельно; внешние заказы сверяются до новых effects.

Экспорт выбранного фильма не переносит runtime. Регистрация не переносит данные. Автоматический backup и local/cloud sync не входят в первый билд; [backup и restore](operations-security.md#backup-и-restore) задают границы.

Факты совместимости зависимостей и обязательные испытания Windows/Linux находятся в [Local MVP](../roadmap-mvp.md). Smoke test SQLite saver не доказывает сохранность прикладных approvals/files; hosted integration проверяется отдельно.

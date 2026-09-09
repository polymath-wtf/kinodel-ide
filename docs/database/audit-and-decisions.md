# Аудит и решения по хранению

Дата: 8 сентября 2026 года. Статус: **документальная проверка и точечные исправления**, не SQL, код или испытание работающего приложения. Рекомендации не заменяют выбор пользователя. Проверенный охват отделён от предыдущего прохода в [source coverage](source-coverage.md#повторный-аудит).

## Замечания по важности

Решение 9 сентября: [SQLite local / PostgreSQL server](local-vs-hosted.md) приняты пользователем, вместе с раздельной privacy topology, compatible full backup и new-execution prefix rework. Таблица ниже сохраняет историю предыдущего аудита, не действующий PostgreSQL-only local baseline. Текущие незакрытые детали находятся в [реестре](open-questions.md); выбор engine больше не вопрос.

Автору нужно открыть фильм, продолжить работу в новом разговоре и забрать материалы с собой. Хранилище должно сохранять выбранные версии и решения, не заставляя автора восстанавливать фильм по именам файлов или платить за облачную копию локального проекта. Ниже последствия для обоих способов использования, а не объявление готовых экранов.

| Важность | Что было не так | Последствие и исправление |
|---|---|---|
| P1: граница платного заказа | [Credits, ключевые записи](credits-billing.md#ключевые-записи) требовали reserve и job intent одной транзакцией без различия локального приложения и endpoint | Две БД не могут выполнить описанную локальную транзакцию вместе. Уточнены отдельные local intent и service order, стабильный ключ повторной отправки и сверка после потери ответа. Ledger только на сервисе, promotion только у владельца проекта. Точный protocol остаётся Q16/Q18 |
| P1: сохранность при переносе | [Managed storage](artifacts-media.md#managed-storage) описывал файлы рядом, но не пользовательский смысл move/import; [backup](operations-security.md#backup-и-restore) уже требовал БД и checkpoints | Папку можно было принять за самодостаточный проект и потерять возможность продолжения. Разделены выдача результатов, смена storage root и полный restore; добавлен Q20, per-project live import не обещан |
| P2: продуктовая топология | [Размещение](operations-security.md#размещение-без-второго-владельца) сводило local к dev/production, не отделяя SaaS compute от hosted app | Могло породить обязательную cloud Project DB или синхронизацию двух владельцев. Добавлены профили одной модели; endpoint хранит заказы, не весь фильм. Hosted-продукт остаётся отдельным выбором |
| P2: недостоверные открытые вопросы | Q1/Q2 повторно открывали engine/canonical storage, Q4 терял существующий design default; Q9/Q10/Q15 смешивали заданную семантику и детали реализации | Обновлены [статусы](open-questions.md#уже-отвечено-в-контрактах) с источниками. PostgreSQL не заменён SQLite, hosting/auth/retention не назначены за пользователя |
| P2: история разговора | [Chat model](projects-identity-chat.md#история-сообщения-и-экран) имела body/revision без определения оригинала, правок, partial ответов и удаления копий | Рекомендуются immutable accepted events и производный экран, exact attachment refs и ограниченная передача модели. Raw не означает token/provider dump; сроки, partial и доступ остаются Q6/Q10 |
| P2: wiki workflow | [Wiki](knowledge-wiki.md#редактирование-и-публикация) предлагала отдельный human publish для каждой правки, хотя RAG задаёт maintained Markdown с provenance, не отдельного reviewer | Предложение явно отделено от контракта; для личной wiki достаточно одного действия публикации автором. Отдельные claim/link tables и graph engine не требуются. Memory review creative chunks не отменён |
| P3: честность охвата | [Coverage](source-coverage.md) говорил о полном чтении всех docs и внешней сверке предыдущего прохода без отдельной границы повторного аудита | Добавлен реальный охват этого прохода; исторические проверки не переименованы в выполненные сейчас тесты |

P1 здесь означает риск потери работы или неправильной границы платного эффекта при реализации по тексту; P2 означает противоречие, существенную неоднозначность или лишнее усложнение; P3 означает качество документации. Это не наблюдавшиеся сбои приложения. Оснований объявлять P0 или пройденные crash tests нет.

## Одно упрощающее решение

**Место вычисления не определяет владельца проекта.** Рекомендуем один логический project/execution/artifact model в локальном и полном hosted-приложении, с разными размещениями байтов и БД. У каждого live проекта только один владелец записи. Удалённая генерация является заказом у исполнителя: он возвращает результат, а приложение автора решает, что выбрано и утверждено.

Это убирает необходимость в DB-per-user на SaaS, cloud-копии каждого локального фильма, синхронизации approvals, per-chat папках, отдельном workflow wiki и втором финансовом журнале у клиента. Общий event-sourcing framework, универсальный revision engine, graph DB и обязательные vectors не нужны. Существующие связи, immutable revisions и явные команды покрывают текущие задачи; новые abstractions не добавлены.

Принято: SQLite/files локально, PostgreSQL/storage на сервере, без transparent compatibility layer. Local: одна application и один active graph runner; server: multi-worker concurrency при одном writer на execution. Различия ownership/saver/transactions и ещё не выполненные tests перечислены в [local-first](local-vs-hosted.md).

## Что увидит автор

| Действие | Рекомендуемое поведение | Что нужно выбрать |
|---|---|---|
| Открыть старый фильм в новом чате | Тот же проект, запуски и актуальное согласование; terminal execution не оживает | Q10: scope/edit/partial; local история локальная, browser hosted история серверная |
| Исправить текст или файл | Новая версия с понятной историей; старый approved результат не переписан | Q10/Q20: editor/import UX, не прямое изменение managed originals |
| Скачать фильм и тексты | Понятные имена в outputs и оглавление точных версий; кандидаты и закрытый audit не смешаны с выбранной выдачей | Q2/Q20: состав экспорта и формат manifest |
| Перенести незавершённую работу | Подтверждён полный backup DB/checkpoints/files/versions; один writer | Q5/Q20: формат, retention, restore test; per-project live transfer не обещан |
| Вернуться к раннему этапу | Сохранить E1 и сравнивать с E2 в том же проекте из exact prefix | Решение принято; Q21 уточняет DTO/closure/entry guards, реализация #todo |
| Заказать удалённую генерацию | Передать только входы заказа; после получения импортировать candidate локально | Q16: authorization, transport, status lookup и retention сервиса |

## Термины

Artifact означает проверенную версию творческого результата; immutable означает запрет переписывания принятой версии, не вечное хранение. Execution означает один запуск производства, chat означает разговор, login session означает срок входа в приложение. Manifest/index означает оглавление, не управляющую БД. Digest означает контрольный отпечаток содержимого; OCC означает отказ перезаписать объект, если его версия уже изменилась. Provenance означает происхождение результата из точных источников; ledger означает будущий журнал финансовых операций.

## Остаток и проверки

### Журнал изменений 9 сентября

- Приняты engine/ownership profiles; нормативные architecture/runtime/implementation/state-machine/langgraph/tools и roadmap больше не требуют PostgreSQL для local. План сохраняет 13 логических Project DB entities, 9 для text foundation; chat persistence принято, физические chat tables не объявлены утверждёнными.
- Закреплены no-account local/no upload on registration, server-owned hosted history, selected endpoint payload и private object-ref/signed-URL delivery. Text proxy default без bodies, abuse/quota metadata отдельно; direct local BYOK и отсутствие универсального ZDR обещания сохранены.
- Public wiki публикует owner через GitHub releases, revisions pinned; personal wiki/RAG/taste private и explicitly selected. ACL проверяется до retrieval и повторно при hydration/citation/media; CinemaChunk/taste требуют user approval.
- Rework принят как новая execution/branch из exact prefix того же проекта; immutable E1 сравнивается с E2, без arbitrary rewind/inherited approval изменённых outputs. Current-revision conflict и persist-before-advance уточнены в canonical contracts.
- Реально открытые вопросы подняты вверх реестра; принятые ответы вынесены ниже. SQL, migrations, runtime code и отчёты dry run не изменялись; чужие dirty изменения сохранены. Обе saver integration и runtime checks остаются #todo.

Обновлённый scope: Q1/Q3 установка/доступ, Q2/Q6 storage policy и Q7-Q9 executable contracts остаются по своим функциям. Q5 backups/RPO/RTO отложен до production; Q17/Q18 теперь MVP compute credits, не text local dependency. Q19 реальные платежи/подписки #future, Q15 discovery отдельно. Q20 ручной перенос и Q21 rework проверяются перед включением этих функций.

### Исследование физических стыков (исторический срез)

Следующие абзацы сохраняют состояние до последующих решений пользователя, не текущие blockers. Сейчас Q3 закрывает credential выбор Supabase email/password, Q1 фиксирует Windows/Linux; actual-token lost-text billing принято, product daily limits и final retention #todo финального релиза. MVP credits/signup 100 сохраняются. Актуальные детали находятся в [реестре](open-questions.md).

9 сентября добавлены [local startup/lock](../backend/local-startup.md), [physical DTOs](../backend/physical-dtos.md) и [rework](../backend/rework.md). Приняты пользовательские GCS/365-day outputs, Supabase users, welcome access modes и цены MVP 1/3/5, text 1/2 per million, free 0, signup 100. Финансовая outcome policy, 15-minute URL TTL, stdlib lock реализация, canonical_json_v1 и terminal-source-only rework являются инженерными предложениями, не незаметно согласованными фактами.

Главный открытый конфликт: Supabase password API не имеет native username-only. Username без email сохранён как требование Q3, не реализован synthetic email workaround. DTO проверка разделяет candidate creativity и trusted IDs/refs/approvals; start reservation закрывает конкретную pre-execution pin дыру ценой одной предлагаемой physical table. LangGraph fork не переносит business approvals и не отменяет платные effects. SQLite saver/app DB транзакции не объявлены атомарными вместе; PostgreSQL same-session saver ещё требует реального integration proof.

Инструменты Task/subagent и TODO недоступны: экспертное делегирование и независимое ревью не выполнены, вместо них проведены собственные отдельные исследовательский и consistency проходы. Подробный реальный охват фиксируется в source coverage; runtime, provider, GCS и auth tests не запускались.

#todo Все runtime-сценарии приёмки на предметных страницах ещё предстоит реализовать и выполнить. Проверки прежнего аудита не являются результатами этой правки; текущий охват и documentary verification отделены в [source coverage](source-coverage.md#принятие-решений-9-сентября). Исторические dry runs не переписаны в успешные tests. Нормативные backend/context/RAG и конфликтующие roadmap/first-deployment формулировки теперь обновлены, а не только снабжены scope notes.

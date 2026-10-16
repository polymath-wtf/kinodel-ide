---
title: "Kinodel IDE — пакет препродакшна"
created: 2026-10-15
updated: 2026-10-16
type: concept
tags: [kinodel, preproduction, project, ai-cinema]
sources: [raw/kinodel-plugin-raw/hermes-kinodel.md, raw/kinodel-plugin-raw/hermes-mvp.md]
confidence: medium
status: preproduction
---

# Kinodel IDE — пакет препродакшна

**Рабочая документация для будущей реализации, не готовая спецификация API и не отчёт о работающем плагине.** Перепаковка исходного концепта с учётом прямого запроса пользователя от 2026-10-15. Сейчас не устанавливаем profiles, не создаём производственные задачи и не вызываем генераторы.

## Суть продукта
Kinodel превращает «user input vibe» в мини-фильм с командой узких специалистов. Автор не собирает результаты из бесконечного чата: он видит производство, сравнивает материалы, выбирает дубли и принимает решения на остановках workflow. Producer сопровождает автора в чате; Pipeline показывает маршрут; Canvas — содержимое фильма.

Плагин — фиксированный производственный шаблон, инструкции ролей, контракты материалов и React WebUI поверх Hermes Kanban. Это не новый агентный runtime, не независимая task DB и не произвольный редактор исполняемых графов.

## Как читать пакет
| Страница | Владеет темой |
|---|---|
| [[kinodel-preproduction/product-and-mvp]] | Пользовательский опыт, границы MVP и исключения |
| [[kinodel-preproduction/pipeline-and-gates]] | Последовательность, допуск этапов, остановки |
| [[kinodel-preproduction/agents-and-context]] | Роли, входы, инструкции и wiki picker |
| [[kinodel-preproduction/artifacts-and-revisions]] | Словарь данных, версии, происхождение и правки |
| [[kinodel-preproduction/backend-boundaries]] | Минимальный backend и границы Hermes/Kinodel |
| [[kinodel-preproduction/frontend-workspace]] | Pipeline, Canvas, чат, инспектор и референсы |
| [[kinodel-preproduction/render-and-montage]] | Общий render-путь, anchors, клипы и финал |
| [[kinodel-preproduction/decisions-and-questions]] | Что принято, что предложено, что ещё решить |
| [[kinodel-preproduction/implementation-readiness]] | Последовательность подготовки и будущая приёмка |
| [[kinodel-preproduction/source-map]] | Происхождение документации и отсутствующие материалы |

## Правила чтения
- **Требование** — прямое пожелание пользователя или продуктовый инвариант.
- **Решение концепта** — сохранённый выбор исходного пакета; это не проверка совместимости с Hermes.
- **Предложение** — рабочий вариант, который нельзя незаметно превратить в обязательный контракт.
- **Открытый вопрос** — решение ещё не принято или требует проверки установленного host.
- **Проверенный факт реализации** — с версией и явным уровнем доказательства: source inspection подтверждает наличие конкретного кода; выполненный runtime test подтверждает проверенный сценарий. В пакете есть source research, но приёмка работающего Kinodel не выполнялась.

Один предмет — одна основная страница. Детальные старые JSON-примеры остаются в raw как проектные эскизы, а не копируются в новые файлы под видом исполняемых schemas. Старые обзорные страницы wiki ведут сюда. Следующий разговор можно начать с любой строки реестра решений, не решая весь backend сразу.

## Текущая готовность
[[kinodel-preproduction/readiness-audit]] — аудит 2026-10-16: можно начинать ограниченные spikes и подготовку domain contracts; весь MVP ещё не implementation-ready. Там разделены структурная проверка, integration blockers, решения B01–B10 и gates text/media.

## Переход от концепта к механизмам
Актуальный механизм на 2026-10-16: [[kinodel-preproduction/hermes-mechanisms]] — domain/native ownership, lifecycle/recovery и enforcement gaps; [[kinodel-preproduction/localhost-webui]] — самостоятельный browser UI, auth и native chat; [[kinodel-preproduction/kinodel-features]] — backlog проверок и функций. Исправлен прежний уклон в Desktop SDK. Это source inspection, не runtime-приёмка. Продуктовые требования сохраняются; browser bootstrap, worker restrictions и строгий Stop ещё не доказаны интеграцией.


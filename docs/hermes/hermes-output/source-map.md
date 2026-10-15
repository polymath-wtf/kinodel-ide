---
title: "Карта источников и границы доказательств"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, decisions, project]
sources: [raw/kinodel-plugin-raw/hermes-artifact.md, raw/kinodel-plugin-raw/hermes-goal.md, raw/kinodel-plugin-raw/hermes-kinodel-agents.md, raw/kinodel-plugin-raw/hermes-kinodel-architecture.md, raw/kinodel-plugin-raw/hermes-kinodel-context.md, raw/kinodel-plugin-raw/hermes-kinodel-render.md, raw/kinodel-plugin-raw/hermes-kinodel-roadmap.md, raw/kinodel-plugin-raw/hermes-kinodel.md, raw/kinodel-plugin-raw/hermes-mvp.md, raw/kinodel-plugin-raw/hermes-nodes.md, raw/kinodel-plugin-raw/hermes-questions.md, raw/kinodel-plugin-raw/hermes-webui.md]
confidence: medium
status: preproduction
---

# Карта источников и границы доказательств

## Что изучено
Полностью прочитаны Markdown-файлы предоставленного каталога; оба PNG просмотрены визуально. Дополнительно прочитаны существующие SCHEMA/index/log и три обзорные страницы wiki. Внешние документы по старым относительным ссылкам не импортированы и не считаются прочитанными.

| Исходный файл в raw/kinodel-plugin-raw | Основная страница нового пакета |
|---|---|
| hermes-artifact.md | artifacts-and-revisions; decisions-and-questions |
| hermes-goal.md | backend-boundaries — goal loops вне MVP |
| hermes-kinodel-agents.md | agents-and-context |
| hermes-kinodel-architecture.md | backend-boundaries; pipeline-and-gates |
| hermes-kinodel-context.md | agents-and-context — picker и точные inputs |
| hermes-kinodel-render.md | render-and-montage |
| hermes-kinodel-roadmap.md | implementation-readiness |
| hermes-kinodel.md | overview; product-and-mvp |
| hermes-mvp.md | product-and-mvp; implementation-readiness |
| hermes-nodes.md | pipeline-and-gates |
| hermes-questions.md | decisions-and-questions |
| hermes-webui.md | frontend-workspace |
| pipeline reference.png | frontend-workspace — горизонтальный маршрут |
| canvas reference.png | frontend-workspace — материалы и инспектор |

Прямой пользовательский запрос от 2026-10-15 уточняет: Producer в чате, будущий контекст из собственной wiki, подготовка backend/frontend в отдельном wiki-разделе и постепенное решение вопросов. Это контекст перепаковки, не файл в raw; дословный transcript здесь не создавался.

## Недостающие материалы исходного проекта
- Полные инструкции пяти ролей из внешнего `hermes-agents/README.md` и связанных файлов.
- ComfyUI workflow JSON, registry/mappings и прежний comfyui-tool документ.
- Указанные в исходниках Hermes documentation snapshots, research и test-results.
- Старые standalone backend/context contracts и Chat reference.

Их упоминание не означает наличие в текущей установке. Старые абсолютные/относительные пути не перенесены в рабочий пакет как обещание доступных файлов. Не создаём поддельные skills/workflows, чтобы заполнить пробелы.

## Что проверено, а что нет
**Этот проход:** чтение источников и существующей wiki, визуальный разбор двух референсов, создание новой документации, проверка структуры/ссылок и неизменности raw.

**Не выполнялось:** проверка host API, capabilities моделей, permissions profiles, установка plugin, создание Kanban задач, запуск worker/render/FFmpeg, тесты frontend/backend. Поэтому данные concept-файлов о Hermes представлены как основания будущего исследования, не актуальная API-справка.

Названия tools в концепте могут быть настоящими именами, но этого недостаточно для утверждения об их доступности, scope или совместимости. Детальные JSON-примеры raw — иллюстрации. Дата страницы — дата перепаковки, не дата технической верификации интеграции.

## Сохранность
Raw остаётся неизменяемым, изображения используются по исходным ссылкам без копирования. Новая рабочая документация находится в kinodel-preproduction; старые overview-страницы ведут к ней. Wiki исключена из Git локально: clean status репозитория не означает backup этой документации.

Связи: [[kinodel-preproduction/overview]], [[kinodel-preproduction/decisions-and-questions]], [[kinodel-preproduction/implementation-readiness]].

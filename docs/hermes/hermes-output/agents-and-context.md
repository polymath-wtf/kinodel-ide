---
title: "Агенты, инструкции и контекст"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, context, workflow]
sources: [raw/kinodel-plugin-raw/hermes-kinodel-agents.md, raw/kinodel-plugin-raw/hermes-kinodel-context.md, raw/kinodel-plugin-raw/hermes-artifact.md]
confidence: medium
status: preproduction
---

# Агенты, инструкции и контекст

## Контракт команды
**Требование:** у специалиста одна зона ответственности, structured input, полный structured output и условия остановки. Нехватка данных — вопрос; техническая проблема — ошибка, не разрешение чинить код или менять provider. ^[raw/kinodel-plugin-raw/hermes-kinodel-agents.md]

| Роль | Работа | Не делает |
|---|---|---|
| Producer | Уточняет vibe, собирает Brief, объясняет результаты, адресует feedback | Не является pipeline-нодой исполнителя; не диспетчеризует специалистов и не утверждает за автора |
| Storytell | Превращает Brief в целостную историю и последовательность действий по shots | Не рендерит и не меняет утверждённые условия Brief молча |
| Wardrobe | Планирует portrait, location и character_sheet | Не переписывает Story |
| Storyboard | Планирует начальную композицию каждого shot по Story и anchors | Не переизобретает утверждённую внешность |
| Filmmaker | Планирует движение, камеру и длительность непрерывного clip | Не заменяет утверждённую начальную композицию |

Montage — техническая сборка, не шестой творческий агент. Смысловые входы всех этапов — в [[kinodel-preproduction/pipeline-and-gates]].

## Что передаётся
Producer получает полные текущие Brief и Story, когда они существуют, плюс компактное состояние производства. До первого полного Brief ответы остаются в разговоре; отдельного draft-документа нет. Полный результат другого этапа читается по запросу, обязательно перед правкой. «Текущий» — выбранный проектом, не последний созданный файл. ^[raw/kinodel-plugin-raw/hermes-kinodel-context.md]

Wardrobe, Storyboard и Filmmaker получают **полные approved Story и Brief**, а не summaries или только characters/shots. Проекции полей принадлежат той же Story revision. При rework дополнительно передаются предыдущий полный output и feedback. Transcript прежней session полезен, но не заменяет exact inputs. ^[raw/kinodel-plugin-raw/hermes-artifact.md]

## Инструкции и инструменты
Предлагаемый минимум: разрешённое чтение, `skill_view`, при необходимости `vision_analyze` и узкое действие публикации своего результата. Producer нужны сохранение Brief revision и адресация feedback. Это семантика будущих plugin-действий, не придуманные имена зарегистрированных tools.

Творческим workers не нужны terminal, изменение кода, общий `delegate_task`, произвольное создание Kanban tasks или прямые неучтённые renders. Ограничения должны обеспечиваться host/profile/plugin, а не одним текстом prompt. Механизм и scope ещё проверяются. ^[raw/kinodel-plugin-raw/hermes-kinodel-agents.md]

В инспекторе показываем подготовленные инструкции роли, их версию, назначенные skills и доступные сведения о фактической загрузке. `SKILL.md` — не автоматически весь system prompt Hermes. Подготовлено, наблюдаемо загружено и недоступно для наблюдения — разные состояния; не обещаем показ скрытых рассуждений. Полных текстов пяти role skills в переданном пакете нет: их ещё нужно предоставить или совместно написать. ^[raw/kinodel-plugin-raw/hermes-kinodel-context.md]

## Wiki picker — пользовательский контекст
Прямое требование пользователя: выбирать собственные styles, characters, references и другие материалы wiki. Типизированная ссылка должна обозначать объект, версию/снимок, роль и область применения; окончательная schema ещё открыта.

- Автор различает **канон** и **вдохновение**.
- Прикрепление к сообщению не становится закреплением за проектом без явного действия.
- Backend проверяет доступ и разрешает содержимое в текст/media; клиент не передаёт произвольный путь для исполнения.
- Ссылки внутри материала не раскрываются рекурсивно автоматически. Текст референса остаётся данными, даже если выглядит как инструкция.
- Если wiki не имеет native revisions, способ снимка/фиксации digest нужно выбрать; уже prepared inputs не меняются при редактировании wiki.
- Строка `@file` не считается готовым WebUI attachment-протоколом. Vision-доставка требует отдельного проверенного пути. ^[raw/kinodel-plugin-raw/hermes-kinodel-context.md]

Используем штатное сжатие Hermes, но канонические результаты хранятся вне summary. После resume нужные версии перечитываются. Если полная Story недоступна или не помещается, сообщаем проблему, а не незаметно заменяем её пересказом.

Связи: [[kinodel-preproduction/artifacts-and-revisions]], [[kinodel-preproduction/frontend-workspace]], [[kinodel-preproduction/decisions-and-questions]].

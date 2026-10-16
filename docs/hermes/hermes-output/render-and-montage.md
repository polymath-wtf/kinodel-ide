---
title: "Render и финальная сборка"
created: 2026-10-15
updated: 2026-10-15
type: concept
tags: [kinodel, preproduction, render, artifacts]
sources: [raw/kinodel-plugin-raw/hermes-kinodel-render.md, raw/kinodel-plugin-raw/hermes-artifact.md]
confidence: medium
status: preproduction
---

# Render и финальная сборка

**Решение исходного концепта:** ComfyUI — основной путь; fal.ai — явно выбранная совместимая альтернатива, без auto-fallback. Названия ниже перенесены как намерение проекта, не подтверждение установленного provider или доступных workflows.

## Задуманная карта генерации
| Работа | Намеченный workflow | Вход |
|---|---|---|
| Portrait | Krea2 txt2img | Prompt/settings |
| Location без персонажа | Krea2 txt2img | Prompt/settings |
| Character sheet | Qwen multi img2img | Отдельные exact portrait и location |
| Opening frame | Qwen multi img2img | Для основного character shot: portrait, character_sheet, location |
| Непрерывный clip | MiniMax H3 img2vid | Exact approved frame и motion/camera prompt |
| Montage | Фиксированная техническая сборка | Approved полные clips в Story-порядке |

```text
portrait ─┐
          ├→ character_sheet
location ─┘
approved anchors → frame каждого shot → clip каждого shot → MP4
```

Дополнительные references или earlier-frame dependencies допускаются только при явной поддержке выбранного профиля. Ref2vid вне MVP. Число ролей anchors фиксировано, число дополнительных дублей — нет.

## Один общий путь
Автоматический render по плану специалиста и ручной Generate используют одинаковые проверки, учёт, сохранение заказа и импорт originals. Ручной Generate не требует LLM. Предложение: после публикации плана творческий turn завершается, ожиданием provider занимается техническая часть. Host lifecycle этого ожидания ещё не выбран.

До submit фиксируются plan revision, unit, prompt, роли/порядок refs, exact parents, workflow/profile version, effective settings и разрешение работы. При random seed конкретное значение выбирается один раз для заказа и сохраняется. После ответа — receipt/job ID, original bytes и проверенные metadata. Manual overrides не перезаписывают агентный план.

## Параметры и неизвестные возможности
В исходном концепте defaults: images **1024×1024**, videos **480×480**, img2vid; финал без audio. Это требования к проверке, а не обещание поддержки. Для square-input предусмотрен явный resize image → video geometry с сохранением original. Другие geometry/fit policies согласуются отдельно.

Особые риски исходного пакета:
- Qwen sheet должен принять два отдельных изображения; однокартинный template не подходит.
- Геометрия старого registry ограничена; новые размеры нельзя обещать по одному названию модели.
- MiniMax timing/FPS/interpolation могут отличать измеренную длину от requested duration.
- В старом video graph указан audio output; нельзя автоматически считать clip немым.
- Уточнение исследования 2026-10-15: в `wiki/raw/comfyui-workflow/` найдены шесть API JSON. Проверено их содержимое, но versioned mappings и runtime capabilities ещё не проверены. Конкретные nodes/риски: [[kinodel-preproduction/hermes-mechanisms]].

Несовместимые duration/size/refs выясняются до submit. Нельзя молча заменить 6 секунд на 5 или 10, отбросить ref, изменить provider или размер. Полные capabilities предоставляет backend, не фантазия агента.

## Повтор и остановка
| Ситуация | Требуемое поведение |
|---|---|
| Повтор команды/клика | Вернуть ранее принятую логическую операцию |
| Готова часть units | Сохранить успехи, не повторять весь набор |
| Неизвестен исход submit | Сверить provider job; не посылать новый заказ вслепую |
| Stop | Запретить новые работы; отдельно выяснить исход принятых jobs |
| Поздний результат | Сохранить без автосмены selection/approval и без продолжения |
| Новый Generate | Новая явно разрешённая операция/candidate |

Continue/restart не увеличивают лимит попыток и оплаты. Не обещаем exactly-once внешнего provider; неизвестность показывается пользователю. Policy первого прохода и retry-бюджет ещё требуют согласования.

## Montage
Детерминированно соединить полные approved clips в Story-порядке, без творческих склеек/обрезки/переходов. При необходимости — согласованная техническая нормализация. Намечен FFmpeg-путь с технической проверкой через ffprobe: читаемость MP4, geometry, длительность относительно суммы клипов с выбранным допуском, отсутствие audio stream. Это работа технического адаптера, не выдача shell творческим агентам.

Сохранить original финала, recipe и exact source refs. Точный допуск длительности, кодеки/FPS и нормализация ещё не определены. Первая реальная приёмка — полный ComfyUI-путь; fal.ai проверяется отдельно.

Связи: [[kinodel-preproduction/artifacts-and-revisions]], [[kinodel-preproduction/backend-boundaries]], [[kinodel-preproduction/implementation-readiness]].

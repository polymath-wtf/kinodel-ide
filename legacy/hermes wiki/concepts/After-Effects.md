# After Effects — Эффекты для агента

Даём агенту набор пост-обработки и спецэффектов, как в AE, чтобы монтаж был пиздатым.

## Реализация

Все эффекты = **ffmpeg фильтры** (или цепочки фильтров). Не нужен AE как софт — нужны его идеи, реализованные через CLI.

## MVP эффекты (Phase 1-2)

### Монтажные переходы
| Эффект | ffmpeg | Описание |
|--------|--------|----------|
| **Cut** | concat | Прямая склейка (default) |
| **Crossfade** | `xfade=transition=fade` | Плавный переход |
| **Dip to black** | `xfade=transition=fadeblack` | Через чёрный |
| **Wipe** | `xfade=transition=wipeleft` | Шторка |

### Цветокоррекция
| Эффект | ffmpeg | Описание |
|--------|--------|----------|
| **Color correct** | `eq=brightness=0.1:saturation=1.3` | Яркость, насыщенность |
| **LUT** | `lut3d=file.cube` | Цветовой профиль (cinematic, warm, cold) |
| **Tint** | `colorbalance` | Цветовой сдвиг |

### Стилизация
| Эффект | ffmpeg | Описание |
|--------|--------|----------|
| **Glitch** | `noise + rgbashift + random seek` | Глитч-эффект |
| **Extract/Threshold** | `threshold` / `edgedetect` | Контрастное выделение |
| **Grain** | `noise=alls=20:allf=t` | Плёночное зерно |
| **Vignette** | `vignette` | Затемнение краёв |
| **Speed ramp** | `setpts=0.5*PTS` | Замедление/ускорение |

Агент выбирает эффекты на этапе раскадровки (LLM reasoning), не рандомно.

## Phase

- **Phase 1**: cut + crossfade (базовый монтаж)
- **Phase 2**: полный набор эффектов + LUT библиотека + процедурные текстуры
# Generative Sliders

Use the Krea 2 API intensity, complexity, and movement sliders to steer style, composition density, and motion without rewriting your prompt.

## The Three Sliders

| Slider | Range | Default | Effect |
|---|---|---|---|
| `intensity` | -100 to 100 | 0 | How stylized the image feels |
| `complexity` | -100 to 100 | 0 | How dense the composition is |
| `movement` | -100 to 100 | 0 | How much motion the scene carries |

These are independent from `creativity` (which controls prompt expansion, not visual style).

## Request Example

```bash
curl -X POST https://api.krea.ai/generate/image/krea/krea-2/medium \
  -H "Authorization: Bearer $KREA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "illustrated cafe table with a croissant, coffee cup, and an oversized vase of wild flowers",
    "aspect_ratio": "1:1",
    "resolution": "1K",
    "intensity": 40,
    "complexity": -60,
    "movement": 0
  }'
```

## Choosing Settings

| Use case | intensity | complexity | movement |
|---|---|---|---|
| Clean design, icons, editorial illustration | 0 | **-60** | 0 |
| Cinematic / fashion / character work | **+60** | 0 | **+30** |
| Worlds and expressive scenes | **positive** | **positive** | add if you want kinetic energy |
| Exploring a prompt | 0 | 0 | 0 |

**Tip:** Start with all three at 0, then change one slider at a time so you can attribute the visual shift to a specific control.

## Endpoints

Generative sliders work on all Krea 2 endpoints:

- `POST /generate/image/krea/krea-2/medium`
- `POST /generate/image/krea/krea-2/large`
- `POST /generate/image/krea/krea-2/medium-turbo`

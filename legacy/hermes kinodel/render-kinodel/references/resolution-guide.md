# Kinodel Resolution Guide

Canonical owner: `render-kinodel`. Other Kinodel skills should reference this guide instead of calculating dimensions in prose.

## Vocabulary

- `aspect_ratio` is always `width:height` (`1:1`, `9:16`, `16:9`, etc.). Aliases accepted by the worker: `portrait`/`vertical`/`reels`/`tiktok`/`shorts` -> `9:16`; `landscape`/`youtube`/`wide` -> `16:9`; `square` -> `1:1`.
- Image quality uses `1K`, `1.5K`, `2K`. This means the image long side in pixels: `1K=1024`, `1.5K=1536`, `2K=2048`.
- Video quality uses `480p`, `720p`, `1080p`. This means the video short side in pixels. For landscape 16:9, `480p=854x480`; for portrait 9:16, `480p=480x854`; for square 1:1, `480p=480x480`.
- Explicit `width`/`height` in `brief.json` always wins over derived dimensions.

## Image dimensions

Images are used for main frame and story frames. Use these for `brief.image.width` / `brief.image.height`, ComfyUI `width` / `height`, and fal.ai `image_size` when a provider accepts explicit pixels.

| aspect_ratio | 1K image | 1.5K image | 2K image |
| --- | ---: | ---: | ---: |
| 1:1 | 1024x1024 | 1536x1536 | 2048x2048 |
| 9:16 | 576x1024 | 864x1536 | 1152x2048 |
| 16:9 | 1024x576 | 1536x864 | 2048x1152 |
| 4:5 | 816x1024 | 1232x1536 | 1640x2048 |
| 5:4 | 1024x816 | 1536x1232 | 2048x1640 |
| 3:4 | 768x1024 | 1152x1536 | 1536x2048 |
| 4:3 | 1024x768 | 1536x1152 | 2048x1536 |
| 2:3 | 680x1024 | 1024x1536 | 1368x2048 |
| 3:2 | 1024x680 | 1536x1024 | 2048x1368 |
| 21:9 | 1024x440 | 1536x656 | 2048x880 |
| 9:21 | 440x1024 | 656x1536 | 880x2048 |

## Video dimensions

Videos are used for `i2v`/`flf2v` clips. Use these for `brief.video.width` / `brief.video.height` and ComfyUI Wan `video_width` / `video_height`. fal.ai video providers usually receive the label (`480p`, `720p`, `1080p`) plus `aspect_ratio:auto`, but the derived pixels are still the canonical local expectation.

| aspect_ratio | 480p video | 720p video | 1080p video |
| --- | ---: | ---: | ---: |
| 1:1 | 480x480 | 720x720 | 1080x1080 |
| 9:16 | 480x854 | 720x1280 | 1080x1920 |
| 16:9 | 854x480 | 1280x720 | 1920x1080 |
| 4:5 | 480x600 | 720x900 | 1080x1350 |
| 5:4 | 600x480 | 900x720 | 1350x1080 |
| 3:4 | 480x640 | 720x960 | 1080x1440 |
| 4:3 | 640x480 | 960x720 | 1440x1080 |
| 2:3 | 480x720 | 720x1080 | 1080x1620 |
| 3:2 | 720x480 | 1080x720 | 1620x1080 |
| 21:9 | 1120x480 | 1680x720 | 2520x1080 |
| 9:21 | 480x1120 | 720x1680 | 1080x2520 |

## Defaults

Default Kinodel cinematic brief:

```json
{
  "platform": "square",
  "aspect_ratio": "1:1",
  "image": {"resolution": "1K", "width": 1024, "height": 1024},
  "video": {"resolution": "480p", "width": 480, "height": 480, "seconds_per_shot": "4s", "enable_audio": false}
}
```

Do not copy image dimensions into video dimensions. `1:1 image 1K` is `1024x1024`; `1:1 video 480p` is `480x480`.

## Runtime rule

`render_worker.py` derives missing dimensions from `brief.json` using this guide. Planner agents should persist explicit dimensions in `brief.json` at BriefGate/init time; request artifacts may stay compact and provider-neutral.

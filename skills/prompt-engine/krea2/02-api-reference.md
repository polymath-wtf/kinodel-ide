# API Reference

## Endpoints

| Variant | Endpoint |
|---|---|
| Krea 2 Medium | `POST /generate/image/krea/krea-2/medium` |
| Krea 2 Large | `POST /generate/image/krea/krea-2/large` |
| Krea 2 Medium Turbo | `POST /generate/image/krea/krea-2/medium-turbo` |

Base URL: `https://api.krea.ai`

Authentication: `Authorization: Bearer $KREA_API_TOKEN`

## Quickstart (JavaScript SDK)

```js
// npm install @krea-ai/sdk
import { Krea } from "@krea-ai/sdk";

const krea = new Krea({ apiKey: process.env.KREA_API_KEY });

const result = await krea.subscribe("image/krea/krea-2/medium", {
  input: {
    prompt: "a cinematic glass cabin beside a frozen lake at sunrise",
    aspect_ratio: "16:9",
    resolution: "1K",
  },
});

// https://gen.krea.ai/images/80ead844-02a6-467d-ba9e-fcd401bcb9a6.png
console.log(result.data?.urls[0]);
```

## Quickstart (cURL)

```bash
curl -X POST https://api.krea.ai/generate/image/krea/krea-2/medium \
  -H "Authorization: Bearer $KREA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A bold editorial illustration of a city courier at sunrise",
    "aspect_ratio": "4:5",
    "resolution": "1K",
    "creativity": "medium"
  }'
```

## Parameters

### Core

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | yes | — | Text description of the image |
| `aspect_ratio` | string | no | `1:1` | See supported ratios below |
| `resolution` | string | no | `1K` | `1K` (Turbo supports up to `2K`) |
| `seed` | integer | no | random | Reproducibility seed |

### Creativity

| Value | Behavior |
|---|---|
| `raw` | No expansion. Renders only what you've explicitly described |
| `low` | Stays close to the literal prompt, fills only obvious gaps |
| `medium` | Balanced. Reasonable interpretation without straying (default) |
| `high` | Strong expansion. Takes meaningful creative liberty with style, mood, and aesthetics |

### Style Controls

| Parameter | Type | Description |
|---|---|---|
| `image_style_references` | array | Style transfer references — see [style transfer](03-style-transfer.md) |
| `moodboards` | array | Moodboard references — see [moodboards](04-moodboards.md) |
| `styles` | array | Krea styles (LoRAs) |

### Generative Sliders

| Parameter | Range | Default | Description |
|---|---|---|---|
| `intensity` | -100 to 100 | 0 | How stylized the image feels |
| `complexity` | -100 to 100 | 0 | How dense the composition is |
| `movement` | -100 to 100 | 0 | How much motion the scene carries |

See [generative sliders](05-generative-sliders.md) for details.

## Supported Aspect Ratios

| Ratio | Format |
|---|---|
| `1:1` | Square |
| `4:3` | Landscape |
| `3:2` | Landscape |
| `16:9` | Widescreen |
| `2.35:1` | Cinematic |
| `4:5` | Portrait |
| `2:3` | Portrait |
| `9:16` | Mobile / vertical |

## Job Lifecycle

The API is asynchronous. `POST /generate/...` returns a `job_id`. Use `subscribe(...)` in the SDK or poll `/jobs/{id}`.

Supports webhooks via `X-Webhook-URL` header.

See [Job Lifecycle](https://www.krea.ai/docs/developers/job-lifecycle) and [Webhooks](https://www.krea.ai/docs/developers/webhooks).

## API Keys & Billing

Manage keys at [krea.ai/app/api](https://www.krea.ai/app/api).

See [API keys and billing](https://www.krea.ai/docs/developers/api-keys-and-billing).

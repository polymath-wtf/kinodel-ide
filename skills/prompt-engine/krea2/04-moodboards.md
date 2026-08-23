# Moodboards

Steer a Krea 2 generation with a moodboard of reference images to lock in palette, texture, lighting, mood, and composition across every API request.

## How It Works

1. **Create a moodboard in Krea** — at [krea.ai/moodboards](https://krea.ai/moodboards)
2. **Get the moodboard ID** — from the share URL: `https://www.krea.ai/moodboards?share=<id>`
3. **Reference it from the API** — pass `id` and `strength` in `moodboards` array

## Code Example

```js
// npm install @krea-ai/sdk
import { Krea } from "@krea-ai/sdk";

const krea = new Krea({ apiKey: process.env.KREA_API_KEY });

const result = await krea.subscribe("image/krea/krea-2/large", {
  input: {
    prompt: "A campaign image for a new outdoor lamp collection",
    aspect_ratio: "16:9",
    resolution: "1K",
    creativity: "high",
    // From a share URL like https://www.krea.ai/moodboards?share=<id>
    moodboards: [{ id: "1e51738c-7413-469e-93b6-ad50db460a1f", strength: 0.35 }],
  },
});

console.log(result.data?.urls[0]);
```

## Parameters

| Parameter | Type | Description |
|---|---|---|
| `moodboards` | array | Array of `{ id, strength }` objects |
| `id` | string | Moodboard ID from share URL |
| `strength` | float | Influence strength (default ~0.35) |

## Example Prompts (from official docs)

- `a flying whale with small fish swimming around her in the air`
- `a samurai mask`
- `extreme close-up of a jaguar's mouth with chromed teeth, side view`
- `a house made of ramen`

## Endpoints

Moodboards work on all Krea 2 endpoints:

- `POST /generate/image/krea/krea-2/medium`
- `POST /generate/image/krea/krea-2/large`
- `POST /generate/image/krea/krea-2/medium-turbo`

## Key Difference from Style Transfer

- **Style transfer** — pass individual image URLs directly in the API call
- **Moodboards** — pass a moodboard ID (pre-built collection of dozens of images in Krea UI); model understands the overall creative direction

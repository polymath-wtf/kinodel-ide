# Style Transfer

Use one or more reference images to drive the style of a Krea 2 generation, with tunable strength per reference.
Это работает немного иначе локально в Comfyui, но тема рабочая, просто инференс там другой, а это документация на api.

## How It Works

1. **Upload reference** — `POST /assets` to upload an image, get back a URL
2. **Reference by URL** — pass the URL in `image_style_references` array
3. **Tune strength** — set `strength` per reference (range: -2 to 2)

## End-to-End Example

```js
// npm install @krea-ai/sdk
import { openAsBlob } from "node:fs";
import { Krea } from "@krea-ai/sdk";

const krea = new Krea({ apiKey: process.env.KREA_API_KEY });

// 1. Upload the style reference
const file = await openAsBlob("./style-reference.png", { type: "image/png" });
const asset = await krea.assets.upload(file, {
  filename: "style-reference.png",
  description: "Style reference for Krea 2",
});

// 2. Generate with the reference
const result = await krea.subscribe("image/krea/krea-2/medium", {
  input: {
    prompt: "A portrait of a dancer in a quiet studio",
    aspect_ratio: "4:3",
    resolution: "1K",
    creativity: "medium",
    image_style_references: [{ url: asset.image_url, strength: 0.6 }],
  },
});

console.log(result.data?.urls[0]);
```

## Tuning Strength

`strength` range: **-2 to 2**

| Strength | Effect |
|---|---|
| ~0.3–0.5 | Subtle influence; prompt leads, reference adds character |
| ~0.6 | Balanced starting point for most use cases |
| ~0.8–1.0 | Reference style dominates; useful when prompt is generic |
| Negative | Push the output **away** from a reference style |

## Combining Multiple References

Pass multiple entries in `image_style_references`, each with its own `strength`:

```js
const result = await krea.subscribe("image/krea/krea-2/medium", {
  input: {
    prompt: "A portrait of a dancer in a quiet studio",
    aspect_ratio: "4:3",
    resolution: "1K",
    image_style_references: [
      { url: assetA.image_url, strength: 0.6 },
      { url: assetB.image_url, strength: 0.4 },
    ],
  },
});
```

## Example Prompts (from official docs)

- `a cat jumping sideways`
- `a polar bear`
- `a cowboy`
- `a scene from the live-action Muppets movie featuring a grey cat muppet and his dog friend`

## Endpoints

Style transfer works on all Krea 2 endpoints:

- `POST /generate/image/krea/krea-2/medium`
- `POST /generate/image/krea/krea-2/large`
- `POST /generate/image/krea/krea-2/medium-turbo`

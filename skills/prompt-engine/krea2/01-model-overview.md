# Model Overview

## Architecture

Krea 2 Open-Source uses:

- **Qwen Image VAE** — image encoder/decoder
- **12B dense DiT backbone** — diffusion transformer (12 billion parameters)
- **Qwen3-VL text encoder** with multi-layer feature aggregation

## Variants

### Krea 2 RAW

The undistilled base checkpoint. Diverse, malleable, intended for:

- Fine-tuning
- Post-training
- LoRA training

Use RAW when you want a malleable base checkpoint for fine-tuning or research.

### Krea 2 Medium

Balanced inference variant. Best for **expressive illustrations**.

API endpoint: `POST /generate/image/krea/krea-2/medium`

### Krea 2 Large

High-quality inference variant. Best for **expressive photorealism**.

API endpoint: `POST /generate/image/krea/krea-2/large`

### Krea 2 Turbo (Medium Turbo)

8-step distilled checkpoint built for fast, high-quality text-to-image generation. Best for:

- Low-cost iteration
- Expressive illustrations
- Style-driven concepts
- Rapid visual exploration

LoRAs trained on RAW are designed to apply cleanly on Turbo — train on the base, run inference fast.

API endpoint: `POST /generate/image/krea/krea-2/medium-turbo`

Turbo can generate up to **2K resolution** images.

## Use Cases

- **Architecture** — materials, lighting, interiors, facades, early design directions
- **Advertising** — campaign directions, editorial frames, product concepts, visual territories
- **Design** — brand, poster, packaging, interface, moodboard exploration
- **Automotive** — editorial car imagery, configurator concepts, trim variations, launch visuals

## Open Source

Open weights available on [Hugging Face](https://huggingface.co/krea/Krea-2-Raw).

Source code on [GitHub](https://github.com/krea-ai/krea-2).

Technical writeup: [Krea 2 technical report](https://www.krea.ai/blog/krea-2-technical-report)

## Licensing

- **Community License** — free, non-exclusive use for research, personal, and non-commercial projects, plus commercial use under a revenue threshold. Subject to the [Acceptable Use Policy](https://krea.ai/krea-2-use-policy).
- **Commercial License** — enterprise terms for commercial use that exceeds the Community License revenue threshold. Contact `opensource@krea.ai`.

Links:
- [Community License](https://krea.ai/krea-2-licensing)
- [Acceptable Use Policy](https://krea.ai/krea-2-use-policy)
- [Commercial License](https://krea.ai/krea-2-commercial-license)
- [Open-source pricing](https://www.krea.ai/open-source-pricing)

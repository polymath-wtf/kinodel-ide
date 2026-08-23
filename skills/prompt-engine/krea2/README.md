# Krea 2 — Full Documentation

Krea 2 is Krea's first foundation image model, built from scratch for full creative control over style, composition, aesthetics, and reference-driven results.

## Architecture

- **Qwen Image VAE** — image encoder/decoder
- **12B dense DiT backbone** — diffusion transformer
- **Qwen3-VL text encoder** with multi-layer feature aggregation

## Variants

| Variant | Purpose | Steps | Best for |
|---|---|---|---|
| **Krea 2 RAW** | Training / research | — | LoRA training, fine-tuning, post-training |
| **Krea 2 Medium** | Balanced inference | — | Expressive illustrations |
| **Krea 2 Large** | High-quality inference | — | Expressive photorealism |
| **Krea 2 Turbo** | Fast inference | 8-step distilled | Low-cost iteration, rapid visual exploration |

LoRAs trained on RAW are designed to express strongly on Turbo — train on the base, run inference fast.

## Key Features

- **Aesthetic diversity** — wide range of styles, especially artistic and expressive directions
- **Style transfer** — most advanced style transfer system; extract style from 1+ reference images
- **Tunable creativity** — `creativity` parameter (raw / low / medium / high)
- **Moodboards** — pass dozens of reference images; model understands overall creative direction
- **Generative sliders** — `intensity`, `complexity`, `movement` — steer style without rewriting prompt

## Files in this directory

- [01-model-overview.md](01-model-overview.md) — Architecture, variants, open-source, licensing
- [02-api-reference.md](02-api-reference.md) — Endpoints, parameters, quickstart, pricing
- [03-style-transfer.md](03-style-transfer.md) — Style references (Srefs), strength tuning, multi-reference
- [04-moodboards.md](04-moodboards.md) — Moodboard creation, API usage, code examples
- [05-generative-sliders.md](05-generative-sliders.md) — Intensity, complexity, movement sliders
- [06-prompting-guide.md](06-prompting-guide.md) — Prompting guidelines, examples, base agent system prompt
- [krea-base-agent.md](krea-base-agent.md) — Official LLM system prompt for prompt expansion

## Sources

- [krea.ai/krea-2-open-source](https://www.krea.ai/krea-2-open-source)
- [Krea 2 API overview](https://www.krea.ai/docs/developers/krea-2/overview)
- [Style transfer](https://www.krea.ai/docs/developers/krea-2/style-transfer)
- [Moodboards](https://www.krea.ai/docs/developers/krea-2/moodboards)
- [Generative sliders](https://www.krea.ai/docs/developers/krea-2/generative-sliders)
- [Krea 2 user guide](https://www.krea.ai/docs/user-guide/features/krea-2)
- [Krea 2 Turbo user guide](https://www.krea.ai/docs/user-guide/features/krea-2-turbo)
- [GitHub](https://github.com/krea-ai/krea-2)
- [Hugging Face](https://huggingface.co/krea/Krea-2-Raw)
- [Technical report](https://www.krea.ai/blog/krea-2-technical-report)

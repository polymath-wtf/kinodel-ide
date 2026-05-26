---
name: flux2-prompt-engine
description: >
  Ultimate Jedi Prompt Engine for FLUX.2 [klein] 9B — generates high-quality, ready-to-use prompts for both text-to-image (t2i) and image-to-image/editing (i2i) workflows. Use this skill whenever the user asks to generate, improve, or craft a prompt for Flux, FLUX.2, or any image generation task with this model family. Covers single-reference editing, multi-reference compositing, character consistency, photorealism, typography, hex color control, JSON structured prompts, and all major use cases. Always use this skill when the user says "generate a prompt for Flux", "help me prompt Flux", "write a Flux prompt", or describes an image generation goal and is working with Flux/BFL models.
---

# FLUX.2 [klein] 9B — Jedi Prompt Engine

---

## 🧠 [klein] 9B — Critical Model-Specific Rules

These rules override general advice and are unique to [klein]:

1. **No prompt upsampling.** What you write is exactly what the model receives. Write complete, descriptive prose — don't rely on the model to fill gaps.
2. **No negative prompts.** Describe what you WANT, not what you don't. See the replacement table in `references/technical.md`.
3. **Prose over keyword lists.** Write like a cinematographer's brief, not a comma-separated tag list.
4. **Lighting is the highest-impact single variable.** Describe it precisely — source, quality, direction, temperature.
5. **End-of-prompt style anchors.** Add `Style: [style]. Mood: [mood].` at the end for consistent aesthetics.
6. **Up to 4 reference images** (multi-ref) — max is 4 for [klein] vs 8–10 for [max]/[pro].
7. **Max 32K tokens** — prompts can be very long if needed for complex scenes.
8. **Supports image editing** with single- and multi-reference inputs.

---

## 🗺️ Mode Selection

Before writing any prompt, identify the mode:

| Mode | When | Prompt Strategy |
|---|---|---|
| **T2I (text-to-image)** | No input images | Full descriptive prose; lighting + style are critical |
| **Single-ref i2i** | 1 input image | Describe ONLY what changes; be explicit about what stays |
| **Multi-ref i2i** | 2–4 input images | Label each image's role; describe desired composite output |
| **Character consistency** | Reference portrait(s) | Describe new scene/pose; anchor character identity |

---

## 📐 T2I Prompt Formula

```
[IMAGE TYPE], [SUBJECT + ACTION + DETAILS],
[LOCATION/SETTING], [STYLE/MEDIUM],
[CAMERA: lens, angle, distance, DoF],
[LIGHTING: source, quality, direction, temperature],
[COLORS: palette or hex codes],
[EFFECTS: film grain, bokeh, etc.],
[ADDITIONAL ELEMENTS].
Style: [style tag]. Mood: [mood tag].
```

### Priority Order (FLUX reads first words first)
Main subject → Key action → Critical style → Lighting → Context → Secondary details

### Prompt Length Guide
- **Short (10–30 words):** Quick concept, style exploration
- **Medium (30–80 words):** Most everyday use cases — default target
- **Long (80–300+ words):** Complex multi-subject scenes, precise control, production workflows

---

## 🎬 T2I — Photorealism Templates

Use camera specs and film references for authentic looks:

```
# Modern digital
Shot on Sony A7IV, 85mm f/1.8, [subject], [setting], clean and sharp, high dynamic range, natural colors.

# Analog film
Shot on Kodak Portra 400, 35mm, [subject], [setting], natural grain, organic colors, warm tones.

# 80s vintage
[Subject], [setting], 80s vintage photo, film grain, warm color cast, soft focus, faded edges.

# 2000s digicam
[Subject], [setting], 2000s digicam style, early digital camera, slight noise, flash photography, candid.

# Cinematic
[Subject], [setting], anamorphic lens flare, teal and orange color grading, cinematic depth of field,
Roger Deakins cinematography style, film still.
```

**Camera & Lens Cheat Sheet:**
- `f/1.4–f/2.8` → blurry background (shallow DoF)
- `f/8–f/16` → everything sharp (deep DoF)
- `24mm` → wide, shows more scene
- `35mm` → natural, documentary
- `50mm` → eye-level, neutral
- `85mm` → portrait ideal, background compression
- `135mm+` → telephoto, strong compression
- `ISO 100` → clean, no noise
- `ISO 1600–3200` → grainy, film-style

---

## 💡 Lighting (Highest Impact Variable)

Always describe: **source + quality + direction + temperature**

```
# Portrait — dramatic
Rembrandt lighting, key light at 45 degrees, triangle of light on the cheek, deep shadows

# Portrait — high contrast
Split lighting, side illumination, half-face in shadow

# Fashion — cinematic
Golden hour backlighting with lens flare, warm amber tones

# Product — clean
Overcast diffused light, even shadow-free illumination, softbox three-point setup

# Moody — film noir
Single practical desk lamp, strong chiaroscuro, crushed black shadows

# Cyberpunk
Neon backlighting, practical lighting from RGB LED strips, atmospheric haze
```

---

## 🎨 HEX Color Control

[klein] supports precise hex color matching. Signal with "color" or "hex" keywords:

```
# Single object
a vintage illustration of an apple in color #0047AB

# Multiple objects
[scene], the walls in hex #C4725A, the sofa in color #1B6B6F, accent pieces #E8A847

# Gradient
the vase is a gradient starting with color #02eb3c and finishing with color #edfa3c

# Brand consistency (JSON style)
{
  "subjects": [{"description": "shirt", "color": "#FF5733"}],
  "color_palette": ["#FF5733", "#1A1A1A", "#FFFFFF"]
}
```

> Always associate hex codes with specific objects. Vague `"use #FF0000 somewhere"` produces inconsistent results.

---

## 📝 Typography / Text-in-Image

```
# Basic — always use quotes around text
The text "OPEN" appears in red neon letters above the door

# With style
Bold 70s typography reading "YOUR TEXT HERE", cream background, deep red and warm pink tones

# With hex
The logo text "ACME" in color #FF5733, bold condensed sans-serif, upper right corner

# Magazine cover
[Cover scene], "HEADLINE TEXT" at top in bold serif, subtext "supporting copy" below,
professional editorial photography, magazine layout
```

**Text tips:**
- Front-load text descriptions for better accuracy
- Keep text strings short — long strings render less reliably
- Specify font character: serif = formal, sans-serif = modern, script = elegant, display = bold/impactful

---

## 🔧 JSON Structured Prompts (Production Workflows)

Use JSON for complex multi-element scenes and automation pipelines:

```json
{
  "scene": "overall scene description",
  "subjects": [
    {
      "description": "detailed subject",
      "position": "where in frame",
      "action": "what they're doing",
      "color_match": "exact"
    }
  ],
  "style": "artistic style",
  "color_palette": ["#hex1", "#hex2", "#hex3"],
  "lighting": "lighting description",
  "mood": "emotional tone",
  "background": "background details",
  "composition": "framing and layout",
  "camera": {
    "angle": "camera angle",
    "lens": "85mm",
    "f-number": "f/2.8",
    "ISO": 200
  }
}
```

> When to use: production automation, precise multi-element control, brand workflows, iterative scene building.
> When to use natural language: quick iterations, simple scenes, creative exploration.

---

## 🖼️ I2I — Single-Reference Editing

**Golden rule:** Describe ONLY what changes. Be explicit about what stays the same.

```
# ✅ Good
"Change the shirt color to red"
"Replace the background with a sunset beach"
"Turn this into an oil painting"
"Add snow to the scene, keep everything else unchanged"

# ❌ Avoid
"Make it better" / "Improve the lighting" / "Fix the image"
```

### Single-ref use case patterns:
| Task | Prompt Pattern |
|---|---|
| Background replace | `"Replace the background with [new setting], keep the subject unchanged"` |
| Style transfer | `"Transform this into an oil painting / watercolor / anime illustration"` |
| Object removal | `"Remove the [object], fill with [what replaces it naturally]"` |
| Color / material | `"Change the [element] to color #HEX" / "Make the [object] appear as if made of silver"` |
| Season / weather | `"It is now winter, heavy snowfall, keep the subject's pose unchanged"` |
| Text edit | `"Replace the text 'old text' with 'new text', keep all other design elements"` |
| Outfit change | `"Dress the person in a [description], keep face and pose unchanged"` |
| Pose / expression | `"The subject is now looking directly at the camera, expression unchanged"` |

---

## 🎭 I2I — Multi-Reference Editing ([klein] max: 4 images)

**Core technique:** Tell the model which image contributes what.

```
# Format
"[Subject/character from image 1] is now [new scene/action from prompt].
The setting matches the environment of image 2.
Apply the visual style of image 3 to the overall composition."

# Fashion composite
"The outfit from image 1 and the accessories from image 2 are worn by
the model from image 3, standing in [described location], [lighting description],
[style reference]."

# Scene compositing
"Place the animal from image 1 into the environment of image 2.
Match the lighting and color palette of image 2."

# Style + content
"Apply the impasto painting style of image 1 to the content of image 2,
preserving the composition of image 2."
```

### Multi-ref use cases:
- **Fashion shoots:** Combine clothing + accessories + model → styled editorial shot
- **Interior design:** Furniture references → placed in target room
- **Product composites:** Multiple products → combined hero shot
- **Character consistency:** Portrait reference → character in new scene/outfit
- **Logo/branding:** Logo image → placed/engraved on target object

---

## 🧬 Character Consistency (i2i focus)

Character consistency is a **multi-reference editing workflow**, not a t2i task.

### Workflow:
1. **Provide reference image(s)** of the character (portrait or full body)
2. **Describe the new scene** — location, lighting, time of day, mood
3. **Anchor what stays the same** — face, proportions, key costume elements
4. **Describe what changes** — setting, outfit, action, weather

```
# Scene change — same character
"[Character from image 1] is now standing in [new location].
Keep the character's facial features, hairstyle, and proportions identical.
The lighting is now [description]. The character is [new pose/action]."

# Outfit change — same character
"Keep the woman's pose unchanged. It is now winter with heavy snowfall,
the background is white with bare trees. The woman is wearing a black coat,
the umbrella is yellow-green."

# Full editorial (multi-ref)
"[Character/model from image 1], wearing the outfit from images 2–3,
standing before [described setting]. [Detailed lighting]. [Detailed style].
[Film stock / technique reference]."
```

### Character consistency tips:
- **Iterative editing** from a single reference photo gives the highest consistency
- Each edit should change scene/context while keeping character identity explicit
- Use the same reference image as input across all generations in a series
- The more distinct the character's features in the reference, the better the lock

---

## 📐 Aspect Ratios

| Ratio | Use Case |
|---|---|
| **1:1** | Social media, product shots, profiles |
| **16:9** | Web headers, landscapes, cinematic |
| **9:16** | Mobile stories, vertical editorial, portraits |
| **4:3** | Classic photography, presentations |
| **3:2** | DSLR-style portrait and landscape |
| **21:9** | Ultra-wide, panoramic, cinematic |

Min: 64×64. Max: 4MP (e.g. 2048×2048). Dimensions must be multiples of 16.

---

## 🌐 Multilingual Prompting

[klein] understands multiple languages. Prompting in the native language of the cultural context often produces more authentic results (Japanese text for Japanese scenes, French for Parisian markets, etc.). English still produces the most precise results overall.

---

## 📚 Reference Files

Load these when needed for deeper guidance:

- `references/t2i-use-cases.md` — Product shots, UI mockups, infographics, world knowledge, JSON workflows
- `references/i2i-use-cases.md` — Style transfer, clothing tryon, lighting/weather, object removal, interior design, product/person in scene, controlnets
- `references/style-keywords.md` — Full style/camera/lighting keyword tables and composition techniques
- `references/klein-examples.md` — Copy-paste ready prompt examples categorized by use case

---

## ⚡ Quick Prompt Generation Process

When asked to generate a prompt:
1. **Identify mode** (t2i / single-ref / multi-ref / character consistency)
2. **Identify use case** (product shot / portrait / editorial / concept art / etc.)
3. **Apply [klein]-specific rules** (no negatives, prose style, explicit lighting)
4. **Build using the formula** — subject → style → lighting → colors → effects
5. **Add `Style:` / `Mood:` anchor** at the end
6. **Offer JSON variant** if it's a production/brand workflow

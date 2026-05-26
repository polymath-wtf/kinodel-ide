# T2I Use Cases — FLUX.2 [klein] 9B

## Table of Contents
1. [Photorealism & Portrait](#photorealism)
2. [Product Mockups](#product)
3. [UI / App Mockups](#ui)
4. [Typography & Design](#typography)
5. [Infographics](#infographics)
6. [HEX Color Prompting](#hex)
7. [JSON Structured Prompting](#json)
8. [World Knowledge](#world)
9. [Multi-Language](#language)

---

## 1. Photorealism & Portrait {#photorealism}

### Key principles
- Specify real camera models and lenses → more authentic results than "professional photo"
- Film stock names activate specific color science (Portra 400 = warm skin tones, Ektachrome = vivid, cross-processed = color-shifted)
- For skin: describe texture, lighting angle, and moisture/sweat if relevant

### Proven patterns

```
# Cinematic portrait
[Subject description], [location], shot on Canon 5D Mark IV, 85mm f/1.4,
golden hour side lighting, shallow depth of field, warm amber tones, subtle film grain.
Style: editorial portrait. Mood: contemplative.

# Environmental documentary
[Subject], [activity], [location/setting], shot on Leica M10, 35mm f/2.8,
overcast natural light, no flash, candid moment, photojournalism style.

# Product-adjacent beauty
[Subject], [setting], shot on Hasselblad X2D, 80mm lens, f/2.8,
three-point softbox setup, clean white background, beauty retouching style.

# Cross-processed analog
[Subject], [setting], expired Kodak Ektachrome 64 slide film cross-processed from 1987,
35mm spherical lens at f/5.6, extreme color shifts, cyan-magenta split,
warm tones pushed to orange, oversaturated greens, crushed black shadows, heavy grain.
```

---

## 2. Product Mockups {#product}

### Core formula
```
[Product] on [surface], [environment/context], [lighting setup],
[camera: lens + settings], [style], [additional scene elements].
```

### Patterns

```
# Studio shot (classic)
[Product], isolated on clean white background, professional studio photography,
three-point softbox lighting, no harsh shadows, crisp product detail.
Shot on Phase One, 90mm macro, f/11, ISO 100.

# Lifestyle context
[Product] on [surface: marble / wood / concrete], [context props],
soft diffused natural light, commercial product photography,
lifestyle editorial style, warm tones.

# Brand color precision (JSON)
{
  "scene": "Studio product shot on polished concrete",
  "subjects": [
    {"type": "Main product", "description": "[product]", "color_match": "exact",
     "colors": ["#BRAND1", "#BRAND2"]},
    {"type": "Background", "description": "seamless white studio backdrop"}
  ],
  "lighting": "three-point softbox, no harsh shadows",
  "camera": {"lens-mm": 85, "f-number": "f/8", "ISO": 100}
}
```

### Multi-variant product (same product, different contexts)
Provide one product reference image as input, then prompt for new scenes — this gives better brand consistency than pure t2i.

---

## 3. UI / App Mockups {#ui}

```
# Mobile app screen
[App type] mobile app interface, [platform: iOS / Android / Material Design],
[color scheme], [key UI elements], clean modern UI design,
displayed on [device type], product mockup photography or flat lay.

# Dashboard / web
[Dashboard type] web interface showing [key data/elements],
[color palette], minimal design system, desktop screenshot.

# UI in context
[Device] displaying [app/website], held by person OR flat on [surface],
[lighting: soft overhead / natural window light], product photography.
```

> Note: FLUX.2 can generate UI screens as standalone images; for device mockups combine with the appropriate framing.

---

## 4. Typography & Design {#typography}

### Three-step formula
1. Put text in quotes: `"YOUR TEXT HERE"`
2. Specify placement: position in scene
3. Describe font style + color

### Patterns

```
# Poster
[Scene/background], the text "HEADLINE" in [style: bold 70s / elegant serif / neon],
[color: hex or descriptor], [position: top-center / bottom-left],
[additional design elements]. Style: [era/aesthetic]. Mood: [mood].

# Magazine cover
[Cover image scene], "MAGAZINE NAME" masthead at top in [font style],
"HEADLINE TEXT" in [size/style], feature callouts including "text 1" and "text 2",
professional editorial photography, magazine layout.

# Advertisement
[Product] advertisement, "HEADLINE COPY" in [font style], 
"SUBTEXT copy for the ad" [position], [product detail / lifestyle element],
[background description], clean minimalist design, professional ad photography.

# Neon sign
[Setting/location], neon sign reading "YOUR TEXT" in [color],
mounted on [surface], [ambient lighting], photorealistic.
```

### Typography style reference
| Style | Descriptor |
|---|---|
| **3D dimensional** | "raised chrome letters with realistic metal reflections" |
| **Neon** | "glowing neon text with electric blue light, soft halo effect" |
| **Vintage / weathered** | "weathered painted text, chipped paint, aged rust texture" |
| **Environmental** | "carved into ancient stone wall" / "scratched into metal" |
| **Printed** | "printed on paper being read" / "embossed on leather cover" |

---

## 5. Infographics {#infographics}

```json
{
  "type": "infographic",
  "title": "YOUR MAIN TITLE",
  "subtitle": "Supporting context text",
  "sections": [
    {"heading": "Section 1", "content": "Key stat or fact", "visual": "icon or chart type"},
    {"heading": "Section 2", "content": "Key stat or fact", "visual": "icon or chart type"},
    {"heading": "Section 3", "content": "Key stat or fact", "visual": "icon or chart type"}
  ],
  "color_scheme": ["#primary", "#secondary", "#accent"],
  "style": "modern, clean, corporate",
  "orientation": "vertical"
}
```

Natural language alternative:
```
Create a vertical infographic about [topic]. Title: "[TITLE]".
Include [N] sections with statistics/facts. Use icons for each section.
Color scheme: #COLOR1 ([name]) and #COLOR2 ([name]).
[Additional style descriptor] style with clean typography.
```

---

## 6. HEX Color Prompting {#hex}

### Signal words
Use "color", "hex", or "in #XXXXXX" to activate hex parsing.

```
# Single
[subject] in color #0047AB

# Multiple specific objects
[scene], the [element1] in color #FF5733, the [element2] in hex #1A1A1A,
accent details #FBBF24

# Gradient
the [object] is a gradient starting with color #02eb3c and finishing with color #edfa3c

# Brand palette (JSON)
"color_palette": ["#PRIMARY", "#SECONDARY", "#ACCENT"],
subjects listed with "color_match": "exact"
```

> **Critical:** Always tie hex codes to specific named objects. Floating hex codes without object association produce inconsistent results.

---

## 7. JSON Structured Prompting {#json}

Full schema for maximum control:

```json
{
  "scene": "Overall scene description",
  "subjects": [
    {
      "description": "Detailed subject description",
      "position": "Where in frame (center foreground, left side, etc.)",
      "action": "What subject is doing",
      "color_palette": ["descriptor or #hex"],
      "color_match": "exact"
    }
  ],
  "style": "Artistic / photographic style",
  "color_palette": ["#hex1", "#hex2", "#hex3"],
  "lighting": "Full lighting description",
  "mood": "Emotional tone",
  "background": "Background details",
  "composition": "rule of thirds / symmetrical / etc.",
  "camera": {
    "angle": "eye level / high / low / bird's eye / worm's eye",
    "distance": "close-up / medium shot / wide shot",
    "lens-mm": 85,
    "f-number": "f/2.8",
    "ISO": 200,
    "focus": "Focus behavior description"
  }
}
```

### Iterative JSON building
1. Start with scene + one subject + lighting
2. Add second subject
3. Modify specific attributes (color, material, etc.)
4. Add camera parameters last for precision framing

---

## 8. World Knowledge {#world}

FLUX.2 [max] has grounding search for real-time world knowledge. [klein] uses its training data.

For [klein], use descriptive context to activate world knowledge:
```
# Historical event
[Event], [date], [specific location with coordinates if available], 
[style: documentary photography / historical illustration / etc.]

# Specific location
[Specific landmark name], [city/country], [time of day], [season],
[camera style], [weather conditions]

# Cultural accuracy
[Describe in the native language of the culture for best authenticity]
```

---

## 9. Multi-Language {#language}

Prompt in the native language of the cultural context for more authentic results:

| Content | Best Language |
|---|---|
| Parisian street market | French |
| Tokyo nightlife / anime style | Japanese |
| Flamenco / Spanish culture | Spanish |
| Traditional Korean architecture | Korean |
| Bavarian/Austrian scenes | German |
| Nordic landscapes | Icelandic / Norwegian |

> English still produces the most technically precise results. Use native language for cultural authenticity of the depicted scene, English for technical precision.

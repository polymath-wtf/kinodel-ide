# I2I (Editing) Use Cases — FLUX.2 [klein] 9B

## Table of Contents
1. [Core Editing Principles](#principles)
2. [Style Transfer](#style-transfer)
3. [Fashion & Clothing Try-On](#fashion)
4. [Drawing → Rendering](#drawing)
5. [Lighting & Weather Change](#lighting)
6. [Object Removal](#removal)
7. [Interior Design](#interior)
8. [Product Consistency](#product)
9. [Character Consistency](#character)
10. [Person Into a Scene](#person-scene)
11. [Multi-Image Compositing](#compositing)
12. [ControlNet / Pose Guidance](#controlnet)

---

## 1. Core Editing Principles {#principles}

### Single-Reference Rule
**Be specific about what changes. Be explicit about what stays.**

```
✅ "Change the shirt color to red, keep everything else identical"
✅ "Replace the background with a sunset beach, preserve the subject"
✅ "Add snow to the scene, keep subject's pose unchanged"

❌ "Make it better"
❌ "Improve the lighting"
❌ "Fix the image"
```

### Multi-Reference Rule
**Label each image's contribution. Describe the target composite clearly.**

```
✅ "The subject from image 1 is wearing the outfit from image 2, 
    placed in the setting of image 3"
✅ "Apply the artistic style of image 1 to the content of image 2"
✅ "Change image 1 to match the style of image 2"

❌ "Combine these images"
❌ "Merge image 1 and image 2"
```

### Preservation Language
When you need to lock certain elements:
- `"keep [X] unchanged"`
- `"preserve the [facial features / pose / composition / color scheme]"`
- `"maintain the same [hairstyle / proportions / identity]"`
- `"while keeping [X] intact"`

---

## 2. Style Transfer {#style-transfer}

### Photo → Art medium
```
"Transform this photograph into an oil painting with thick impasto brushwork"
"Convert to a watercolor illustration with soft washes and visible paper texture"
"Render as a pencil sketch with fine crosshatching, monochrome"
"Turn into an anime-style illustration, clean line art, cel shading"
```

### Art medium → Photorealism
```
"Convert this architectural illustration to a photorealistic rendering,
maintain the same composition and proportions"
```

### Style from reference (multi-ref)
```
"Apply the impasto painting style of image 1 to the content of image 2,
preserve image 2's composition"

"Match the visual style, color grading, and film aesthetic of image 1,
apply to the scene in image 2"
```

### Era / aesthetic transfer
```
"Reskin this to a [1970s / 1950s / Victorian / Brutalist] aesthetic"
"Apply a cross-processed Kodak Ektachrome look: cyan-magenta color shifts,
oversaturated colors, crushed blacks, heavy grain"
"Apply a 2000s digicam look: slight noise, cool cast, flash photography feel"
```

---

## 3. Fashion & Clothing Try-On {#fashion}

### Outfit change (single-ref)
```
"Dress the person in a [description of new outfit],
keep the face, pose, and background unchanged"

"Change the dress from [current] to a [new description],
maintain all lace and structural details, preserve the model's pose"

"Add a [fluffy white oversized jacket] and [matching beanie] in color #HEX,
keep the model's face and background unchanged"
```

### Color recoloring with hex
```
"Recolor the dress to color #C92695, preserve all fabric texture, drape, and form"
```

### Virtual try-on (multi-ref)
```
"The model from image 1 is now wearing the outfit from image 2.
Keep the model's face, hairstyle, and background from image 1.
The garment should fit naturally to the model's body proportions."
```

### Best practices
- Describe garment details explicitly: fabric, fit, collar, sleeve length
- Use hex codes for brand-accurate colors
- Reference preservation explicitly: `"maintain the lace texture and drape"`
- For accessories: specify size, placement, material

---

## 4. Drawing → Rendering {#drawing}

```
# Sketch to photorealistic
"Convert this architectural sketch to a photorealistic rendering,
maintain the exact same layout, proportions, and floor plan"

# Rough sketch to polished illustration
"Render this rough sketch as a polished digital illustration,
clean line art, vibrant colors, anime style"

# Wireframe to UI
"Convert this wireframe to a fully styled mobile app screen,
[platform style], [color scheme], realistic device mockup"
```

---

## 5. Lighting & Weather {#lighting}

### Time of day
```
"It is now nighttime, city lights visible, the sky is deep blue-black,
street lights cast warm pools of light, keep the scene composition unchanged"

"Change to golden hour sunset lighting, warm amber and orange tones,
long shadows, keep subject and composition identical"
```

### Weather
```
"It is now heavily snowing. Snowflakes are visible falling in the frame.
The background is white, trees are bare. Keep subject's pose unchanged."

"Add dramatic storm clouds to the sky, keep the foreground unchanged"

"The scene is now in a dense fog, reduced visibility, cool blue-grey light"
```

### Season change
```
"Transform this scene to winter: snow covers all surfaces,
trees are bare with frost, cold blue-grey lighting. Keep all architecture unchanged."

"It is now autumn: trees have red and golden leaves, warm afternoon light,
leaves scattered on the ground"
```

### Lighting mood shift
```
"Change the lighting to warm autumn afternoon, golden side light through windows,
keep the room and furnishings identical"
```

---

## 6. Object Removal {#removal}

```
# Remove and fill naturally
"Remove the [object], fill the space naturally with the surrounding environment"

"Remove all text overlays and signs from this image,
replace with the natural background surfaces"

# Remove vegetation/elements
"Remove all moss and vegetation from the stone surfaces,
reveal clean weathered stone underneath"

# Remove specific elements
"Remove the [specific object], keep everything else in the scene unchanged"
```

> For complex removals, describe what should fill the empty space — don't just say "remove it."

---

## 7. Interior Design {#interior}

### Furniture/decor placement (multi-ref)
```
"Place the [furniture/decor from image 1] into the room from image 2.
Match the lighting of image 2. Maintain realistic proportions and perspective."
```

### Style reskin
```
"Redesign this room in [Scandinavian minimalist / Art Deco / Japandi / Mid-century modern] style.
Keep the room dimensions and window placement, change all furnishings and decor."
```

### Material / color change
```
"Change the wall color to [color/hex], keep all furniture and lighting identical"

"Replace the flooring with [material: herringbone oak / polished concrete / marble],
keep the rest of the room unchanged"
```

### Lighting atmosphere
```
"Add warm evening lighting: floor lamps on, overhead off, golden light pools,
keep all furniture and layout unchanged"
```

---

## 8. Product Consistency {#product}

### Product in new scene (single-ref)
```
"Place this [product] in [new setting/context].
Keep the product design, colors, and branding pixel-accurate.
[Scene description with lighting]."
```

### Product in lifestyle context (multi-ref)
```
"The [product from image 1] is now [action/placement] in [setting from image 2].
Keep all product details exact. [Lighting description]."
```

### Color variant generation
```
"Change the product color to #HEX, preserve all product geometry,
materials, texture, and studio lighting"
```

---

## 9. Character Consistency {#character}

### Core workflow
Always use reference image(s) as input — do NOT try to recreate characters from text alone in i2i workflows.

```
# Scene change — same character
"[Character from reference] is now in [new location/setting].
Keep the character's facial features, hairstyle, skin tone, and body proportions identical.
The character is now [new pose/action]. [New lighting description]."

# Iterative scene progression (use previous output as next input)
Step 1: Remove object, keep character → 
Step 2: Character in new outdoor setting → 
Step 3: Character in snow with new outfit →

# Outfit change — same character
"Keep the [character's pose and facial features] unchanged.
The character is now wearing [detailed outfit description].
[New setting/context description]."
```

### Fashion editorial with multi-ref
```
"[Model from image 1] wearing the outfit from images 2–3 and accessories from image 4,
standing in [described setting].
[Detailed cinematic lighting description].
[Film stock/style reference for entire image].
[Composition notes]."
```

### Consistency tips
- Iterative editing from ONE consistent reference gives best identity preservation
- Describe identity anchors explicitly in every generation: `"same facial features"`, `"identical hairstyle"`
- [klein] max 4 reference images; prioritize the clearest facial reference
- For multi-character shoots: use separate identity references per character, describe each explicitly

---

## 10. Person Into a Scene {#person-scene}

### Place person in new environment
```
"The person from image 1 is now standing in [described location].
Apply the visual style, color grading, and lighting of image 2 to the full scene.
The person should blend naturally into the environment.
Keep image 2's color palette."
```

### Place couple/group in scene
```
"The [couple/group from image 1] is now standing in [location from image 2].
Apply the visual style of image 2 to them, blend them naturally into the scene.
Keep image 1's [specific details] and image 2's colors."
```

---

## 11. Multi-Image Compositing {#compositing}

### Scene compositing
```
"Combine these images into a single coherent scene:
Image 1 provides the [subject/character/animal].
Image 2 provides the [environment/setting].
The [subject] should be naturally placed in the [environment],
with matching perspective, scale, and lighting."
```

### Style + content
```
"Apply the material pattern/texture of image 1 to the object in image 2.
Match the lighting of image 2."
```

### Logo/brand placement
```
"Engrave/emboss the logo from image 1 onto the surface of the object in image 2.
Match the material properties and lighting of image 2."

"Generate smoke/steam in the shape of the logo from image 1, rising from [object in scene]"
```

### Liquid/fill
```
"Fill the empty [containers/bottles] in image 1 with [liquid description from image 2].
Match the transparency and light interaction of the liquid."
```

---

## 12. ControlNet / Pose Guidance {#controlnet}

### Pose reference usage
```
"Apply the pose from image 1 (the skeleton/pose reference) to 
the character described in this prompt: [character description].
[Setting]. [Style]. [Lighting]."

"The character maintains the exact body position and hand gesture from image 1.
[Character description]. [New scene/outfit/style]."
```

### Layout/composition guidance
```
"Using the composition and depth layout of image 1 as a guide,
generate: [new scene description]. Maintain the same spatial relationships
and perspective of the reference."
```

### Edge/structure preservation
```
"Preserve the architectural structure and spatial layout of image 1.
Apply new materials, lighting, and style: [description]."
```

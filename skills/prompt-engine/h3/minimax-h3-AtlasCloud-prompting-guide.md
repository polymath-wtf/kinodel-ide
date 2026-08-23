# MiniMax H3 — Prompting Guide

> **Source:** Compiled from the official fal.ai prompting guide ([fal.ai/learn/devs/minimax-h3-prompting-guide](https://fal.ai/learn/devs/minimax-h3-prompting-guide)), MiniMax official docs ([platform.minimax.io](https://platform.minimax.io/docs/guides/video-generation)), MiniMax blog ([minimax.io/blog/minimax-h3](https://www.minimax.io/blog/minimax-h3)), AtlasCloud prompt analysis ([atlascloud.ai](https://www.atlascloud.ai/blog/guides/minimax-h3-prompt-guide)), EvoLink prompt gallery ([evolink.ai](https://evolink.ai/minimax-h3-prompts)), and Morphic guide ([morphic.com](https://morphic.com/resources/how-to/minimax-h3-guide)).

---

## Table of Contents

- [Model Overview](#model-overview)
- [Capabilities](#capabilities)
- [Endpoints & Workflows](#endpoints--workflows)
- [The Six-Block Prompt Structure](#the-six-block-prompt-structure)
- [The H3 Prompt Skeleton](#the-h3-prompt-skeleton)
- [Official Prompts (12 Examples with Full Text)](#official-prompts-12-examples-with-full-text)
  - [1. Sci-Fi Mystery Trailer](#1-sci-fi-mystery-trailer)
  - [2. Glowing Kitchen Creature](#2-glowing-kitchen-creature)
  - [3. Vampire Romance Short Drama](#3-vampire-romance-short-drama)
  - [4. Futuristic Eyewear Campaign](#4-futuristic-eyewear-campaign)
  - [5. Clay Fox Canyon Leap](#5-clay-fox-canyon-leap)
  - [6. Multi-Element Scene Edit](#6-multi-element-scene-edit)
  - [7. Otome Visual Novel Transition](#7-otome-visual-novel-transition)
  - [8. Street Dance Motion Transfer](#8-street-dance-motion-transfer)
  - [9. Dialogue and Performance Replacement](#9-dialogue-and-performance-replacement)
  - [10. Wind Voice Clone](#10-wind-voice-clone)
  - [11. Magician Costume Swap](#11-magician-costume-swap)
  - [12. Luxury Headphones Showcase](#12-luxury-headphones-showcase)
- [Tutorial: "This Is Fine" Dog (Image-to-Video + Reference-to-Video)](#tutorial-this-is-fine-dog-image-to-video--reference-to-video)
- [Three More Prompt Patterns Worth Stealing](#three-more-prompt-patterns-worth-stealing)
- [Official MiniMax API Code Examples](#official-minimax-api-code-examples)
- [Prompting Best Practices](#prompting-best-practices)
- [Common Mistakes](#common-mistakes)
- [Garbled Text Fix](#garbled-text-fix)
- [Cost & Budgeting](#cost--budgeting)
- [FAQ](#faq)

---

## Model Overview

MiniMax H3 (also written Hailuo 3.0, Hailuo 03, or Hailuo 3) is MiniMax's open-weight, general-purpose multimodal video model. Instead of one model to generate, another to edit, and another to follow a reference, H3 reads text, images, video, and audio as a single context and returns a finished audio-visual clip from it.

- **Resolution:** 2K (1440p short edge, e.g. 2560×1440 for 16:9). 768p announced but not yet live.
- **Frame rate:** 24fps
- **Duration:** 5–15 seconds (varies by endpoint)
- **Audio:** Native stereo (AAC stereo at 32kHz), generated in the same pass as picture
- **Prompt length:** Up to 7,000 characters
- **Open weights:** Planned for release in the coming days (as of launch)

### Use Cases

- Brand films and commercials
- Vertical drama and dialogue (9:16)
- Title sequences and motion design
- Product and e-commerce
- Interface and game concepts
- Stylized and animated work

---

## Capabilities

| Capability | What it does | Best for |
| --- | --- | --- |
| Omni reference | Reads up to 9 images, 3 video clips, and 3 audio files as one brief | Locking a face, a motion, and a voice at once |
| Native stereo audio | Generates dialogue, effects, and room tone with the picture | Drama, ads, and title cues that need sound |
| Instruction-based editing | Changes the element you name and leaves the rest of the frame alone | Fixing a keeper without a re-roll |
| Voice cloning and transfer | Gives a character a voice taken from a reference recording | Dubbing, recasting a line, language swaps |
| Multi-shot in one clip | Several shots inside a single 5 to 15 second generation | Title sequences, shot-reverse-shot coverage |
| 2K at 24fps | A 1440-pixel short edge at the cadence film is shot at | Delivering without an upscaling pass |

### Omni Reference

One generation takes up to 9 images, 3 video clips, and 3 audio files — 12 files at most. Each one can do a different job: an image sets the character, a second sets the location, a video carries the motion or the edit rhythm, an audio file carries the voice. Reference video and audio run 2 to 15 seconds each and 15 seconds in total. Audio has to travel with at least one image or video rather than on its own.

### Native Stereo Audio

Sound is not a second step. Every generation returns stereo audio produced in the same pass as the picture. A scene comes back with the line spoken, the footsteps landing, and the room already sounding like a room. Audio is something you direct rather than something you accept.

### Instruction-Based Editing

When a clip is right except for one thing, you name that thing. Replace a subject, remove an object, swap a background, relight a scene from day to night, add an effect, change a line of dialogue: the targeted element moves and the rest of the frame holds. Several changes can travel in a single instruction.

### Voice Cloning and Transfer

A reference recording can give a character a voice they did not have, and a supplied line can replace what was said on camera with the performance adjusted to match. Paired with an identity image, that is enough to keep one character recognizable across a sequence in both face and sound.

### Framing and Finishing

Six aspect ratios: 21:9, 16:9, 4:3, 1:1, 3:4, 9:16. Plus auto mode on reference runs. First and last frame runs follow the uploaded image's ratio. Output is 1440p at 24fps, with 1440 as the short edge (a 21:9 master lands near 2976×1248).

---

## Endpoints & Workflows

Three doors. Which one you pick decides what your prompt still has to do.

| Endpoint | What you hand it | What it locks for you | Parameters worth knowing | Reach for it when | Billing |
| --- | --- | --- | --- | --- | --- |
| `minimax/h3/text-to-video` | Prompt only | Nothing. The text carries everything | duration 5–10 (default 8), resolution 2K, ratio must be set explicitly | Testing a look or a sound design before you commit | Billed per second of output |
| `minimax/h3/image-to-video` | Prompt + image (first frame), optional `end_image` | Where the clip starts, and optionally where it lands | `end_image`, duration 5–10 (default 8), ratio adaptive by default | You have artwork and you want it to move without being redrawn | Billed per second of output |
| `minimax/h3/reference-to-video` | Prompt + `refers[]` | Subject identity and style, across a scene you invent | `refers[]` mixed array, duration 5–15, ratio up to 21:9 | Same character or product, new environment | Billed per second of output |

### `refers[]` Shape

```json
"refers": [
  { "url": "https://.../subject.png", "type": "image" },
  { "url": "https://.../style-board.png" },
  { "url": "https://.../motion-ref.mp4", "type": "video" },
  { "url": "https://.../beat.mp3",       "type": "audio" }
]
```

### Four Rules for References

1. **Audio cannot ride alone.** At least one image or video has to be in the array. A beat track by itself is rejected.
2. **`type` is optional.** It is inferred from the URL, but state it anyway when the extension is ambiguous.
3. **The ceilings are real.** Up to 9 images, 3 videos and 3 audio clips, 12 files total. Reference video and audio run 2 to 15 seconds each.
4. **Give every reference a job inside the prompt text.** Official prompts open with lines like "Image 1 is the overall mood and style reference, Image 2 is the lead character reference." Without that sentence, the model has to guess which board means what.

### Spec Discrepancies (Docs vs. Reality)

| Thing | MiniMax's own documentation | What the endpoints actually accept today | What that means for your prompt |
| --- | --- | --- | --- |
| Duration | 4 to 15 seconds, integers only | text-to-video and image-to-video: 5 to 10, default 8. reference-to-video: 5 to 15, default 8 | A 15-second shot list only fits reference-to-video right now |
| Resolution | 2K | 2K is currently the only value that runs. 768p is rejected with `supported resolutions: 2K` | Write for a 1440px short side |
| Aspect ratio | Common ratios or adaptive | image-to-video and reference-to-video default to adaptive. Text-only rejects adaptive and requires: 16:9, 4:3, 1:1, 3:4, 9:16, 21:9 | On text-to-video, set ratio explicitly or the job fails |
| Mixed references | 9 images, 3 videos, 3 audio, 12 files, audio never alone | `refers[]` takes `{url, type}` with image, video or audio, at least one image or video | You can sync motion to a supplied beat, but cannot supply only the beat |
| Native audio | Stereo audio in the same pass | Every official clip: 2560×1440, 24fps, AAC stereo at 32kHz | The audio block is not decoration — it is half the deliverable |

---

## The Six-Block Prompt Structure

Every strong official prompt shares this shape. Blocks 5 and 6 are free — they cost nothing extra to generate and they are where most of the quality lives.

| Block | What goes in it | Skip it and you get |
| --- | --- | --- |
| 1. Style contract | Medium, look, texture, things that must not change about the image | The model "improves" your look into clean 3D |
| 2. Timeline / shot list | `[0s-2s]`, `[2s-4s]` beats with one event per slice | One slow push-in stretched over the whole duration |
| 3. Camera | Move type, lens, framing, what the camera does on its own | Static default, no cinematic intent |
| 4. Audio | Instruments, effects, dialogue, room tone, when each enters | The model picks a track for you |
| 5. Negative list | What must not appear: no subtitles, no watermarks, no soft dissolves | Extra on-screen text, subtitle strips, generic transitions |
| 6. Text spelling | Every word that must be readable, typed out verbatim | Letter-shaped noise where text should be |

---

## The H3 Prompt Skeleton

> Goal → ordered references → subject and identity anchors → chronological action beats → camera path → audio or dialogue direction → what must stay unchanged → final state.

Work down that list and you will not forget the two lines most prompts miss: the audio and the ending.

### Text to Video

You own everything, so spend the words on a timeline the clip can actually finish. Name the subject, order the beats, give the camera one continuous path, then describe the sound as separate layers — dialogue, ambience, music — rather than as a mood.

### First / Last Frame

The frames already carry the appearance. Describe only the change between them: the motion added, the camera move, what must be preserved, and the state you land on. Re-describing the picture is the most common way to waste this route.

### Multimodal Reference

Give every asset one job and address it by array position — Image 1 for the character, Image 2 for the location, Video 1 for the camera path, Audio 1 for the voice. Up to 9 images, 3 videos and 3 audio clips per request, and no more than 12 files in total; audio can never travel alone.

### Editing an Existing Clip

Write two lists, not one paragraph: **Change** (target → result, one line each) and **Preserve** (anything adjacent that must survive). Send the source clip as Video 1 on the reference route, trimmed to the section you actually need.

### Audio and Dialogue

Quote the lines you want spoken, verbatim. Assign a voice reference one narrow job — timbre — and write accent, emotion and pacing into the prompt separately. Keep dialogue, ambience and music from competing for the same seconds.

---

## Official Prompts (12 Examples with Full Text)

> All prompts below are preserved in their original form. Each card lists the **workflow type**, **duration**, **aspect ratio**, and **reference assets** used. Source: [EvoLink MiniMax H3 Prompts](https://evolink.ai/minimax-h3-prompts) and [MiniMax official samples](https://www.minimax.io/).

---

### 1. Sci-Fi Mystery Trailer

**Workflow:** Multimodal Reference (ref2vid) · **Duration:** 15s · **Aspect:** 16:9 · **References:** 2 images

**What you need:**
- Image 1: an atmosphere and style plate — the environment, palette and grade you want the shot to inherit.
- Image 2: the protagonist, shot large enough that the face and silhouette stay readable when the figure is small in frame.
- A title string you actually want burned in; H3 renders the text you write, so keep it short and spell it exactly.

**Full Prompt:**

```
Realistic cinematic look, high-contrast lighting, and a tight pace. Use Figure 1 as the overall atmosphere and style reference, and Figure 2 as the protagonist reference. Shot 1 — Ultra-wide establishing shot. A huge circular cosmic gateway nearly fills the frame. The person is only a tiny figure seen from behind before the gateway, positioned toward the lower right. The ground is wet and reflective, and the center of the gateway is pitch black. The camera slowly pushes forward. A large title fades in from the edge of the darkness, blurred at first and then sharp: "THE STARS WERE LISTENING". Use an extremely condensed, heavy, all-caps typeface in dark red mixed with rust red, with subtle grain and misted edges. Audio: a deep low-frequency pulse, faint metallic vibrations in the distance, and a soft hit as the text becomes sharp. → Hard cut.
```

**Why it works:**
- Each reference is given one job — Image 1 for atmosphere, Image 2 for the character — so the model never has to guess which plate owns the look.
- The shot is described as one continuous push-in with a single event (the title resolving), which is what a 15-second budget can actually hold.
- Audio is written as three specific layers (low pulse, distant metallic vibration, a hit on the text) instead of a vague 'cinematic soundtrack'.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 2. Glowing Kitchen Creature

**Workflow:** Text to Video (t2v) · **Duration:** 15s · **Aspect:** 16:9 · **References:** None

**What you need:**
- Nothing to upload — this route takes the prompt only.
- Decide duration and aspect ratio in the request, not in the prompt text.

**Full Prompt:**

```
15-second, 16:9 landscape video. Blend live-action footage of a small kitchen at dusk with hand-drawn glowing animation. The last light of sunset lingers by the window. The lived-in kitchen contains an old wooden table, a half-washed mug, a slightly fogged glass bottle, and a hanging dishcloth. Give the footage subtle one-handed smartphone shake, hesitant close-range focusing, exposure fluctuations caused by backlight, and slightly coarse noise in the shadows. It should not look carefully arranged like an advertisement; instead, it should feel like someone hurriedly captured an unbelievable event at home. Do not show huge eyes, gaping mouths, fangs, threatening or lunging movements, sudden black frames, or jump scares. Use only kitchen room tone, cloth rubbing, the soft clink of a mug, water dripping from the faucet, the camera operator's footsteps and quiet breathing, plus gentle electronic sounds and tiny calls from the hand-drawn creature.
```

**Why it works:**
- It specifies the camera's flaws — one-handed shake, hesitant focus, backlight exposure swings, noise in the shadows — which is what sells 'someone filmed this at home' over 'this is an advert'.
- It carries an explicit do-not list (no huge eyes, no fangs, no lunging, no jump scares) that keeps a cute creature from drifting into horror.
- The audio direction names each source separately: room tone, cloth, mug, tap, footsteps, breathing, plus the creature's own sounds.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 3. Vampire Romance Short Drama

**Workflow:** Multimodal Reference (ref2vid) · **Duration:** 15s · **Aspect:** 9:16 · **References:** 2 images

**What you need:**
- Image 1: both leads together, so the model reads them as one consistent casting.
- Image 2: the location plate — the castle interior, its light and its materials.
- A one-line premise and a stated emotional reversal; a 15-second hook can carry one turn, not a full episode.

**Full Prompt:**

```
Generate a 15-second, 9:16 vertical trailer segment for an international live-action vampire romance short drama. Use Figure 1 as the appearance reference for the male and female leads, and Figure 2 as the scene reference. Keep both leads' identities consistent, with a realistic live-action look and premium short-drama production quality. Story: an innocent human heroine accidentally enters a forbidden area of an old castle and awakens a sleeping aristocratic vampire. He discovers that she carries an aura connected to an ancient war, which sparks a powerful urge to control her and a dangerous fascination with her. She fears him but does not completely submit, resisting his pressure. Overall style: an international ReelShort / DramaBox vampire-romance trailer. Dark romance, dangerous attraction, fate, intense control, brooding oppression, and a striking reversal. Keep the visuals premium, restrained, and tightly paced, like the opening 15-second hook of a hit short drama. No gore, cheap horror, Halloween aesthetic, or modern street feel. Format: 9:16 vertical composition for TikTok / ReelShort / DramaBox. Use primarily medium close-ups, close-ups, and extreme close-ups, emphasizing faces, eye contact, pressure, and relationship tension within the vertical frame.
```

**Why it works:**
- Naming the genre reference (ReelShort / DramaBox trailer) transfers pacing, grade and framing conventions in a few words.
- It fixes the shot vocabulary — medium close-up, close-up, extreme close-up — which is what makes a vertical frame read as premium instead of cramped.
- The exclusion list (no gore, no cheap horror, no Halloween look, no modern street feel) removes the four ways this genre usually degrades.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 4. Futuristic Eyewear Campaign

**Workflow:** Multimodal Reference (ref2vid) · **Duration:** 15s · **Aspect:** 9:16 · **References:** 3 images

**What you need:**
- Image 1: the key visual — full-body models, wardrobe, studio light and attitude.
- Image 2: appearance detail for the two characters, so faces stay consistent through the cuts.
- Image 3: the product, shot clearly enough that its silhouette and materials survive at speed.
- A seamless studio background you are willing to keep for the whole clip.

**Full Prompt:**

```
Generate a vertical screen 9:16 high-end fashion glasses commercial, taking overall reference to the storyboard rhythm, editing speed, white studio texture and cool fashion atmosphere of the given video. The picture is a minimalist white booth, a seamless white background, a strong sense of high-end advertising, and a clean, simple, handsome, avant-garde, international first-line fashion blockbuster texture. Key visual character reference picture 1, two full-body female models, one black female model and one European and American model, maintain their high-end clothing, body posture, white studio light and shadow, fashion show temperament and overall cool attitude. Both of them wear futuristic high-end glasses. The design of the glasses refers to Figure 3, emphasizing the covered curved surface, sharp geometric cat-eye/goggle hybrid outline, mirror reflection, streamlined temples, and the texture of high-end fashion accessories. Please refer to Figure 2 for the appearance details of the two characters.
```

**Why it works:**
- Three references with three explicit jobs is the pattern the reference route is built for; ambiguity is what makes multi-image prompts collapse.
- The product is described by its geometry — wrap curvature, cat-eye/goggle hybrid outline, mirrored surface, streamlined temples — not just by its name.
- A single-material white studio removes background variance, so the model spends its budget on the product and the performers.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 5. Clay Fox Canyon Leap

**Workflow:** First / Last Frame (i2v) · **Duration:** 10s · **Aspect:** 16:9 · **References:** 1 image (start frame)

**What you need:**
- A start image that already carries the style — here the claymation fox and its material.
- One action you want to happen. Not three.

**Full Prompt:**

```
Claymation style. A sprinting fox reaches the edge of a cliff and launches without hesitation, making a dramatically tense, heroic slow-motion leap across a vast lava canyon. While the fox is airborne, the camera rushes at high speed beneath its belly in a sweeping dynamic move, fully revealing the terrifying depth of the chasm and the fox's clay body at maximum extension in midair.
```

**Why it works:**
- The prompt describes change, not the picture. The start frame already holds the appearance, so every word buys motion.
- The camera has its own instruction — a high-speed sweep beneath the fox's belly — which turns a jump into a shot.
- Naming the peak moment ('maximum extension in midair') gives the model a target pose to build the timing around.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 6. Multi-Element Scene Edit

**Workflow:** Multimodal Reference (ref2vid — editing) · **Duration:** 10s · **Aspect:** 16:9 · **References:** 1 video

**What you need:**
- Video 1: the clip to edit, 2–15 seconds, MP4 or MOV, H.264 or H.265, up to 50 MB.
- A list of edits, each naming what to change and what it becomes.

**Full Prompt:**

```
Replace the newspaper in the reference video with a green-covered book; change the chair the character is sitting on to a red sofa; remove the sunglasses worn by the character to retain a clear face; remove the car burning effect to keep the vehicle in a normal state; change the photo the character takes out of his arms to a small black book; and add a tree on the left side of the screen
```

**Why it works:**
- Every instruction is a pair — target plus result — so nothing is left to interpretation ('the newspaper' becomes 'a green-covered book').
- Removals state the intended end state ('remove the sunglasses to retain a clear face'), which stops the model from leaving a hole where the object was.
- It carries no scene description whatsoever, so the model treats the source clip as ground truth and only applies the deltas.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 7. Otome Visual Novel Transition

**Workflow:** First / Last Frame (i2v) · **Duration:** 15s · **Aspect:** 16:9 · **References:** 2 images (start + end frame)

**What you need:**
- Image 1: the opening frame, complete with its UI state.
- Image 2: the exact closing frame you want to land on.
- A one-line description of the emotional change between the two states.

**Full Prompt:**

```
Use the first image as the opening frame and the second image as the exact final frame to generate an otome visual-novel interface transition. Overall feel: a premium Chinese otome romance-interaction interface capturing an intimate moment before and after a performance. Transition naturally from "choose to watch his performance" to "Han Xu is drawn in by the heroine's words and reacts with intrigued interest." UI text, choices, and dialogue boxes should appear with refined otome-game presentation. Keep the transition silky smooth and the emotion suggestive yet restrained.
```

**Why it works:**
- Both endpoints are locked, so the model solves interpolation instead of composition — the most reliable way to get a predictable shot.
- The prompt names the emotional transition ('choose to watch his performance' → 'drawn in and intrigued') rather than listing frames, so the performance carries the cut.
- It states the interface elements should animate in the genre's own idiom, which keeps the UI from being redrawn.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 8. Street Dance Motion Transfer

**Workflow:** Multimodal Reference (ref2vid) · **Duration:** 10s · **Aspect:** 16:9 · **References:** 2 images + 1 video

**What you need:**
- Image 1 and Image 2: the two characters, one clean full-body reference each.
- Video 1: the movement to copy, 2–15 seconds, with the performer fully in frame.

**Full Prompt:**

```
Have the characters perform street dance following the movements in Video 1. Use Figure 1 and Figure 2 as the character references.
```

**Why it works:**
- The prompt is short because the references carry the information — the video owns the motion, the images own the identities.
- Each asset is addressed by its array position, so there is no ambiguity about which reference supplies what.
- It asks for nothing else. No lighting, no camera, no style — every extra instruction would compete with the motion it is trying to copy.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 9. Dialogue and Performance Replacement

**Workflow:** Multimodal Reference (ref2vid — editing) · **Duration:** 10s · **Aspect:** 16:9 · **References:** 1 video + 1 audio

**What you need:**
- Video 1: the clip containing the line to replace.
- Audio 1: the replacement line, WAV or MP3, up to 15 MB and 15 seconds.
- Both lines written out verbatim in the prompt.

**Full Prompt:**

```
Replace the girl's line in Video 1, "We can't be together. It's not that we don't love each other; we truly can't make it to the end," with the line from Audio 1: "Don't go, okay? This time, let's not let go of each other." Slightly adjust the corresponding performance.
```

**Why it works:**
- Quoting the outgoing line tells the model exactly which span of the clip to operate on, instead of 'the dialogue near the middle'.
- Quoting the incoming line means the lip sync has a target rather than being inferred from the audio alone.
- 'Slightly adjust the corresponding performance' grants a bounded licence to change the acting — bounded, so the rest of the take survives.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 10. Wind Voice Clone

**Workflow:** Multimodal Reference (ref2vid) · **Duration:** 10s · **Aspect:** 16:9 · **References:** 1 video + 1 audio

**What you need:**
- Video 1: the character who will deliver the line.
- Audio 1: a clean sample of the target voice, 2–15 seconds, ideally without music underneath.
- The exact line of dialogue, written out.

**Full Prompt:**

```
Character dialogue: "Follow the wind, live free. Leave worries behind, enjoy the moment." Use Audio 1 as the voice-timbre reference.
```

**Why it works:**
- The dialogue is quoted rather than paraphrased, so timing and lip sync have something concrete to lock onto.
- Audio 1 is assigned one narrow job — voice timbre — instead of being handed over as a general 'soundtrack'.
- Nothing else is specified, so the reference clip keeps full control of framing and performance.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 11. Magician Costume Swap

**Workflow:** First / Last Frame (i2v) · **Duration:** 7s · **Aspect:** 16:9 · **References:** 1 image (start frame)

**What you need:**
- A start image holding both performers, their costumes and the stage.
- A clear before/after state for whatever swaps.

**Full Prompt:**

```
Two magicians stand onstage facing the audience and perform a "swap" trick. They wave their wands at the same time, and a cloud of smoke rises. When it clears, their suit colors have switched: the person on the left wears a white suit, and the person on the right now wears a black suit, while both magicians' glove colors remain unchanged. They bow to thank the audience. The red curtain behind them closes, transitioning from deep red to deep blue.
```

**Why it works:**
- The swap is masked by an event — the smoke cloud — giving the model a legitimate moment to make the change instead of morphing on camera.
- It names what must not change (the glove colors) next to what must, which is exactly how you keep an edit from spreading.
- The shot ends on a defined final state: the bow, the curtain closing, the color landing on deep blue.

**Source:** [Official MiniMax sample](https://www.minimax.io/)

---

### 12. Luxury Headphones Showcase

**Workflow:** Text to Video (t2v) · **Duration:** 15s · **Aspect:** 16:9 · **References:** None

**What you need:**
- Nothing to upload — text-to-video takes the prompt alone.
- A product you can describe by material and mechanism, not just by name.

**Full Prompt:**

```
Create a 15-second luxury cinematic product showcase for premium wireless over-ear headphones. 0–4s: Begin with an extreme macro tracking shot moving across the soft memory-foam ear cushion, fine fabric texture, brushed-metal hinge and precision-machined controls. A narrow light band travels across the surface, revealing realistic materials against a deep black studio background. 4–8s: Pull back into a three-quarter hero view. The headphones rotate slowly above a glossy reflective pedestal. The ear cups pivot naturally while the adjustable headband extends slightly, demonstrating flexible construction and comfort. Maintain exact symmetry, stable geometry and consistent proportions. 8–12s: Transition into an elegant exploded-view reveal. The ear cushion, acoustic driver, internal sound chamber, control ring and outer shell separate smoothly in perfect alignment. Subtle luminous sound waves pulse outward from the driver while the camera performs a restrained side orbit. 12–15s: Every component reconnects seamlessly. The headphones settle into a centered front-facing hero composition as soft rim lighting defines the silhouette. Complete a gentle dolly-in toward the ear cups. Premium technology-commercial finish, controlled reflections, realistic shadows, shallow depth of field, crisp surface detail, stable product shape, no hands, no distortion, no onscreen text.
```

**Why it works:**
- Time is split into 0–4s, 4–8s, 8–12s and 12–15s, so the model gets a shot list instead of a wish list.
- Each block moves the camera differently — macro track, pull back, side orbit, dolly in — which is what makes the clip read as edited rather than drifting.
- The closing line is a list of prohibitions (no hands, no distortion, no onscreen text) that cover the three ways product renders usually fail.

**Source:** [Community sample — @LudovicCreator on X](https://x.com/LudovicCreator/status/2082783319075291312)

---

## Tutorial: "This Is Fine" Dog (Image-to-Video + Reference-to-Video)

> Source: [AtlasCloud — MiniMax H3 Prompt Guide](https://www.atlascloud.ai/blog/guides/minimax-h3-prompt-guide). Original comic: [KC Green's Gunshow #648](https://gunshowcomic.com/comics/20130109.png), published 9 January 2013.

### Step 1: Prepare the Frames

The strip is six panels, two columns by three rows, 600×887. Only panel 2 (the "THIS IS FINE." panel) and panel 6 (the melting dog) are needed.

```bash
curl -L -o gunshow-648.png https://gunshowcomic.com/comics/20130109.png
# 600x887, 6 panels, 2 cols x 3 rows

# crop panel 2 (the "THIS IS FINE." panel): x 302-584, y 20-293
# crop panel 6 (the melting dog): x 302-584, y 595-868
# upscale each 4x with Lanczos -> 1128x1092
```

> Do not ask an image model to draw "a dog that looks like This Is Fine." The watercolour wash, the wobbly hand lettering and the paper grain are the entire contract.

### Step 2: Image-to-Video with `end_image`

**Workflow:** Image-to-Video (i2v) · **Duration:** 10s · **Resolution:** 2K · **Ratio:** 1:1 · **Image:** panel 2 (first frame) · **End image:** panel 6

**Full Prompt:**

```
Hand-painted 2D webcomic panel, brought to life. Keep the original watercolour
texture, visible ink outlines, off-register paper grain and flat comic palette
in every frame. Do not smooth, do not re-render in 3D, do not clean up the
linework, do not add new objects, do not add new text.

[0s-3s] Almost nothing moves. The dog sits perfectly still, holding the mug,
eyes fixed forward. Only the flames behind him move: slow orange licks climbing
the wall, one ember drifting up. The speech bubble reading "THIS IS FINE."
stays exactly where it is, fully legible, unchanged, hand-lettered.

[3s-6s] The dog lifts the mug and takes one small, calm sip. The speech bubble
fades out after the sip. The fire brightens. The wall behind him begins to warp
with heat. His hat starts to smoulder at the brim.

[6s-8.5s] The heat reaches him. His ears sag, his outline softens and begins to
run downward like wet paint. He still does not move his eyes. The mug stays in
his paw.

[8.5s-10s] Full melt. The face distorts, one eye slides, teeth bared in a fixed
grin, the fur runs red and orange. He holds the pose. Hold on the final frame
for the last half second.

Camera: locked off, single static wide shot, no push in, no handheld, no cuts.
The frame never moves. This is one continuous take inside one comic panel.

Audio: room-tone of an interior fire throughout - low crackle, occasional pop of
burning wood, a faint structural creak. At 3s, one ceramic mug touching teeth and
a small swallow. A calm, flat, unbothered male voice says exactly: "This is fine."
- deadpan, no emotion, slightly too relaxed. From 6s the crackle grows louder and
the room tone thickens; the last 2 seconds add a low sub-bass swell. No music,
no laugh track, no sound effects that are not in this list.

Do not add subtitles. Do not add a watermark. Do not spell any word other than
the words already in the image. Do not change "THIS IS FINE." Do not cut away.
```

### Step 3: QA the Output

Four checks, each testing a different block of the prompt:

1. Is THIS IS FINE. in the bubble still legible and still spelled right? (tests block 5 — text spelling)
2. Did the linework survive, or did something "improve" it into clean 3D? (tests block 1 — style contract)
3. Does the audio contain only the sounds you listed? Probe the container: `ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate -of default=noprint_wrappers=1 output.mp4`
4. Does the final frame land on panel 6's pose? (tests `end_image`)

### Step 4: Move the Dog Somewhere New (Reference-to-Video)

**Workflow:** Reference-to-Video (ref2vid) · **Duration:** 8s · **Resolution:** 2K · **Ratio:** 16:9 · **refers[]:** panel 2 as image

**Full Prompt:**

```
Image 1 is the character and art-style reference: keep this exact hand-painted
2D webcomic look, the same watercolour texture, the same ink outline weight, the
same dog, the same little hat, the same mug. Do not redraw him in 3D, do not
change his proportions, do not clean up the linework.

Put him in a different room and keep his composure. A cramped open-plan office at
night, fluorescent tubes flickering, a wall of monitors all showing a red error
state, printer paper drifting down through the frame, a small electrical fire in
the corner. He sits in an office chair at the centre of the frame, mug in paw,
looking straight at the camera, completely relaxed.

Camera: locked off, static wide shot. No push in, no cuts.

Audio: fluorescent hum, printer grinding, a repeating soft alarm chirp every two
seconds, distant electrical crackle, one calm sip at 4s. No music. No voice.

Do not add any on-screen text. Do not add subtitles. Do not add other characters.
```

> The transferable rule: `refers[]` carries identity and style, the text carries the scene. That split is the whole trick to character consistency.

---

## Three More Prompt Patterns Worth Stealing

> Source: [AtlasCloud — MiniMax H3 Prompt Guide](https://www.atlascloud.ai/blog/guides/minimax-h3-prompt-guide)

### Pattern 1: The Motion Poster

The whole prompt is two lines: keep the gallery white frame, the inner frame, the red-white-black palette, the 3D-figure feel and the layout structure unchanged, and put a nimble sound effect under the text entrance.

**Rule:** Name the parts that must survive. "Keep the layout" is not a style note, it is a constraint, and the model treats it as one.

### Pattern 2: The Interface Demo

The prompt asks for a downward page scroll, a hover state, a strong scale-up and a colour inversion. Four verbs. It never says "modern" or "sleek."

**Rule:** Interactions are actions, so write them as actions. The thing that makes it read as a real page came from the verbs.

### Pattern 3: Live Action + Hand-Drawn, Held Together by Refusals

A phone-shot evening kitchen with small glowing hand-drawn creatures. The reason it stays charming instead of turning into a horror short is a list of bans: no giant eyes, no split mouths, no fangs, no threatening posture, no lunging, no sudden cut to black, no jump scares.

**Rule:** The negative list is the primary style control, not a patch. It is also where you encode taste.

### Bonus: The Noir Title Sequence (Official MiniMax)

> This is a chunk of the official prompt behind MiniMax's noir title sequence, translated from the Chinese original, running maybe a third of its full length. Five style reference boards were handed to H3 alongside this prompt.

```
Generate a 15-second 16:9 light-suspense crime film title sequence. Overall style references the visual language of these images: retro Japanese-anime title cards, hard-edged silhouettes, comic collage, asymmetric split screen, strong geometric colour blocks, English credit titles, a little Japanese katakana decoration, jazz-crime feel. The mood is 60% suspense, 40% jazz: mysterious, cool, nimble, urban-crime, not horror, not heavy, and do not turn it into a cheerful jazz MV.

[...] English credits must be clearly legible [...] Do not add Chinese, do not produce garbled text, do not misspell the English. Rule for the whole piece: every English credit and job title appears exactly once. Do not repeat a job title, do not repeat a name, do not give one person multiple titles.

Transitions must be varied: circular vinyl-record mask, vertical car-door wipe, a figure's long shadow sweeping the screen, red-line cut, giant English letter mask, split-screen frame recomposition, hard colour-block cut, panels pasted in block by block. All transitions land on the drum hits: crisp, suspenseful, nimble, comic-collage. No soft dissolves, no fluid transitions.

BGM: original 15-second title music, 60% suspense, 40% jazz. Built from a sustained bass tone, tense pizzicato strings, cold synth pulses, kick drum, sparse jazz brushes, a walking bass fragment, short baritone sax phrases and brief brass stabs. First 2 seconds establish suspense with low frequencies and hi-hat, at 3 seconds the low drums enter, at 6 seconds the jazz bass groove joins, at 10 seconds a short sax/brass riff appears, the last 2 seconds lock it with a tense chord and drum hit.
```

**Result:** MIDNIGHT LINE, STARRING, MAYA CROSS, REN KATO, LENA WARD, DIRECTED BY NOAH VOSS — spelled correctly, no job title used twice, katakana decoration sitting where it was asked to sit.

### Bonus: The Game UI Demo (Official MiniMax)

The official game-UI prompt is built out of six timestamped beats:

```
[0s-2s] menu
[2s-4s] right-arm panel
[4s-7s] armament grid
[7s-8.5s] confirm
[8.5s-10s] loading bar
[10s-15s] the world loads in
```

The finished clip hits all six, in order, on time. Text spelled out in the prompt (RIGHT ARM EQUIPMENT, PHANTOM GRIP, CHRONOS CLAW) renders cleanly. Text only gestured at generically ("HUD elements") renders as letter-shaped noise (ETR METNO CITFEP).

---

## Official MiniMax API Code Examples

> Source: [MiniMax API Docs — Video Generation](https://platform.minimax.io/docs/guides/video-generation)

### Workflow

1. **Create a generation task:** Submit a video generation request and receive a task ID (`task_id`).
2. **Check task status:** Poll the task status using the `task_id`. Once successful, the response directly returns the video download URL (`content.url`).
3. **Retrieve video file:** Download the video from `content.url` and save it locally.

### Full Python Example (All 4 Modes)

```python
import os
import time
import requests

api_key = os.environ["MINIMAX_API_KEY"]
headers = {"Authorization": f"Bearer {api_key}"}
BASE_URL = "https://api.minimax.io"
MODEL = "MiniMax-H3"

# --- Step 1: Create a video generation task ---

def invoke_text_to_video() -> str:
    """(Mode 1) Text-to-video (t2va). For t2va, ratio is required and cannot be 'adaptive'."""
    url = f"{BASE_URL}/v2/video_generation"
    payload = {
        "model": MODEL,
        "content": [
            {"type": "text", "text": "A tiktok dancer is dancing on a drone, doing flips and tricks."},
        ],
        "duration": 5,
        "resolution": "2K",
        "ratio": "16:9",
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["task_id"]

def invoke_image_to_video() -> str:
    """(Mode 2) Image-to-video (i2va) using a first-frame image and text."""
    url = f"{BASE_URL}/v2/video_generation"
    payload = {
        "model": MODEL,
        "content": [
            {"type": "text", "text": "Contemporary dance, the people in the picture are performing contemporary dance."},
            {"type": "image_url", "image_url": {"url": "https://filecdn.minimax.chat/public/85c96368-6ead-4eae-af9c-116be878eac3.png"}, "role": "first_frame"},
        ],
        "duration": 5,
        "resolution": "2K",
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["task_id"]

def invoke_start_end_to_video() -> str:
    """(Mode 3) First-frame + last-frame image + text."""
    url = f"{BASE_URL}/v2/video_generation"
    payload = {
        "model": MODEL,
        "content": [
            {"type": "text", "text": "A little girl grows up."},
            {"type": "image_url", "image_url": {"url": "https://filecdn.minimax.chat/public/fe9d04da-f60e-444d-a2e0-18ae743add33.jpeg"}, "role": "first_frame"},
            {"type": "image_url", "image_url": {"url": "https://filecdn.minimax.chat/public/97b7cd08-764e-4b8b-a7bf-87a0bd898575.jpeg"}, "role": "last_frame"},
        ],
        "duration": 5,
        "resolution": "2K",
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["task_id"]

def invoke_reference_to_video() -> str:
    """(Mode 4) Reference-to-video (r2va): combine reference images / videos / audio."""
    url = f"{BASE_URL}/v2/video_generation"
    payload = {
        "model": MODEL,
        "content": [
            {"type": "text", "text": "On an overcast day, in an ancient cobbled alleyway, the model walks and adjusts a vintage beret with a smile; natural lighting and cinematic colors."},
            {"type": "image_url", "image_url": {"url": "https://filecdn.minimax.chat/public/54be8fbe-5694-4422-9c95-99cf785eb90e.PNG"}, "role": "reference_image"},
        ],
        "duration": 5,
        "resolution": "2K",
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["task_id"]

# --- Step 2: Poll task status ---

def query_task_status(task_id: str) -> str:
    """Poll task status by task_id and return the video download URL on success."""
    url = f"{BASE_URL}/v2/query/video_generation/{task_id}"
    while True:
        time.sleep(10)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        task = response.json()["task"]
        status = task["status"]
        print(f"Current task status: {status}")
        if status == "succeeded":
            return task["content"]["url"]
        if status in ("failed", "cancelled", "expired"):
            raise Exception(f"Video generation did not succeed: status={status}, error={task.get('error')}")

# --- Step 3: Download and save the video file ---

def fetch_video(download_url: str):
    """Download the video and save it locally."""
    with open("output.mp4", "wb") as f:
        video_response = requests.get(download_url)
        video_response.raise_for_status()
        f.write(video_response.content)
    print("Video successfully saved as output.mp4")

# --- Main process ---

if __name__ == "__main__":
    task_id = invoke_text_to_video()       # Mode 1: Text-to-Video
    # task_id = invoke_image_to_video()     # Mode 2: Image-to-Video
    # task_id = invoke_start_end_to_video() # Mode 3: First-and-Last-Frame Video
    # task_id = invoke_reference_to_video() # Mode 4: Reference-to-Video
    print(f"Video generation task submitted, Task ID: {task_id}")
    download_url = query_task_status(task_id)
    print(f"Task succeeded, video URL: {download_url}")
    fetch_video(download_url)
```

### Input Requirements

| Item | Requirement |
| --- | --- |
| First/last-frame entry | Images: 0, 1, or 2; width/height in [256, 5760]; aspect ratio (width/height) in 2:5 – 5:2. With no image input, becomes Text-to-Video. |
| Reference entry | Images: ≤ 9; width/height in [256, 5760]. Videos: ≤ 3 clips; per-clip duration [2, 15]s; total duration ≤ 15s; width/height in [256, 5760]; aspect ratio in 2:5 – 5:2. Audio: ≤ 3 clips; must be accompanied by an image or video input (cannot be sent alone); per-clip duration [2, 15]s. |
| Any image, video, or audio input | Must be accessible via public URL. |

---

## Prompting Best Practices

- **Give every reference a job.** "Image 1 sets the mood and film texture, Image 2 is the talent, Image 3 is the product" beats attaching four images and hoping.
- **Write the beats with timings.** Blocking the clip as 0 to 2 seconds, 2 to 5 seconds, and so on gives the model an order to follow across all 15.
- **Say what must not change.** Naming the locked elements — a mask that stays fixed, a face that keeps its hair and wardrobe — is what stops drift mid-clip.
- **Write the negatives explicitly.** No subtitles, no watermarks, no modern clothing, no soft dissolves: constraints are followed when they are stated.
- **Direct the sound as its own track.** Name the instruments, the specific effects, and where the cue lands, since the audio is generated with the picture either way.
- **Name the transitions.** A wipe, a hard cut, a whip pan, a match cut on a shape: listing them keeps an edit rhythmic instead of generically smooth.
- **Describe the capture, not only the scene.** Handheld phone tremor, exposure breathing, delayed autofocus, and grain are what separate a look that feels filmed from one that feels rendered.
- **Spec the type animation.** Give text an entrance, a duration, and a ban list, and titles stop spinning and bouncing.
- **Edit by naming the target.** For a fix, say what changes and what stays. Re-rolling the whole shot risks losing the take you liked.
- **Budget the references.** Twelve files is the ceiling, video and audio references cap at 15 seconds each in total, and audio only counts if an image or video rides with it.

---

## Common Mistakes

- Attaching references without saying what each one is for, so the model has to guess which image drives the scene.
- Describing a frozen frame instead of an action that runs the length of the clip.
- Leaving the audio unwritten, then treating the sound that comes back as a fault of the model.
- Sending an audio reference on its own, which is rejected unless an image or video accompanies it.
- Re-rolling a whole shot to fix one object, when an edit instruction would have kept the rest of the take.

---

## Garbled Text Fix

Three things go wrong, and they are all absences rather than mistakes:

1. **No timeline.** You asked for ten seconds and described one moment, so you get one slow push-in stretched over ten seconds. The model had nothing to do at second seven.
2. **No audio block.** Sound is generated in the same pass as picture. If you say nothing, the model still ships you a track. It just picks one.
3. **No negative list.** Left alone, the model reaches for soft dissolves, invents extra on-screen text, and adds a subtitle strip nobody asked for.

**The garbled text fix:** If a word needs to be readable, type the word. Then add a negative line: `do not misspell, do not add other text, do not add subtitles`.

- Strings that appear literally in the prompt render cleanly.
- Anything you gesture at generically ("HUD elements," "some labels") comes back as letter-shaped texture.

---

## Cost & Budgeting

H3 is billed per second of generated video, by resolution.

- **Iterate at 5 seconds, deliver at 10 or 15.** Composition, palette and sound design all resolve at 5. Nothing about a locked-off shot needs the full duration to tell you it is wrong.
- **`end_image` is a cost tool, not just a creative one.** Most reruns happen because the ending drifted. Pinning the last frame removes that failure mode before you pay for it.
- **Negative lists and spelled-out text are free.** They add characters to a prompt that is billed by the second, not the token. Use them heavily.
- **Match duration to the endpoint before you write.** Building a 15-second shot list and then discovering your endpoint caps at 10 costs you a rewrite, not just a rerun.
- **768p tier:** Listed in pricing but currently rejected outright. Budget as if every second is a 2K second.

---

## FAQ

### Does MiniMax H3 generate audio, or do I add it afterwards?

Same pass. Picture and sound come out together, which is exactly why audio has to be written into the prompt body rather than bolted on later. Give it its own `Audio:` block and state when each sound enters. Every official clip probed came back as AAC stereo at 32kHz alongside a 2560×1440, 24fps video stream.

### How long can a MiniMax H3 prompt be?

Up to 7,000 characters, per MiniMax's documentation. In practice the official examples span a wide range, with a median around 130 Chinese characters and the two longest at 657 and 858. Short prompts work fine when a reference image is doing the describing. If you have no references, expect to write a shot list.

### Why does text come out garbled in my MiniMax H3 videos?

Because you did not type it. Strings that appear literally in the prompt render cleanly; anything you gesture at generically ("HUD elements," "some labels") comes back as letter-shaped texture. Spell out every word that has to be readable, then add `do not misspell, do not add other text, do not add subtitles`.

### How many reference images, videos and audio clips can one MiniMax H3 prompt use?

Nine images, three videos and three audio clips, twelve files in total, with reference video and audio between 2 and 15 seconds each. Audio cannot be the only reference. Note that model capability and what a given endpoint exposes are two different things, so check the model page for the current input list.

### Can a MiniMax H3 prompt control how the clip ends, not just how it starts?

Yes, on image-to-video, via the optional `end_image` parameter. Give it a first frame and a last frame and the clip interpolates between them. Keep the two images at similar aspect ratios or the transition gets ugly.

### What durations and resolutions can I actually get right now?

2K, and only 2K. A 768p job is currently rejected with `supported resolutions: 2K`, despite 768p appearing in the pricing table. Duration differs by endpoint: text-to-video and image-to-video accept 5 to 10 seconds with a default of 8, while reference-to-video accepts 5 to 15. On text-only generation the API rejects `adaptive` and requires an explicit ratio.

### Is MiniMax H3 the same thing as Hailuo 3?

Yes. MiniMax H3 is also known as Hailuo 3, Hailuo 3.0 or Hailuo 03.

### Why do the prompts say Figure 1 or Video 1?

The reference route resolves assets by their position in the `image_urls`, `video_urls` and `audio_urls` arrays. Referring to "Image 1" or "Video 1" in the prompt is how you assign a job to a specific asset. The `@image1` syntax is not part of this API contract.

---

## Sources

- [fal.ai — MiniMax H3 Prompting Guide](https://fal.ai/learn/devs/minimax-h3-prompting-guide)
- [MiniMax — Official Blog Post](https://www.minimax.io/blog/minimax-h3)
- [MiniMax — API Docs: Video Generation](https://platform.minimax.io/docs/guides/video-generation)
- [MiniMax — H3 Feature Highlights](https://platform.minimax.io/docs/guides/video-prompt)
- [AtlasCloud — MiniMax H3 Prompt Guide: All 45 Official Prompts](https://www.atlascloud.ai/blog/guides/minimax-h3-prompt-guide)
- [EvoLink — MiniMax H3 Prompts and Video Examples](https://evolink.ai/minimax-h3-prompts)
- [Morphic — How to use MiniMax H3](https://morphic.com/resources/how-to/minimax-h3-guide)

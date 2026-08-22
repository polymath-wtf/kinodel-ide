# Craft Subjects for Kinodel Chunks

Craft-Kinodel uses five subjects for every reusable chunk: `context`, `references`, `action`, `focus`, `timing`.

This borrows the aerodynamic shape of Gemini Omni CRAFT, but the semantics are chunk/RAG-oriented, not video-prompt-oriented.

## 1. context

Defines what the chunk is and how canonical it is.

Required fields:

- `summary` — compact human-readable meaning.
- `chunk_role` — `canon`, `continuity_memory`, `identity_library`, `music_inspiration`, `style_inspiration`, `archive_memory`, etc.
- `scope` — global/project/season/episode/stage scope.
- `status` — for episodes use `planned -> active -> completed -> archived`; for reusable libraries use draft/approved/archived as appropriate.
- `source_artifacts` — paths to the artifacts/media that produced this chunk.
- `canon_policy` — whether downstream agents may treat it as fact, inspiration, or only a style ref.

Rules:

- Canon chunks must come from approved/completed artifacts.
- Inspiration chunks must say they are not canon.
- Never put provider logs or queue IDs here.

## 2. references

The media/doc refs that downstream agents will select from.

Each ref must have:

```json
{
  "handle": "@image1",
  "path": "refs/front.png",
  "modality": "image",
  "role": "front_closeup identity reference",
  "take": ["face structure", "hair silhouette"],
  "ignore": ["background", "temporary lighting"],
  "use_cases": ["wardrobe main frame", "filmmaker identity lock"],
  "priority": "P1",
  "consumers": ["wardrobe-kinodel", "storyboard-kinodel", "filmmaker-kinodel"]
}
```

Priority convention:

- `P1` — identity/canon-critical refs.
- `P2` — style, wardrobe, character-state, important music vibe.
- `P3` — motion/camera/audio sync references.
- `P4` — supporting environment/object refs.
- `P5` — optional inspiration or archive refs.

## 3. action

What consumers should do with the chunk.

Examples:

- Avatar: preserve identity; choose pose/emotion refs; avoid face/outfit drift.
- Music: inspire new lyrics/music prompt; use vibe/energy/instrumentation; do not clone melody.
- Season: preserve season canon; provide episode constraints and payoff strategy.
- Episode: continue from ending state; respect continuity facts and open threads.
- Cinema: reuse as inspiration/few-shot style memory, not canon for a new project.

Action should be written for agents, not for a video model.

## 4. focus

The semantic priority. Focus tells downstream agents what must not drift.

Common fields:

```json
{
  "primary": "identity_lock | continuity | style_dna | music_energy | emotional_state | visual_anchor",
  "must_preserve": [],
  "must_not_drift": [],
  "conflict_resolution": "approved canon beats inspiration refs"
}
```

Focus is not camera language. Camera belongs to downstream render/prompt planning.

## 5. timing

Source-derived time/sequence structure.

Allowed timing forms:

- Music sections: intro/verse/chorus/drop/bridge/outro.
- Episode order: episode_01 → episode_02 → payoff later.
- Act order: act_01..act_N if already in story artifact.
- Video beat map: only if imported from a real source video/ALM/render result.
- Empty with reason: `{"mode": "not_applicable", "reason": "static identity chunk"}`.

Forbidden:

- invented second-by-second video timings;
- provider-specific duration defaults;
- hidden external UI state.

## retrieval_text

Every chunk should also produce a compact `retrieval_text`. This is a retrieval projection, not an agent instruction and not a dump of the full chunk.

```text
title: {title} | text: {chunk_type}; {context.summary}; status: {status}; canon_policy: {canon_policy}; focus: {focus.primary}; preserve: {must_preserve}; avoid: {must_not_drift}; refs: {role list}; timing/search tags: {source-derived timing summary}
```

Keep it stable. Target 150–600 tokens; warn above 600; reject above 1200 unless explicitly overridden. Changing retrieval formatting requires index rebuild.

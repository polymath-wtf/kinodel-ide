# Creative Chunks

Status: **Domain contracts, introduced with their pipelines**

A creative chunk is approved reusable memory, not an embedding record and not a process archive. Craft produces semantic content; validators and index services handle schema, storage, embeddings, and retrieval projections.

## Shared Rules

- source only approved artifact revisions and selected assets;
- distinguish canon, inspiration, plan, and completed fact;
- keep exact provenance and rights constraints;
- store asset references, never base64 media;
- exclude prompts/logs/provider payloads unless the prompt itself is approved reusable craft;
- use a new immutable revision for updates;
- index is derived and deletable;
- load direct selected chunks before semantic search.

## Types

### `CharacterChunkV1`

Identity, appearance, wardrobe anchors, voice/motion references, continuity constraints, approved image/video/audio assets, and optional LoRA reference metadata. Provider-specific activation belongs to adapters/runtime settings.

Consumers: Wardrobe, Storyboard, Filmmaker, Season, Episode.

### `CinemaChunkV1`

Approved story/hook, visual language, selected main/story frames, clips/final video, and a concise account of what should carry forward.

Consumers: future cinematic projects, style research, Muse/Season as explicitly selected inspiration.

### `MusicChunkV1`

Rights-aware inspiration memory: audio asset, analysis summary, genre/mood/instrumentation/vocal attributes, section/energy map, and explicit `take`/`ignore` rules.

Muse may take abstract attributes. It must ignore exact melody, copyrighted lyrics, voice identity, and artist cloning.

### `SeasonChunkV1`

Approved season authority: premise, story engine, character and relationship arcs, canon, production defaults, ordered episode blueprints/statuses, and approved anchors.

### `EpisodeChunkV1`

Continuity memory: compact recap, exact ending state, character/relationship deltas, wardrobe/location/prop/injury continuity, open threads, required payoffs, approved anchors, and final episode asset.

Planned and completed episode chunks are distinct revisions/statuses. Future plans never become past facts.

### `MusicVideoChunkV1`

Approved song selection, timing map, visual concept, selected frames/clips, final video, and rights-safe reusable lessons. It remains separate from a generic `MusicChunkV1` because project result and musical inspiration have different semantics.

### Future Types

Product, world/location, voice, and other chunks are added only when a real pipeline has a stable owner and consumer. Do not create empty schemas in anticipation.

## Attention And Token Cost

Gemini embedding dimensions do not make injected text shorter. Context cost is controlled by:

- selecting fewer, more relevant chunks;
- compact agent-specific projections;
- direct references instead of broad retrieval;
- summaries linked to full canonical artifacts;
- measured prompt-token budgets.

For Episode, pass the approved season summary, target episode, exact previous ending, and only relevant neighbors. Do not inject the whole series history or pretend a 256-dimensional vector makes that history cheaper to read.

# Creative Chunks

Status: **Domain contracts, introduced with their pipelines**

A creative chunk is approved reusable production memory. It is a typed artifact with exact provenance, not an embedding row, arbitrary Markdown note, chat summary, or process archive.

## Shared Contract

Artifact infrastructure owns immutable ID, schema/version, digest, project scope, body URI, source provenance, and creation operation. A chunk body adds only domain meaning rather than repeating one universal legacy envelope.

Every chunk records or references:

- one stable logical subject such as a character, season, episode, film, or music reference;
- its authority role: `canon`, `plan`, `completed_fact`, or `inspiration`;
- exact approved source artifact revisions and separately labelled validated supporting provenance;
- approved media handles with rights and intended use;
- facts and continuity constraints needed by declared consumers;
- the prior chunk revision it supersedes when applicable.

Project DB `chunk_bindings` map each reusable logical subject to its active approved artifact revision, status, and optimistic revision. Supersede and archive retain immutable history; archive excludes new normal selection. Existing executions retain exact pinned revisions on ordinary supersede/archive while retained data and rights permit use. Rights withdrawal immediately blocks use, including already prepared selections. Purge tombstones the logical identity, removes its body and derived projections under retention policy, and makes future resolution fail closed.

Chunk purge removes shared media bytes only when no retained artifact, chunk, or live operation references/pins them and retention permits deletion. Removing one chunk is not authorization to destroy another production's assets. A rights-wide purge is a separate explicit policy action; it must block affected references even if retention requires keeping restricted audit data. Cleanup follows the Artifact Store publication/GC protocol.

Index text, embedding profiles, provider payloads, prompts, chat logs, retry history, and base64 media are not canonical chunk fields.

## Creation And Approval

```text
approved source artifacts and selected assets
-> Craft creates one typed chunk candidate artifact
-> schema, provenance, rights, and source-claim validation
-> lightweight human memory review
-> promote as the active approved chunk revision
-> derive consumer projections and, later, search records
```

Approval of a film or episode authorizes Craft to draft memory, but does not approve an unseen summary as future canon. The gate reviews that one candidate artifact; deterministic promotion updates its `chunk_binding`. Until then it is not available through `@@chunk` or pipeline-required context. Updating memory creates a new immutable revision; it never edits history in place.

Film or memory approval does not authorize inferred global taste changes. Taste suggestions require [separate explicit user acceptance](../database/knowledge-wiki.md#lifecycle-и-приёмка); personal preferences stay private and are selected explicitly, not automatically updated or injected into every film. The `taste.md` filename/editor details remain open, not the approval requirement.

Validation, freshness, approval, selection/promotion, and publication remain independent. Craft may inspect exact validated plans/timing analysis as supporting provenance, but result approval does not independently approve those artifacts or make planned intent a completed fact. The memory gate reviews new reusable claims. Promotion rechecks subject/activation/dependency closure, source approvals, rights, and expected chunk-binding revisions; it publishes only the reviewed bodies, never another model-generated summary.

Memory revision follows Critic -> Craft -> the same gate. Critic `needs_input`/`out_of_scope` returns a new request for the unchanged candidate without calling Craft; rewriting approved production sources requires a new execution outside this repair path. A historical approval cannot authorize publication after source validity or rights fail.

## Media Handles

A media handle connects an approved `AssetRef` to meaning:

```ts
type ChunkMediaHandleV1 = {
  handle: string;
  asset_ref: AssetRef;
  role: string;
  take: string[];
  ignore: string[];
  must_preserve: string[];
  prohibited_drift: string[];
  permitted_consumers: string[];
};
```

For example, a face reference may authorize identity and hair while explicitly excluding its background, temporary lighting, or pose. Downstream agents receive selected handles, not every asset in the chunk.

## Compact Projections

The canonical chunk is not pasted wholesale into every prompt. Deterministic, versioned projection functions expose only the fields and media handles required by a consumer. Missing mandatory projection data blocks the invocation; optional inspiration may be omitted with a recorded reason.

The prepared operation freezes exact source revisions and projection versions/digests. Checkpoints hold only a selection reference; adapters hydrate typed content and verify it on retries. `pinned_revision` shared canon does not follow a new active chunk binding automatically. New context needs a new authorized activation/execution; reindexing cannot approve, publish, or advance a graph.

## `CharacterChunkV1`

**Purpose:** durable character identity and continuity authority across projects, seasons, and episodes.

**Canonical content:** stable character ID and aliases; user-approved identity and narrative traits; visual identity, silhouette, age impression, face/hair features; baseline wardrobe; voice and motion traits when available; relationships and canon constraints; `must_preserve` and prohibited drift; approved image/video/audio handles; optional training reference metadata without provider activation syntax.

**Creation:** imported character Markdown/assets or approved character design becomes a Craft candidate and receives its own human memory review. A demo `.md` remains a source until this promotion occurs.

**Consumers and projections:**

- Season: identity, relationships, long arcs, and immutable constraints;
- Episode: narrative canon plus only current relevant continuity;
- Wardrobe: visual identity, baseline wardrobe, and anchor handles;
- Storyboard: shot-relevant appearance, pose/emotion handles, and prohibited drift;
- Filmmaker: motion/voice traits and selected visual handles.

**Injection:** explicit creator mention for cinematic work; pipeline-required when a season or episode references the character.

## `CinemaChunkV1`

**Purpose:** reusable memory of one completed cinematic production, primarily as explicit inspiration for future work.

**Canonical content:** approved hook and story summary; visual language; selected main frame as the primary style/identity anchor; ordered promoted story frames and clips; final video; concise carry-forward lessons; reuse rights and prohibited imitation.

**Creation:** after final video approval, Craft drafts the chunk from exact approved artifacts and promoted assets; memory review publishes it.

Each reusable claim retains the minimal [Cinema claim evidence](../agents/craft.md#cinema-claim-evidence): labelled intent/measured/observed basis and exact field or inspected-media citations. Selected frame/clip handles derive from exact RenderResult unit entries; final-film claims cite the final asset, not merely planned motion or source clips. These are semantic requirements; executable cinema schemas and evidence validators remain pending.

**Consumers:** Storytell, Wardrobe, Storyboard, Filmmaker, Montage, Muse, or Season only when the creator/pipeline explicitly selects a relevant projection. It is not mandatory context for a new cinematic by default.

**Injection:** story lesson projection for Storytell; visual-language/anchor projection for Wardrobe or Storyboard; motion/editing lesson projection for Filmmaker or Montage. Final media is never pasted as text and is passed only through selected handles.

## `MusicChunkV1`

**Purpose:** rights-aware musical inspiration, not the production result of a music-video project.

**Canonical content:** source/title and ownership/license; permitted and forbidden use; approved audio handle; analysis summary; genre, mood, instrumentation, vocal qualities; section and energy map; explicit `take`/`ignore`; optional lyrics/transcript reference under separate rights.

**Creation:** import plus rights declaration, optional bounded audio analysis, and explicit human approval. A generated song enters this reusable library only through a separate promotion action.

**Consumers:** Muse receives the rights-safe inspiration projection. Storyboard or Filmmaker may receive rhythm/energy projections only when the pipeline explicitly requests them. Montage consumes the exact approved song artifact and timing map, not an inspiration chunk.

**Forbidden use:** exact melody, copyrighted lyrics, artist/voice cloning, or an inference that an uploaded file is licensed merely because it exists.

## `SeasonChunkV1`

**Purpose:** active approved authority for a season.

**Canonical content:** premise and repeatable story engine; world/canon rules; tone and provider-payload-neutral production defaults; exact CharacterChunk refs; character and relationship arcs; escalation, setups, and payoffs; ordered episode blueprints and statuses; approved visual/audio anchors.

**Creation:** after approval of `SeasonPlanV1`, the per-episode VisualAnchorPlan, and selected episode anchors, Craft creates one `SeasonMemoryDraftV1` containing the proposed Season body and ordered planned Episode bodies. One gate reviews this aggregate stage output, not a bundle of independently owned artifacts. Deterministic promotion stages immutable bytes and then commits the separate chunk metadata/bindings and operation result atomically in the DB, checking every expected revision. Each output records its exact approved draft and body mapping; no additional creative call occurs during promotion. This does not claim atomicity between files and DB.

**Consumers and projections:** Episode receives season spine, target blueprint, relevant character/relationship subset, production continuity, and selected anchors. A later Season pipeline may receive a prior season projection only for an explicit continuation.

**Injection:** mandatory at continuity validation and Episode story creation; visual agents receive bounded episode-specific projections rather than the whole season.

## `EpisodeChunkV1`

**Purpose:** distinguish future episode intent from completed continuity while keeping one stable episode identity.

### Planned Revision

Contains episode index/title, logline/promise, must-happen events, setup/payoff obligations, planned character beats, and planned anchors. Every field is labelled as plan, never past fact. It is drafted from the approved season plan and reviewed before episode production.

### Completed Revision

Contains compact recap; exact ending state; character and relationship deltas; wardrobe, location, prop, injury, weather, and other continuity changes; open threads; required future payoffs; resolved obligations; selected anchors; final episode asset.

The completed revision is drafted only after final episode approval and then receives memory review. It does not overwrite the historical planned revision.

Stable episode identity is separate from revision role. An execution pins its target planned revision and corresponding season blueprint ID explicitly; promotion of a completed revision into the active shared binding does not replace that input. Do not use an ambiguous latest Episode lookup or require the upstream SeasonPlan to reference chunks that do not exist yet. A later approved continuity revision is selected by a new authorized execution rather than silently patched into running episodes.

**Injection into episode N:**

- approved `SeasonChunkV1` selected and pinned for this execution: mandatory;
- target planned episode revision: mandatory;
- completed episode N-1: mandatory when N is greater than one;
- referenced `CharacterChunkV1`s: mandatory;
- older completed episodes: only relevant continuity projections;
- future neighbor plans: optional and explicitly labelled as plans.

Wardrobe, Storyboard, and Filmmaker receive only the current visual/physical state and handles relevant to their acts or shots.

## `MusicVideoChunkV1`

**Purpose:** completed memory of one audiovisual production, distinct from general musical inspiration.

**Canonical content:** exact selected song artifact and rights; final timing map; approved visual concept and style frame; ordered promoted frames/clips; montage plan/result and final video; reusable audiovisual lessons; forbidden reuse.

**Creation:** after final video approval, Craft drafts the chunk and memory review publishes it.

**Consumers:** future Muse, Wardrobe, Storyboard, Filmmaker, or Montage stages only as explicitly selected inspiration. Saving its generated song as `MusicChunkV1` is a separate reviewed promotion.

## Pipeline Injection Matrix

| Pipeline stage | Required chunks | Optional explicit chunks |
|---|---|---|
| cinematic brief/story | selected character canon when reused | cinema inspiration |
| cinematic visual/motion | selected character projections | cinema style/motion lessons |
| serial season | selected characters; prior season only for continuation | cinema/music inspiration |
| serial episode story | season, target plan, previous completed episode, referenced characters | older relevant continuity |
| serial episode visual/motion | bounded character and episode-state projections | approved style inspiration |
| music-video Muse | none unless selected by Brief | music, character, cinema inspiration |
| Render | none | none; deterministic adapters consume exact FramePlan/MotionPlan/MusicPlan and assets |
| Montage | none | bounded cinema editing lessons only when explicitly selected; execution service consumes exact approved assets |
| Craft | none through discovery | reads exact approved sources and labelled supporting provenance through prepared direct projections |

## Attention And Token Cost

Embedding dimensions do not make injected context shorter. Cost is controlled by direct selection, consumer-specific projections, summaries linked to full canonical artifacts, selected media handles, and measured model-specific budgets. Mandatory canon never disappears silently to fit a budget.

## Deferred Types

World/location, voice, product, and other chunk families are added only when a real pipeline has one stable owner and consumer. Do not revive generic `MasterChunk`, `FinalChunk`, or the legacy five-block schema.

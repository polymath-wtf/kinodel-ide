# Creative Chunks

Status: **Future domain memory; no publication in the cinematic MVP.** Type contents below are design proposals, not executable schemas or mandatory pipeline stages.

A creative chunk is approved reusable production memory. It is a typed artifact with exact provenance, not an embedding row, arbitrary Markdown note, chat summary, or process archive.

Think of it as a **reusable creative card**, not a piece cut out of text or a runtime node. Retrieval passages are disposable search projections; consumer projections are bounded views for a specialist. Neither has an independent approval or canonical binding. Chunks use existing artifact storage and library bindings, not a second LangGraph Store copy or a database per type.

These are future library contracts. The current cinematic MVP ends with a technically verified assembly of approved shots, without final-film review or memory publication. References below to final approval describe prerequisites of future memory-enabled pipelines, not an existing gate. Before enabling Cinema publication, reconcile its final-source acceptance and anchor selection with the then-current cinematic contract; do not silently treat completion as approval.

## Shared Contract

Artifact infrastructure owns immutable ID, schema/version, digest, project scope, body URI, source provenance, and creation operation. A chunk body adds only domain meaning rather than repeating one universal legacy envelope.

Every chunk records or references:

- one stable logical subject such as a character, season, episode, film, or music reference;
- its authority role: `canon`, `plan`, `completed_fact`, or `inspiration`;
- exact approved source artifact revisions and separately labelled validated supporting provenance;
- approved media handles with rights and intended use;
- facts and continuity constraints needed by declared consumers;
- the prior chunk revision it supersedes when applicable.

Project DB `chunk_bindings` map each logical subject to its active approved artifact revision, status and optimistic revision. [Knowledge lifecycle](../database/knowledge-wiki.md#lifecycle-и-приёмка) owns supersede/archive/withdrawal/purge: ordinary updates retain pinned history; withdrawal blocks even prepared use. Deleting a chunk never independently authorizes deleting shared production media; [artifact storage](../backend/artifacts.md#managed-project-storage) owns pins and cleanup.

Index text, embedding profiles, provider payloads, prompts, chat logs, retry history, and base64 media are not canonical chunk fields.

## Creation And Approval

```text
approved source artifacts and selected assets
-> memory feature maps selected fields and creator-authored claims into one typed candidate
-> schema, provenance, rights, and source-claim validation
-> lightweight human memory review
-> promote as the active approved chunk revision
-> derive consumer projections and, later, search records
```

A future memory feature explicitly selects eligible production sources; completion alone does not trigger publication. No Craft agent is required. Human review approves the candidate's reusable claims, not an unseen summary. Publication rechecks source acceptance, rights, dependency closure and expected binding revisions; it publishes those exact reviewed bytes. Only then is the revision available through `@@chunk` or required library context. Supporting plans remain intent, not observed fact. Personal taste needs [separate explicit acceptance](../database/knowledge-wiki.md#lifecycle-и-приёмка).

Future memory revision edits the typed candidate and returns it to the same review; saving and publication are service operations, not reasoning tasks. Missing required evidence blocks publication rather than inventing claims. Rewriting approved production sources requires a new execution; historical approval cannot authorize publication after rights or source validity fail.

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

The [context resolver](../context/context.md#contextselectionv1) freezes exact revisions and versioned consumer projections on the prepared operation. Required canon cannot disappear to fit a budget. Retry rehydrates that selection; a new library revision or index does not change it. The content/consumer sections below define what is useful to project, not a second selection protocol.

## `CharacterChunkV1`

**Purpose:** durable character identity and continuity authority across projects, seasons, and episodes.

**Canonical content:** stable character ID and aliases; user-approved identity and narrative traits; visual identity, silhouette, age impression, face/hair features; baseline wardrobe; voice and motion traits when available; relationships and canon constraints; `must_preserve` and prohibited drift; approved image/video/audio handles; optional training reference metadata without provider activation syntax.

**Creation:** explicit source-field mapping and creator edits turn imported character Markdown/assets or approved design into a typed candidate for human memory review. A demo `.md` remains a source until this promotion occurs.

**Consumers and projections:**

- Season: identity, relationships, long arcs, and immutable constraints;
- Episode: narrative canon plus only current relevant continuity;
- Wardrobe: visual identity, baseline wardrobe, and anchor handles;
- Storyboard: shot-relevant appearance, pose/emotion handles, and prohibited drift;
- Filmmaker: motion/voice traits and selected visual handles.

**Injection:** explicit creator mention for cinematic work; pipeline-required when a season or episode references the character.

## `CinemaChunkV1`

**Purpose:** reusable memory of one completed cinematic production, primarily as explicit inspiration for future work.

**Canonical content:** approved hook and story summary; visual language; explicitly selected style/identity media handles; ordered promoted story frames and clips; final video; concise carry-forward lessons; reuse rights and prohibited imitation. Selecting a representative image for memory does not restore the retired production `main_frame` slot.

**Creation:** source eligibility and explicit creator acceptance of the assembled final must be defined when memory is enabled, because current cinematic has no final-film gate. The memory feature maps exact sources and creator-supplied claims into a candidate; memory review separately approves publication.

Each reusable claim retains the minimal [Cinema claim evidence](../tools/memory.md#cinema-claim-evidence): labelled intent/measured/observed basis and exact field or inspected-media citations. Selected frame/clip handles derive from exact RenderResult unit entries; final-film claims cite the final asset, not merely planned motion or source clips. These are semantic requirements; executable cinema schemas and evidence validators remain pending.

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

**Creation, unresolved:** [serial](../pipelines/serial.md#episode-breakdown-and-execution) first approves one SeasonPlan; target episodes may use exact blueprint projections or separately published chunks. The earlier `SeasonMemoryDraftV1` aggregate is an option only if chunk publication is chosen. Then one memory review covers the proposed Season/Episode bodies and deterministic publication commits their bindings atomically after file publication, without another model call. Per-episode anchors and a separately approved VisualAnchorPlan are not prerequisites of the current serial concept.

**Consumers and projections:** Episode receives season spine, target blueprint, relevant character/relationship subset, production continuity, and selected anchors. A later Season pipeline may receive a prior season projection only for an explicit continuation.

**Injection:** if this chunk-based path is activated, supply its bounded season/episode projection before Episode creation; otherwise use the exact approved plan projection declared by serial. Visual agents receive only relevant continuity.

## `EpisodeChunkV1`

**Purpose:** distinguish future episode intent from completed continuity while keeping one stable episode identity.

### Planned Revision

Contains episode index/title, logline/promise, must-happen events, setup/payoff obligations, planned character beats, and planned anchors. Every field is labelled as plan, never past fact. It is drafted from the approved season plan and reviewed before episode production.

### Completed Revision

Contains compact recap; exact ending state; character and relationship deltas; wardrobe, location, prop, injury, weather, and other continuity changes; open threads; required future payoffs; resolved obligations; selected anchors; final episode asset.

The completed revision is drafted only after final episode approval and then receives memory review. It does not overwrite the historical planned revision.

Stable episode identity is separate from revision role. If chunks are enabled, pin the target planned revision and corresponding season blueprint ID; publication of a completed revision does not replace that input. Never require SeasonPlan to reference chunks that do not exist yet. Exact blueprint projections remain the other open serial option. Later continuity changes require a new authorized selection.

**Proposed injection into episode N when the chunk-based path is chosen:**

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

**Creation:** after final video approval, the memory feature prepares a typed candidate from selected fields and evidenced creator claims; memory review authorizes publication.

**Consumers:** future Muse, Wardrobe, Storyboard, Filmmaker, or Montage stages only as explicitly selected inspiration. Saving its generated song as `MusicChunkV1` is a separate reviewed promotion.

## Pipeline Injection Matrix

Future consumer map, conditional on each memory-enabled pipeline. It does not require these chunks or library tables in the current cinematic build; serial's projection-versus-publication choice remains open.

| Pipeline stage | Required chunks | Optional explicit chunks |
|---|---|---|
| cinematic brief/story | selected character canon when reused | cinema inspiration |
| cinematic visual/motion | selected character projections | cinema style/motion lessons |
| serial season | selected characters; prior season only for continuation | cinema/music inspiration |
| serial episode story | season, target plan, previous completed episode, referenced characters | older relevant continuity |
| serial episode visual/motion | bounded character and episode-state projections | approved style inspiration |
| music-video Muse | none unless selected by Brief | music, character, cinema inspiration |
| Render | none | none; deterministic adapters consume exact FramePlan/MotionPlan/MusicPlan and assets |
| Montage | none | none in MVP; execution service consumes exact approved assets; editing lessons require a future creative editor |
| Memory publication service | none through discovery | maps exact selected source fields and reviewed claims; no agent context |

## Attention And Token Cost

Embedding dimensions do not make injected context shorter. Cost is controlled by direct selection, consumer-specific projections, summaries linked to full canonical artifacts, selected media handles, and measured model-specific budgets. Mandatory canon never disappears silently to fit a budget.

## Deferred Types

World/location, voice, product, and other chunk families are added only when a real pipeline has one stable owner and consumer. Do not revive generic `MasterChunk`, `FinalChunk`, or the legacy five-block schema.

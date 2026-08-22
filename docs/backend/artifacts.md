# Artifact Contracts

Status: **Decided foundation**

Artifacts are validated creative truth. A checkpoint says where an execution is; an artifact says what it produced.

## Principles

- Every committed revision is immutable.
- Every logical output has one declared owner.
- Graph state stores `ArtifactRef`, never full bodies or media.
- Node adapters validate and persist agent output; agents do not write arbitrary files.
- Downstream nodes consume exact revisions, not "latest file" or directory scans.
- Provider logs, retries, queue IDs, costs, and raw responses are runtime records, not creative artifacts.
- Derived indexes and previews can be rebuilt from canonical artifacts and assets.

## Reference

```ts
type ArtifactRef = {
  artifact_id: string;
  schema_id: string;
  schema_version: string;
  uri: string;
  digest: string;
  revision: number;
  media_type: string;
  project_id: string;
  execution_id: string;
  produced_by_stage: string;
  operation_id: string;
};
```

`uri` is internal storage identity, not a user-supplied path. Public URLs are optional projections and must not define asset identity.

`artifact_id` identifies one immutable revision. `revision` is the monotonic revision number of its logical slot; a new revision receives a new `artifact_id` and URI.

## Logical Bindings

The execution state maps a semantic slot to one immutable artifact revision:

```ts
type ArtifactBindings = Record<string, ArtifactRef>; // slot -> exact revision
```

Examples: `brief`, `story`, `main_frame_request`, `main_frame`, `story_frames`, `video_plan`, `final_video`.

A revision creates a new artifact and atomically changes the binding. It never overwrites history.

## Commit Protocol

```text
typed candidate
-> schema validation
-> semantic and cross-artifact validation
-> write immutable content/assets
-> commit metadata and provenance
-> atomically update logical binding
-> return ArtifactRef to graph state
```

Every commit uses:

- `operation_id` for idempotency;
- `expected_revision` for optimistic concurrency;
- input artifact digests for provenance;
- a declared output slot and owner.

Same operation plus same content returns the existing reference. Same operation plus different content is an integrity error.

Before invoking a nondeterministic model or external service, a node queries the store by `operation_id`. If that operation already committed, the node returns the existing reference without repeating the work. This closes the crash window between artifact commit and LangGraph checkpoint.

## Media

```ts
type AssetRef = {
  asset_id: string;
  kind: "image" | "video" | "audio" | "document";
  uri: string;
  digest: string;
  mime_type: string;
  bytes?: number;
  duration_ms?: number;
  width?: number;
  height?: number;
};
```

Ordered selected assets are explicit in result artifacts. No downstream stage scans output directories to guess selection or order.

## Provenance

Every generated artifact records:

- source artifact IDs and digests;
- stage and capability version;
- operation ID;
- creation time;
- selected assets when applicable.

Provider/model audit can live in restricted runtime metadata. Creative artifacts should contain it only when reproducibility of that artifact genuinely requires it.

## Invalidation

Do not maintain a hand-written list of stale files. A downstream artifact is stale when one of its recorded input digests no longer matches the active binding.

Examples:

- story revision invalidates visual planning and everything derived from it;
- selected frame revision invalidates motion planning and montage;
- clip selection revision invalidates final video and reusable final memory.

Old revisions remain valid historical outputs. A slot may still point to its latest produced revision after an upstream change, but provenance validation marks that binding stale and prevents downstream consumption until the owning stage replaces it. History and stale previews therefore remain inspectable without pretending they satisfy current preconditions.

## Minimal Schemas

Start with only the schemas needed by the vertical slice:

- `brief.v1`;
- `story.v1`;
- `render_requests.v1` and `render_result.v1` when rendering is added;
- reusable chunk schemas only when their pipeline exists.

Do not build one universal artifact envelope that attempts to model every domain field.

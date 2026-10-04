# Local Characters

Status: **active creator-authored `CharacterV1` library; not generated production memory or `CharacterChunkV1`.**

Characters lets a creator author reusable cards locally, without generation, a database, cloud sync/upload, retrieval index or a memory-publication stage. Agents have no filesystem/library browsing access. Private cards are not automatically published with packaged wiki resources.

## Card And Acceptance

`CharacterV1` has `schema_id="character"`, `schema_version="1"`, stable `subject_id`, positive integer `revision`, `bio` and ordered `images`. Bio requires `name`; `age`, `gender` and `vibe` are optional narrative text. A card requires 1–6 PNG/JPEG/WebP images, each at most 10 MiB, 8192 px per side and 16 million pixels. Uploads are decoded, orientation-normalized and re-encoded without metadata; SVG, animation, mismatched/invalid files and oversized images are rejected. Audio/video are not active fields.

**Save character** explicitly accepts the creator-authored card for reuse. A draft or image upload alone is not acceptance. Saving creates an immutable revision; updating the same subject requires its `expected_revision`. This is not approval of generated production facts and needs no chunk-memory review. The existing localhost session/Host/Origin/CSRF boundary guards saves and reads.

## Canonical Storage

The default root is this `wiki/characters/` directory, separate from execution data. The application manages:

```text
manifest.json
revisions/<subject_id>/<revision>-<card-sha256-hex>.json
images/<image-sha256-hex>.<png|jpg|webp>
```

- `manifest.json` is the atomic commit authority: `current` maps subjects to last exact `CharacterRef`s; `mutations` retains payload digests and save/delete receipts for idempotent replay. Existing canonical version `1` remains readable; the first successful deletion atomically upgrades it to version `2`. Reads and rejected commands do not migrate it.
- `CharacterRef = {subject_id, revision, digest}`; `digest` is `sha256:<hex>` of canonical card JSON. Each image entry records its own digest, MIME, byte length and dimensions. Paths are backend-derived, never client identities.
- Images and revision JSON publish before the manifest commits. Old committed revisions/images remain readable; replay returns the original receipt without rolling current back. Reusing a mutation ID with different bytes/target or a stale update is rejected.
- Reads do not bootstrap an empty library. Unreferenced files left by interrupted saves are not accepted cards; no automatic cleanup is active. A missing/corrupt initialized manifest or tampered bytes fail closed, never silently reset the library. Do not manually edit/delete managed files or overwrite an existing library during setup.

Browser IndexedDB holds pending exact image-bearing mutations before POST, not canonical cards. The manifest/files remain authoritative after browser storage loss. Storage uses one library lock and a bounded manifest; Windows checks cover process-death recovery, not power loss or cloud/network-share storage.

## Deletion

Only the editor exposes **Delete draft** and **Delete character**, each requiring confirmation. Draft deletion discards unsent fields/images without changing the saved character. Opening a different character or creating a new one replaces an unsent draft without a confirmation.

Opening a saved character is clean: **Continue draft** appears only when Bio or ordered image inputs differ from the opened version. Exact reversion clears dirty. Back and page navigation retain those unsent edits; Continue or reopening the same subject resumes them without fetching latest or changing the original OCC revision. Clean cards disable draft deletion. Unsent drafts live in the mounted workspace; pending delivery remains separately persisted in IndexedDB.

`POST /api/characters/delete` accepts `{mutation_id, subject_id, expected_revision}` (JSON, at most 4 KiB) and returns `{mutation_id, ref, deleted:true}` for the last exact saved revision. It shares the save mutation-ID namespace, library lock and localhost security boundary. A stale revision, changed replay payload/key or already deleted target under a new key yields 409; an unknown subject yields 404. Identical replay returns the original receipt, including after restart.

The durable delete receipt removes the subject from the active library; it does not unlink immutable revisions/images. Exact historical reads and frozen Story inputs remain valid, as do new Starts with an already selected exact ref. New updates cannot resurrect a deleted subject; original save replays remain idempotent. There is no restore action in this slice.

Uncertain save/delete delivery cannot be discarded as a draft. The browser persists the exact request before POST, validates its receipt and only then clears the journal. Authentication/CSRF rejection retains pending delivery; one bounded session renewal retries the same bytes/key. Reload exposes **Continue deletion** and exact replay.

## Selection And Storytell

The Story form optionally selects exact refs, not names or latest aliases. Fresh Start verifies committed card revisions and freezes their snapshots and narrative Bio projection in the existing execution owner configuration. Later library edits cannot change that execution; replay/retry/reopen use the frozen data, even if the library is unavailable. This execution snapshot is input provenance, not another editable reusable library.

Only narrative Bio (`name`, optional `age`, `gender`, `vibe`) and exact-ref provenance go to remote Storytell. Images remain local for card/preview use in the current text slice; neither image bytes nor arbitrary paths are sent. No selection is also valid: Storytell may invent the cast in `StoryV2.generated_characters`.

Generated cast and subsequent Story revisions are execution-local. Neither generation nor Story approval creates/publishes a character card automatically. Future production-memory `CharacterChunkV1` review/publication and visual consumers are separate activation work; saving an authored card does not enable them.

Implementation: [`backend/characters.py`](../../backend/characters.py), [`character_api.py`](../../backend/character_api.py), [`story_start.py`](../../backend/story_start.py), [`openrouter.py`](../../backend/openrouter.py). Contracts: [context](../../docs/context/context.md#local-creator-authored-characters), [future chunks](../../docs/rag/chunks.md#characterchunkv1); checks/evidence: [Local MVP](../../docs/roadmap-mvp.md#remaining-steps).

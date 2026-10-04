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

- `manifest.json` (`schema_version="1"`) is the atomic commit authority: `current` maps subjects to exact `CharacterRef`s; `mutations` retains payload digests and save receipts for idempotent replay.
- `CharacterRef = {subject_id, revision, digest}`; `digest` is `sha256:<hex>` of canonical card JSON. Each image entry records its own digest, MIME, byte length and dimensions. Paths are backend-derived, never client identities.
- Images and revision JSON publish before the manifest commits. Old committed revisions/images remain readable; replay returns the original receipt without rolling current back. Reusing a mutation ID with different bytes/target or a stale update is rejected.
- Reads do not bootstrap an empty library. Unreferenced files left by interrupted saves are not accepted cards; no automatic cleanup is active. A missing/corrupt initialized manifest or tampered bytes fail closed, never silently reset the library. Do not manually edit/delete managed files or overwrite an existing library during setup.

Browser IndexedDB holds pending exact image-bearing mutations before POST, not canonical cards. The manifest/files remain authoritative after browser storage loss. Storage uses one library lock and a bounded manifest; Windows checks cover process-death recovery, not power loss or cloud/network-share storage.

## Selection And Storytell

The Story form optionally selects exact refs, not names or latest aliases. Fresh Start verifies committed card revisions and freezes their snapshots and narrative Bio projection in the existing execution owner configuration. Later library edits cannot change that execution; replay/retry/reopen use the frozen data, even if the library is unavailable. This execution snapshot is input provenance, not another editable reusable library.

Only narrative Bio (`name`, optional `age`, `gender`, `vibe`) and exact-ref provenance go to remote Storytell. Images remain local for card/preview use in the current text slice; neither image bytes nor arbitrary paths are sent. No selection is also valid: Storytell may invent the cast in `StoryV2.generated_characters`.

Generated cast and subsequent Story revisions are execution-local. Neither generation nor Story approval creates/publishes a character card automatically. Future production-memory `CharacterChunkV1` review/publication and visual consumers are separate activation work; saving an authored card does not enable them.

Implementation: [`backend/characters.py`](../../backend/characters.py), [`character_api.py`](../../backend/character_api.py), [`story_start.py`](../../backend/story_start.py), [`openrouter.py`](../../backend/openrouter.py). Contracts: [context](../../docs/context/context.md#local-creator-authored-characters), [future chunks](../../docs/rag/chunks.md#characterchunkv1); checks/evidence: [Local MVP](../../docs/roadmap-mvp.md#remaining-steps).

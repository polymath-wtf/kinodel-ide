# Kinodel reference optimization

Use this when auditing or refactoring `pipeline-kinodel/references/`.

## Ownership rule

`pipeline-kinodel` should contain law, route, and the smallest stable maps needed to navigate the system. Move execution detail to the skill that owns it:

| Detail type | Owner |
| --- | --- |
| Pipeline route, hard gates, artifact invariants | `pipeline-kinodel` |
| Producer orchestration, gate UI text, handoff generation | `producer-kinodel` |
| Project scaffold/init/brief-file shape | `kinodel-project-layout` |
| Render request/result schema and provider payloads | `render-kinodel` |
| Specialist output contracts | owning specialist skill (`storytell`, `wardrobe`, `storyboard`, `filmmaker`, etc.) |
| Historical failures and troubleshooting triggers | `bugs/*.md` + `bugs/bugs-mapping.md` |

## Preferred compact shape

For `pipeline-kinodel`, prefer:

- `SKILL.md` — hot-path law and route only.
- `references/artifact.md` — canonical artifact/handoff/request/result map and L0-L6 context model.
- `references/goal-pipeline.md` — exact `/goal` checkpoints and exit conditions.
- `bugs/bugs-mapping.md` — trigger index for still-relevant bug notes.

Audit/remediation references are allowed, but mark them maintenance-only and do not load during normal production.

## Refactor patterns

1. Merge overlapping concept docs when they explain the same abstraction. Example: artifact layering + canonical artifact map belongs in one `references/artifact.md`.
2. Convert incident narratives into compact bug notes with: signature, cause, fix, durable law.
3. Keep bug maps under `bugs/`, not `references/`, when the package uses a dedicated bug directory.
4. After moving files, update all SKILL.md progressive reference lists and cross-skill pointers.
5. Search for stale old filenames and old directory names after the move.
6. Watch for broad search/replace side effects across sibling Kinodel skills; not every package uses the same `bug/` vs `bugs/` directory shape.

## Owner migration workflow

When moving a pipeline reference to a more specific owner, do not leave a dangling pointer file unless the user explicitly asks for compatibility stubs. Preferred sequence:

1. Read the pipeline reference and the target owner reference/skill.
2. Move only unique durable rules into the owner (`kinodel-project-layout` for scaffold/brief shape, `producer-kinodel` for gate UI and orchestration, `render-kinodel` for request/result schema, worker skills for stage contracts).
3. Delete the superseded pipeline reference after the owner has the knowledge.
4. Add a compact ownership pointer or index in `pipeline-kinodel`, not a copied long contract.
5. Verify with stale-link search for the deleted filename and for shortened/globbed provider pointers.
6. If examples are migrated, fix architecture-breaking examples at the same time (for example external-provider `input_media` must use public `https://` URLs from selected result manifests, not local `outputs/...` paths).

For worker contracts specifically, keep `producer-kinodel/references/delegated-design-stages.md` as the generic delegation base, keep executable stage contracts in the owning worker `SKILL.md`, and keep only `pipeline-kinodel/references/worker-contract-index.md` as the synchronization map.

Audit/checklist material is maintenance context, not production context. If it is useful, consolidate it under `pipeline-kinodel/bugs/audit.md` and mark it maintenance-only instead of listing it as a normal progressive production reference.

## Deletion candidates checklist

Before deleting a reference, ask:

- Is this already in `SKILL.md` or a more canonical owner skill?
- Is this a one-off incident that can be represented as a bug trigger?
- Is this provider/runtime detail that belongs to `render-kinodel`?
- Is this Producer behavior that belongs to `producer-kinodel`?
- Is this a large stage contract that belongs to the stage owner?

If yes, move/merge it and leave only a compact pointer in `pipeline-kinodel` when needed.

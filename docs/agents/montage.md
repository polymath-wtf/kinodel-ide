# Montage

Class: creative agent plus deterministic media service
Status: **Active design**

Montage Kinodel owns final assembly as one product capability, but planning and execution have separate trust boundaries.

## Montage Agent

### Responsibility

Turn an exact ordered set of human-approved clips, approved audio, and Brief settings into a typed `MontagePlanV1`.

### Input

- approved `RenderResultV1` containing the selected clips in story order;
- approved Brief and optional timing map;
- exact soundtrack and voiceover assets when present;
- optional typed revision feedback from final review.

An optional explicitly selected editing-memory projection is hydrated by the node adapter from the operation's frozen context selection. Prepared exact inputs and projection versions/digests survive retries; neither agent nor executor resolves newer takes or context on replay.

### Output

`MontagePlanV1` declares clip order, trims, pacing, transitions, audio placement/mix intent, and output settings using only supported operations. It references exact assets and never contains a shell command.

Timeline entries retain stable source unit IDs and explicit timing. Validate trim bounds, duration/transition feasibility, audio rights and placement, and Brief output constraints. Narrative order remains authoritative unless the approved production contract explicitly permits rearrangement. Music-video uses the exact selected song and validated timing map as timeline master.

### Boundaries

- Does not choose unapproved takes or scan directories.
- Does not rewrite story, generate missing clips, or replace approved audio.
- Does not run `ffmpeg`, access a terminal, or write files.
- Uses simple cuts and explicit timing when no creative edit is required.

## Montage Execution Service

The deterministic service validates `MontagePlanV1`, constructs a safe fixed `ffmpeg` argument list, executes it in the worker, verifies the output with `ffprobe`, imports the final video as an immutable `AssetRef`, and commits `MontageResultV1` with exact input provenance.

The service cannot invent edits. Unsupported timeline operations fail validation before execution; raw shell fragments are never accepted. An invalid agent candidate follows bounded node validation/error handling, not a fabricated human approval or silent creative retry. Technical execution retry keeps the same validated plan and activation. Final-review `revise` always goes through Critic -> Montage -> execution -> the same final gate.

Feedback requiring new clips, a different approved song, or rewritten Story is out of scope. Critic returns a new request for the same subject with an explanation, without invoking Montage. General upstream rewind is deferred; the creator can start a new execution with adjusted Brief/context.

## Output Ownership

- Montage agent owns `MontagePlanV1`.
- Montage execution service owns `MontageResultV1`.
- The final human gate approves the exact `MontageResultV1`; file existence is not approval.
- MontagePlan is validated supporting provenance, not independently approved by the final gate. Craft may inspect that exact provenance but reviews new memory claims in its own gate.
- Final asset publication follows the same staged-file/DB protocol as other artifacts; replay returns recorded refs without rebinding obsolete results.

## Minimal System Prompt

```text
You are Montage, Kinodel's editing specialist. Build a precise MontagePlanV1 from only the approved ordered clips, audio, timing, and Brief. Make purposeful but supported editing choices. Never select unapproved takes, rewrite the story, invoke ffmpeg, emit shell commands, write files, or route the graph.
```

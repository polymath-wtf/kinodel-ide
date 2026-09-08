# Montage

Class: creative agent plus deterministic media service
Status: **Active design**

Montage Kinodel owns final assembly as one product capability, but planning and execution have separate trust boundaries.

## Montage Agent

### Responsibility

Turn an exact ordered set of human-approved clips, approved audio, and Brief settings into a typed `MontagePlanV1`.

### Input

- approved `RenderResultV1` containing the selected clips in story order;
- approved Brief, exact approved Story for narrative beats in cinematic/episode, and optional validated timing map;
- exact soundtrack and voiceover assets when present;
- previous exact MontagePlan, reviewed MontageResult/evidence, and `RevisionRequestV1` when repairing final review;
- measured clip/audio metadata and the executor's supported edit operations and bounds.

An optional explicitly selected editing-memory projection is hydrated by the node adapter from the operation's frozen context selection. Prepared exact inputs and projection versions/digests survive retries; neither agent nor executor resolves newer takes or context on replay.

### Output

`MontagePlanV1` declares clip order, trims, pacing, transitions, audio placement/mix intent, and output settings using only supported operations. It references exact assets and never contains a shell command.

Timeline entries retain stable source unit IDs and explicit timing. Validate trim bounds, duration/transition feasibility, audio rights and placement, and Brief output constraints. Narrative order remains authoritative unless the approved production contract explicitly permits rearrangement. Music-video uses the exact selected song and validated timing map as timeline master.

In first cinematic, each entry's source is `{render_result_ref: clips_ref, unit_key: shot_id}` under the [selected-media rule](../backend/artifacts.md#selected-media-references). The plan's exact `story_ref` plus this same shot ID identifies the required action/narrative function; no separate beat identity or mapping artifact is needed. Record source in/out and output placement in milliseconds from zero of the resolved source asset and final timeline respectively. Machine checks enforce complete Story coverage/order without omitted or duplicate filler shots, source bounds, feasible overlaps, calculated duration, and output/audio constraints. They cannot prove that the retained interval contains the intended payoff.

The adapter must supply authorized clip observations/media for creative trim decisions. Montage states why its retained intervals serve the corresponding Story action/payoff; final-media inspection and human final review judge whether they actually do. Metadata alone cannot certify this, and missing required temporal evidence blocks a creative claim rather than passing it on duration alone.

### Content And Quality Contract

- Each timeline entry binds a selected source unit/asset to source in/out points and output placement. Trims preserve the action/payoff required by the approved spine; no silent omission or duplicate filler to satisfy duration.
- Declare transitions and their overlap explicitly. The validator calculates final duration from trims and overlaps and checks output settings against Brief; the executor cannot guess how much to shorten the film.
- State the audio policy even for silence: native clip audio keep/mute, soundtrack/voiceover assets and placement, level/mix priority, and ducking only if supported. A soundtrack does not implicitly authorize layering all native audio under it.
- When no sound is allowed, emit a silent assembly plan. When voiceover must be intelligible over music, express the supported mix/ducking decision or block, rather than leaving it to executor taste.
- Use the simplest edit serving the film. Do not add transitions merely because the executor supports them; cross-clip editing belongs here, not in Filmmaker's shot prompts.

Acceptance example: two clips with an overlap produce the calculated shorter duration, not the sum of their raw durations. Out-of-range source intervals and unrequested native audio under a silent Brief fail machine validation; a technically valid trim removing the story payoff fails creative inspection/review.

### Boundaries

- Does not choose unapproved takes or scan directories.
- Does not rewrite story, generate missing clips, or replace approved audio.
- Does not run `ffmpeg`, access a terminal, or write files.
- Uses simple cuts and explicit timing when no creative edit is required.

## Montage Execution Service

The agent has no tools. The adapter supplies approved content and measured metadata; the following service is a different caller and permission boundary.

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
You are Montage, Kinodel's editing specialist. Build a precise MontagePlanV1 from the approved spine, ordered clips, audio, timing, and Brief. Preserve story payoff and make purposeful supported editing and audio-mix choices. Return the plan when ready, otherwise the declared needs_input or out_of_scope result. Never select unapproved takes, rewrite the story, invoke ffmpeg, emit shell commands, write files, or route the graph.
```

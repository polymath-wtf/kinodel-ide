# Montage

Class: **deterministic assembly tool in MVP; creative agent deferred**.

## MVP Responsibility

The single visible `montage` node assembles the complete approved `shot_videos` set in Story order and saves `final_video`. No mandatory LLM planner or separate `montage_execute` node.

Inputs: submitted Brief output settings, approved Story shot order, exact approved video refs and measured metadata. Freeze an internal [MontagePlanV1](../backend/dto.md#cinematic-extension) containing ordered shot/source refs and output settings. Concatenate every full clip with simple cuts; derive intervals and expected duration from verified metadata instead of storing an editable timeline. Normalize output only through supported transcode settings; first cinematic is silent, so remove native audio. Missing videos, impossible parameters or invalid bytes block instead of omitting a shot.

## Montage Execution Service

Construct a fixed safe ffmpeg argument list from the plan; no shell fragments or arbitrary paths from models/users. Run in an isolated attempt directory with supervised process lifetime. Verify output using ffprobe, including dimensions, expected duration within the selected encoding's declared tolerance and zero audio streams; import immutable bytes and commit `MontageResultV1` plus provenance. Technical retry reuses the exact plan and returns an existing committed result without reassembly.

The tool does not choose alternative takes, trim story payoff, rewrite prompts or regenerate missing videos. Completion checks approved sources and valid final output. The MVP has no separate final HITL: assembled `final_video` is not labelled independently human-approved.

## Output Ownership

<a id="output"></a>

Montage owns the internal assembly plan and final result write. No second creative artifact owner or visible save/promotion stage is required. Craft publication is a separate later feature.

## Later Creative Agent

When creative editing is needed, add a bounded Montage agent proposing trims, pacing, transitions and audio placement from exact approved media. It returns a typed plan, never a command line. Its temporal evidence, editable scope and human review must be defined at activation; these are not MVP prerequisites.

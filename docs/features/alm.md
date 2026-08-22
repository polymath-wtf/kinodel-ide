# Audio Analysis

Status: **Proposed service for `music_video.v1`**

ALM converts an audio asset into typed production evidence:

- sections and timestamp windows;
- tempo/energy curve and transitions;
- vocals, instrumentation, mood, and notable hooks;
- montage and visual trigger suggestions;
- confidence and analysis provenance.

It is a service/tool, not an orchestrating agent. It may combine deterministic DSP, transcription, source separation, and a multimodal model, but the pipeline consumes one provider-neutral `AudioAnalysisV1` artifact.

Initial MVP needs section and lyric-window timing, not perfect beat-level decomposition. Direct music embeddings remain experimental and are not a substitute for explicit timing analysis.

# Kinodel Wiki

Status: **local packaged prompt sources plus a separate creator-authored character library; not generated production memory**

Prompt libraries are explicit versioned resources. They are injected only after an allowlisted `ContextSelectionV1` resolves an exact revision and digest.

| Resource | Consumers |
|---|---|
| [light](prompts/light.md) | Wardrobe, Storyboard |
| [emotions](prompts/emotions.md) | Wardrobe, Storyboard |
| [camera](prompts/camera.md) | Storyboard |

`@resource` and `@artifact` mentions resolve to exact authorized references before the model call. Agents never receive arbitrary filesystem paths. Missing mandatory resources fail closed; optional resources are recorded as omitted.

## Local Characters

[characters/](characters/README.md) is the canonical local store for accepted creator-authored `CharacterV1` cards: an atomic manifest, immutable revisions and managed images. **Save character** is explicit creator acceptance; no cloud, index or production-memory publication is involved. Live Story selection freezes exact revisions and sends only narrative Bio to Storytell; images stay local in the text slice. Generated Story cast stays execution-local, with no automatic library publication. This activation is separate from packaged prompt resources and future `CharacterChunkV1` memory; it does not make the general mention/context-selection protocol above a completed runtime feature.

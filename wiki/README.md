# Kinodel Wiki

Status: **local packaged source library; not runtime canon**

Prompt libraries are explicit versioned resources. They are injected only after an allowlisted `ContextSelectionV1` resolves an exact revision and digest.

| Resource | Consumers |
|---|---|
| [light](prompts/light.md) | Wardrobe, Storyboard |
| [emotions](prompts/emotions.md) | Wardrobe, Storyboard |
| [camera](prompts/camera.md) | Storyboard |

`@resource` and `@artifact` mentions resolve to exact authorized references before the model call. Agents never receive arbitrary filesystem paths. Missing mandatory resources fail closed; optional resources are recorded as omitted.

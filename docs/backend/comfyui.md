# ComfyUI Boundary

Status: **Provider/service design**

ComfyUI is a first-class local or remote render backend. A large deterministic ComfyUI graph appears to Kinodel as one provider workflow with typed inputs, outputs, and capability metadata.

Provider-neutral ports, validation, dependencies and selection belong to [Render](../tools/render.md); durable operations belong to [tools](../tools/tools.md). Local connection, native HTTP routes and verified import belong to [ComfyUI tool](../tools/comfyui-tool.md). Hosted storage, retention and order policy belong to [credits and storage](../database/credits-billing.md#результат-удалённого-рендера); [hosted order DTOs](dto.md#endpoint-wire) are not native ComfyUI routes.

## Contract

The adapter owns one authoritative versioned workflow registry, semantic-to-node mappings, readiness, input materialization, submission/reconciliation and verified output import. Do not duplicate aliases in Python and JSON. Workflow version participates in the job fingerprint; secrets, raw workflows, queue IDs and logs stay out of creative artifacts. Health checks use real readiness endpoints without generating paid content; provider paths/URLs are not durable asset identities.

## Profile Selection

This is a deterministic adapter rule, not an LLM provider choice or a claim that working profiles are registered. A registered generation profile binds its stable ID and immutable version/digest to provider, job kind, workflow ID/version, required semantic inputs, supported workflow classes, dimensions/aspect ratios, duration/output/audio constraints, and required prompt-guidance resources. Raw workflows and semantic-to-node mappings remain in the one adapter-owned workflow registry; profiles reference them rather than copying them.

1. Validate submitted user requirements and visible defaults before Run, including provider preference. Pin Brief and registered capability/profile versions at start; no mandatory Producer or Brief review.
2. For each required image/video job kind, filter registered profiles by fixed pipeline, all explicit requirements, effective defaulted settings, and capabilities. `comfyui provider` requires ComfyUI for both image and video here; it supplies neither workflow nor profile IDs. An explicit profile must itself pass these checks.
3. Keep a compatible explicitly requested profile. Otherwise select the compatible profile designated by the supplied defaults for that job kind/provider; if there is no designated default, select only when exactly one compatible registered profile remains. Multiple remaining choices require focused clarification or block, never arbitrary registry order or an LLM guess. A designated but missing/incompatible default is a configuration failure, not permission to substitute another profile.
4. Validate every enabled role: portrait generation, portrait-conditioned sheet, character-free location and multi-reference shot frames; add video/start-image compatibility only for graphs enabling `i2v`. A profile may bind distinct versioned workflows for these roles. Declare named input/output schemas, role mappings and cardinality in the existing workflow registry. A text-only workflow cannot replace a required image input; insufficient reference capacity or unmapped roles blocks before submission. No silent provider/workflow substitution.

Freeze effective profile versions/digests with submitted Brief at Run. Generation tools resolve those pins without upgrading/reselecting on retry. Unavailable configuration blocks generation. Concrete defaults, workflows and live integration checks remain pending.

Declarations prove neither actual role delivery nor creative quality. Verify exact portrait-to-sheet binding and all three reference roles on the pinned live shot workflow; inspect generated results. Human review remains required. Validate concrete plans before provider effects under the [Render validation boundary](../tools/render.md#input-and-output-contract).

## Audited Workflow Profiles

Current project workflows live in [`workflow/comfyui/`](../../workflow/comfyui/); future providers use `workflow/<provider>/`. The old `docs/comfyui/workflow/` directory is retired. Bundled `skills/comfyui-skill/workflows/` files are generic toolkit examples, not active project workflows.

The profile leads below were audited 2026-09-09. Recheck mappings against the chosen current workflow file and its digest; node IDs/classes are fixture evidence, not verified endpoint capabilities.

| Profile candidate | Job | Semantic input nodes/fields | Output | Blockers |
|---|---|---|---|---|
| `krea2-txt2img` | image text-to-image | prompt `864.text`; dimensions `854.width/height`; sampler `856.seed/steps/cfg/denoise` | `851.images` and `853.image` | custom KJ/rgthree/Crystools nodes, model names, and actual links/capabilities must be verified |
| `krea2-img2img` | image reference edit | source `879.image`; resize `866.image/width/height`; prompt `876.prompt`; edit controls `875.ref_boost/ref_boost_a/fit_mode` | `873.images` and `874.image` | custom Krea/Ostris/KJ nodes, models, URL input policy, links, and output MIME are unverified |
| `minimax-h3-ref2vid` | reference-to-video | prompt/size/length `136.prompt/width/height/length`; refs `136.ref_images.ref_image_0/_1`; source images `147/148` | `157.images`; optional interpolation `158.frames` | Verify nodes, exact start-image behavior, audio, duration and output shape before MVP video activation |

These are audit leads, not registered profiles. The adapter must validate API graph shape, links, installed node schemas, model availability, output MIME, and endpoint execution before freezing a profile. No numeric capability or seed mapping is claimed from editor JSON alone.

## Workflow Submission

Use the [native HTTP path](../tools/comfyui-tool.md#native-http-path). No custom webhook is configured; a separate gateway requires verified URL/auth, payload/response, status and retry semantics while preserving job ownership and ambiguous-acceptance rules. Do not invent a `/webhook` route or require a gateway. WebSocket events are progress hints, not durable completion.

Before submission the adapter must:

1. Load the pinned trusted workflow from the project workflow registry and its explicit input/output mapping. Remove only declared top-level descriptive metadata; reject other malformed entries and broken links. Every submitted graph entry must be a node with `class_type` and `inputs`. Never send a workflow file verbatim as the HTTP body.
2. Bind all required semantic inputs to declared node fields; missing/ignored mappings are errors, not runner warnings to continue past. Materialize exact input assets using the upload response's name/subfolder and verify their identity; use isolated or content-addressed names without overwriting another job's input.
3. Resolve random seeds and all other effective parameters once. Persist the resolved node graph, mapping/workflow digests, input-asset digests and upload bindings, expected output nodes, endpoint identity, and submission correlation in restricted durable job storage before `POST /prompt`. Credentials are supplied separately. Technical retry must not rerun randomization, reload an edited workflow, or discover a different output node.
4. Persist a submission-attempt intent under job ownership before the HTTP call, then persist the response/`prompt_id` before polling. A restart between these writes is ambiguous acceptance, not an unsent job. Review requires verified outputs from the declared nodes and successful execution status, not merely HTTP 200 or a `completed` flag accompanying an execution error.

Freezing a request and seed preserves request identity, not a promise of bit-identical rerendered bytes. Model/runtime/hardware behavior may differ; exact continuity uses the stored, digest-verified candidate bytes. Never substitute a rerender under an existing candidate identity.

`client_id` correlates local events; it is not a provider idempotency key. Even a server version accepting a client-supplied `prompt_id` does not by itself promise duplicate suppression. Kinodel's operation/job key deduplicates local work, not native `POST /prompt`. Reconcile a known ID against queue/history; for a lost response, use only correlation verified on the pinned server version plus the exact prepared request. An empty history/queue after restart or eviction is not proof that submission never happened. If acceptance cannot be established, keep the job blocked; another potentially charged attempt requires the explicit authorization in [runtime.md](runtime.md#rendering-extension). Never configure automatic POST retries around this boundary. On a shared server, cancellation must target the owned job using verified supported semantics; a global queue clear/interrupt is not safe job cancellation.

The [skill](../../skills/comfyui-skill/SKILL.md) and [REST reference](../../skills/comfyui-skill/references/rest-api.md) provide toolkit guidance, not project workflow selection; their legacy `render-kinodel`/backup-provider wording does not override current service ownership. `ComfyRunner.submit()` wraps a graph for HTTP but does not implement Kinodel's durable submission protocol.

Before enabling rendering, test mapping and frozen-seed replay offline, then verify upload -> submit -> queue/history -> import on the configured server and inject a lost response/restart. Checks remain pending; no provider was executed by this documentation audit. [ComfyUI tool](../tools/comfyui-tool.md) records route sources; pin and test the deployed version rather than treating upstream behavior as its guarantee. Build acceptance lives in [Local MVP](../roadmap-mvp.md#provider-setup).

## ALM

Audio analysis may be implemented through ComfyUI when a validated workflow exists. To Kinodel it remains a typed analysis service: audio asset in, timing/section/features artifact out. The pipeline must not depend on which backend produced the analysis.

Implementation reference: `skills/comfyui-skill/`.

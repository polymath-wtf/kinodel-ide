# ComfyUI Boundary

Status: **Provider/service design**

ComfyUI is a first-class local or remote render backend. A large deterministic ComfyUI graph appears to Kinodel as one provider workflow with typed inputs, outputs, and capability metadata.

Local projects remain in SQLite/files; registration uploads neither chats nor projects. Local direct ComfyUI imports an authorized output file or native `/view` download, verifies path/ownership/job/unit/size/type/digest and publishes managed candidate files plus DB metadata; no hosted order auth or bucket upload. Provider-neutral AssetRef/RenderResult does not make local paths trusted. Remote Kinodel compute receives only selected authorized job payload, stores order metadata in PostgreSQL and workflow/input/output in private GCS. All declared remote outputs upload/verify before success; lifecycle stays 365 days. MVP service order logs/durable identities have no scheduled deletion; final retention is #todo, workflow/input/prompt-body policy separate. Remote signed URLs are transient and import verifies bytes/order/unit/generation at the project owner; browser-hosted managed files stay server-side. Paid generated downloads have no arbitrary quota, technical validation/timeouts remain. Only review/promotion advances production. Proposed [hosted order DTOs](physical-dtos.md#endpoint-wire) are not native ComfyUI routes; open retention/transport topics are in [future](../features/future.md).

## Contract

Creative agents produce provider-neutral image/video/audio intent. The ComfyUI adapter owns:

- workflow registration and versioning;
- semantic-input to node-input mapping;
- endpoint health/readiness;
- upload and asset materialization;
- submit, queue reconciliation, progress, cancellation where supported;
- output discovery, download/import, and technical audit.

## Rules

- One workflow registry is authoritative; do not duplicate aliases in Python and JSON.
- Every workflow declares accepted job kinds and required inputs.
- Workflow version participates in the render job fingerprint.
- Secrets, raw workflows, queue IDs, and logs stay out of creative artifacts.
- A local `/view` URL is a preview, not durable asset identity.
- Timeout may mean the GPU job still runs; reconcile queue/history before retry.
- Provider health checks use real readiness endpoints and do not generate paid content.

## Profile Selection

This is a deterministic adapter rule, not an LLM provider choice or a claim that working profiles are registered. A registered generation profile binds its stable ID and immutable version/digest to provider, job kind, workflow ID/version, required semantic inputs, supported workflow classes, dimensions/aspect ratios, duration/output/audio constraints, and required prompt-guidance resources. Raw workflows and semantic-to-node mappings remain in the one adapter-owned workflow registry; profiles reference them rather than copying them.

1. Validate submitted user requirements and visible defaults before Run, including provider preference. Pin Brief and registered capability/profile versions at start; no mandatory Producer or Brief review.
2. For each required image/video job kind, filter registered profiles by fixed pipeline, all explicit requirements, effective defaulted settings, and capabilities. `comfyui provider` requires ComfyUI for both image and video here; it supplies neither workflow nor profile IDs. An explicit profile must itself pass these checks.
3. Keep a compatible explicitly requested profile. Otherwise select the compatible profile designated by the supplied defaults for that job kind/provider; if there is no designated default, select only when exactly one compatible registered profile remains. Multiple remaining choices require focused clarification or block, never arbitrary registry order or an LLM guess. A designated but missing/incompatible default is a configuration failure, not permission to substitute another profile.
4. Validate every enabled role: portrait generation, portrait-conditioned sheet, character-free location and multi-reference shot frames; add video/start-image compatibility only for graphs enabling `i2v`. A profile may bind distinct versioned workflows for these roles. Declare named input/output schemas, role mappings and cardinality in the existing workflow registry. A text-only workflow cannot replace a required image input; insufficient reference capacity or unmapped roles blocks before submission. No silent provider/workflow substitution.

Freeze effective profile versions/digests with submitted Brief at Run. Generation tools resolve those pins without upgrading/reselecting on retry. Unavailable configuration blocks generation. Concrete defaults, workflows and live integration checks remain pending.

The first anchor sequence generates one portrait candidate, binds its exact bytes/digest to the sheet request, then generates an independent location, without intermediate human selection. Verify that binding and all three reference roles on the actual shot workflow. A new seed is an explicit regeneration, not technical retry; changed parent images require new dependent requests. Broader text/image/video/audio combinations follow the same [Render port contract](../agents/render.md), not planner-name branches in the provider adapter.

The visible service node exposes semantic typed ports; these declarations do not prove the deployed workflow maps or uses them correctly. Multiple named image inputs prove neither preservation of character identity nor creative quality: verify actual role delivery on the pinned live workflow and inspect portrait-to-sheet and multi-reference shot results. Human review remains required. Static preflight checks registered declarations; concrete generated plan values, reference counts, access and dependencies are checked before provider effects under the [Render validation boundary](../agents/render.md#input-and-output-contract).

## Workflow Submission

## Audited Workflow Profiles

Audited 2026-09-09 from the bundled API-format JSON files. Node IDs/classes are fixture evidence, not verified endpoint capabilities.

| Profile candidate | Job | Semantic input nodes/fields | Output | Blockers |
|---|---|---|---|---|
| `krea2-txt2img` | image text-to-image | prompt `864.text`; dimensions `854.width/height`; sampler `856.seed/steps/cfg/denoise` | `851.images` and `853.image` | custom KJ/rgthree/Crystools nodes, model names, and actual links/capabilities must be verified |
| `krea2-img2img` | image reference edit | source `879.image`; resize `866.image/width/height`; prompt `876.prompt`; edit controls `875.ref_boost/ref_boost_a/fit_mode` | `873.images` and `874.image` | custom Krea/Ostris/KJ nodes, models, URL input policy, links, and output MIME are unverified |
| `minimax-h3-ref2vid` | reference-to-video | prompt/size/length `136.prompt/width/height/length`; refs `136.ref_images.ref_image_0/_1`; source images `147/148` | `157.images`; optional interpolation `158.frames` | Verify nodes, exact start-image behavior, audio, duration and output shape before MVP video activation |

These are audit leads, not registered profiles. The adapter must validate API graph shape, links, installed node schemas, model availability, output MIME, and endpoint execution before freezing a profile. No numeric capability or seed mapping is claimed from editor JSON alone.

The requested integration is an HTTP submission of `workflow.json` to ComfyUI. No custom webhook is configured or specified yet. Native local ComfyUI already provides `POST /prompt`: send a JSON body `{"prompt": <resolved API-format node graph>, "client_id": <persisted client identifier>}`, not a filename, multipart workflow upload, or editor-format `nodes`/`links` document. Record the returned `prompt_id`; inspect `GET /queue` and `GET /history/{prompt_id}`, then fetch declared outputs through `/view`. WebSocket events are optional progress hints, not durable completion. Cloud/proxy paths and authentication must be verified for the deployed endpoint rather than copied from local examples.

If "webhook" means a separate gateway rather than this native HTTP route, its URL, authentication, payload/response, status lookup, and retry semantics remain deployment inputs. Do not invent a `/webhook` endpoint or insert a gateway as a mandatory layer. Any configured gateway must preserve the same job ownership and ambiguous-acceptance rules below.

Before submission the adapter must:

1. Load the pinned trusted workflow and its explicit input/output mapping. Remove only known top-level descriptive metadata (the bundled Flux example has `_comment`); reject other malformed entries and broken links. Every submitted graph entry must be a node with `class_type` and `inputs`. Never send the example JSON verbatim as the HTTP body.
2. Bind all required semantic inputs to declared node fields; missing/ignored mappings are errors, not runner warnings to continue past. Materialize exact input assets using the upload response's name/subfolder and verify their identity; use isolated or content-addressed names without overwriting another job's input.
3. Resolve random seeds and all other effective parameters once. Persist the resolved node graph, mapping/workflow digests, input-asset digests and upload bindings, expected output nodes, endpoint identity, and submission correlation in restricted durable job storage before `POST /prompt`. Credentials are supplied separately. Technical retry must not rerun randomization, reload an edited workflow, or discover a different output node.
4. Persist a submission-attempt intent under job ownership before the HTTP call, then persist the response/`prompt_id` before polling. A restart between these writes is ambiguous acceptance, not an unsent job. Review requires verified outputs from the declared nodes and successful execution status, not merely HTTP 200 or a `completed` flag accompanying an execution error.

Freezing a request and seed preserves request identity, not a promise of bit-identical rerendered bytes. Model/runtime/hardware behavior may differ; exact continuity uses the stored, digest-verified candidate bytes. Never substitute a rerender under an existing candidate identity.

`client_id` correlates local events; it is not a provider idempotency key. Even a server version accepting a client-supplied `prompt_id` does not by itself promise duplicate suppression. Kinodel's operation/job key deduplicates local work, not native `POST /prompt`. Reconcile a known ID against queue/history; for a lost response, use only correlation verified on the pinned server version plus the exact prepared request. An empty history/queue after restart or eviction is not proof that submission never happened. If acceptance cannot be established, keep the job blocked; another potentially charged attempt requires the explicit authorization in [runtime.md](runtime.md#rendering-extension). Never configure automatic POST retries around this boundary. On a shared server, cancellation must target the owned job using verified supported semantics; a global queue clear/interrupt is not safe job cancellation.

The local [Flux example](../../skills/comfyui-skill/workflows/flux_dev_txt2img.json) maps prompt to `6.inputs.text`, seed to `25.inputs.noise_seed`, dimensions to `27.inputs.width/height`, and output to node `9` (`SaveImage`). It has no input-image node and produces no video. It is evidence for API-format text-to-image mapping, not a registered cinematic profile or a substitute for reference-conditioned frames and an `i2v` workflow. The [skill](../../skills/comfyui-skill/SKILL.md) and [REST reference](../../skills/comfyui-skill/references/rest-api.md) are toolkit evidence; their legacy `render-kinodel`/backup-provider wording does not override current service ownership. `ComfyRunner.submit()` wraps a graph for HTTP but does not implement Kinodel's durable submission protocol.

Before enabling rendering, test mapping and frozen-seed replay offline, then verify upload -> submit -> queue/history -> import on the configured server and inject a lost response/restart. These checks and actual workflows remain pending; no provider was executed by this documentation audit. Native route reference: [ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes), [API examples](https://docs.comfy.org/development/comfyui-server/api-examples). Pin and test the deployed server version rather than treating current upstream behavior as its guarantee.

## ALM

Audio analysis may be implemented through ComfyUI when a validated workflow exists. To Kinodel it remains a typed analysis service: audio asset in, timing/section/features artifact out. The pipeline must not depend on which backend produced the analysis.

Implementation reference: `skills/comfyui-skill/`.

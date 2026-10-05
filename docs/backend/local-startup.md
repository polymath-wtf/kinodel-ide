# Local Startup And Ownership

Status: **Accepted rules; data-root lock, application/saver SQLite preflight, internal Story HTTP lifespan/shutdown and forced-process-death Story recovery tested on Windows. Launcher and full cinematic acceptance pending.** This page owns safe process/data lifetime. Installation tasks, package versions and all first-build checks live in [Local MVP](../roadmap-mvp.md).

## First Launch

Windows `.bat` and Linux shell launchers call the same Python startup core. Resolve paths from the installation, not the current shell directory. Require supported Python with venv/SQLite and useful diagnostics for missing prerequisites; SQLite needs no server.

1. Hold an OS-backed bootstrap lock before creating/changing the private `.venv`; never mutate an environment used by a live app. Install only the pinned release dependencies, display progress and stop on error. No global pip, elevation, implicit `git pull` or upgrade to latest.
2. Run the app using the environment's explicit interpreter path. The app acquires the data-root lock **before** opening DBs, migrations, checkpointer setup or workers. Project data lives outside `.venv`.
3. Initialize only a fresh root or recorded incomplete fresh installation. On existing data, check application/saver DB identity, required tables, integrity and version compatibility before any saver call that might auto-create tables. Missing/corrupt/newer data blocks; never reset to make startup pass.
4. After preflight, permit normal upstream saver setup. Reconcile unfinished work, bind loopback, then expose readiness and open the browser. A provider outage is shown as unavailable generation, not a reason to erase or hide saved projects.

Venv updates and existing-data migrations are explicit maintenance operations. A failed partial update keeps workers disabled until a tested continuation succeeds. No atomic migration across separate DB files or destructive rollback is assumed.

## Process Lock

One permanent lock file in the actual local data root, one retained non-inherited descriptor, one owning app process. Linux can use `fcntl.flock`; Windows `msvcrt.locking` on a byte at offset zero. Open without truncation; never unlink/replace the file, even after exit. A PID or elapsed heartbeat is diagnostic, not permission to evict a live owner.

Second launch refuses cleanly. Lock/permission/I/O errors never fall back to unlocked operation. Resolve path aliases to the same root; reject redirected lock files or databases shared between roots. Network and cloud-synced data directories are unsupported. An independently copied root is not protected by the original root's lock; stop the source before manual transfer.

## Runner And Shutdown

API, graph runner and saver live in the lock-owning process. One active graph invocation at a time; short application transactions, no DB transaction around a model/provider wait. Separate application commits and checkpoints recover through operation receipts under [runtime](runtime.md), not a fictitious shared transaction.

Shutdown stops commands/claims, stops or drains bounded model/tool tasks, flushes saver work, closes DBs, and releases the data lock last. If writers cannot stop within the bound, terminate the app rather than release ownership with live writers. DB/busy/disk-full errors stop effects with a recoverable diagnostic.

Installer and ffmpeg subprocesses must not outlive their supervising lifecycle uncontrolled. Before enabling them, implement tested process-tree cleanup on each OS (for example Windows Job Objects); POSIX groups alone are not proof of parent-death cleanup. An alternative installer must retain its own bootstrap lock until it exits. ffmpeg writes isolated attempt files, never canonical DB bindings. An independently running ComfyUI is an external provider: reconcile its jobs rather than killing its server.

## Internal Story API Prototype

From the repository root on Windows, with `.venv313` installed:

```powershell
.\.venv313\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --workers 1 --no-proxy-headers
```

From `web/`, run `npm ci; npm run typecheck; npm run build` before starting the backend; use `npm run build:watch` for rebuilds during development and reload the same origin (no dev proxy/CORS relaxation). Open `http://127.0.0.1:8765/` or `/?execution=<canonical UUID>` for the Story workspace, `/docs` for the API schema. Missing build gives a 503 guidance page; `/api/session` remains available. The 6D client supports start/question/revision/exact approval/Retry/Cancel with persist-before-POST delivery and session renewal after restart ([frontend instructions/checks](../../web/README.md)). Click «Новая тестовая Story», enter an idea and explicit shot IDs such as `s1, s2`, then create the run. The API serves the **internal deterministic Story fixture**, not a public cinematic Run.

Data defaults to `<installation>/stuff` (`D:\Ai\kinodel-ide\stuff` here), not the shell directory. Both SQLite databases and their WAL/SHM files, lock and bootstrap markers live at this root; project JSON/media lives in `stuff/projects/<project_id>/`. Generated data is ignored by Git. An explicit absolute `KINODEL_DATA_ROOT` may isolate checks outside source/venv paths or under `stuff`. One process owns this root; a second refuses startup. Stop with Ctrl+C, then restart with the same command to inspect the same execution and versions. Before transferring existing data, stop the source backend and move the complete root contents together, including both DBs, any remaining sidecars, markers and `projects`; verify SQLite integrity and committed artifact digests before reopening. Do not start an empty replacement root before the transfer or merge independently initialized databases.

Before using the command/read endpoints, call `GET /api/session` from the same origin to receive an HttpOnly local session cookie and a `csrf_token` in JSON. Send both on each POST, using `X-Kinodel-CSRF` for the token; reads require the cookie. For example in PowerShell:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$csrf = (Invoke-RestMethod -Uri http://127.0.0.1:8765/api/session -WebSession $session).csrf_token
$body = @{project_id = [string][guid]::NewGuid(); client_key = 'story-1'; input_message = 'A fox at dusk'; shot_ids = @('s1')} | ConvertTo-Json
$receipt = Invoke-RestMethod -Uri http://127.0.0.1:8765/api/executions/internal-story -Method Post -WebSession $session -Headers @{'X-Kinodel-CSRF'=$csrf} -ContentType application/json -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/executions/$($receipt.execution_id)" -WebSession $session
```

The response contains the actionable `review` (once ready), `work` status, `stories` including historical bodies and persisted `discussion`. The API schema documents `respond` (`approve`, `revise`, `clarify`), `retry` and `cancel`. Bind Uvicorn to `127.0.0.1:8765` as shown; peer, Host and Origin checks also reject nonlocal requests. The session expires on process restart; bootstrap it again after reopening.

For the first connected Story client, authenticated `GET /api/executions?limit=20` returns `{items:[{execution_id,project_id,input_preview,status,current_story}]}` (limit 1–100, newest **created** first, internal graph only). `current_story` is `{ref,version,current}` or null. Authenticated `GET /api/executions/{execution_id}/projection` returns `execution_id,project_id,status,outcome,submitted,graph,work,stories,reviews,review,remaining_actions,allowed_actions`; unknown/non-internal IDs return 404. `submitted` is the frozen `{input_message,shot_ids,client_key,start_digest}`; `graph` is `{id,version,digest}`. Graph fields show **raw recorded** identity, not validation that the frozen graph is supported or intact: an unsupported digest remains visible with blocked work. Each Story is `{ref,version,current}`; a version without committed operation evidence can be null. Each ordered review is `{request_id,digest,revision,binding_revision,previous_request_id,base_ref,accepted,applied,decision_id,work_id,action,message,result}`. `base_ref` pins the exact request subject; `result` is null until committed and otherwise `{kind,ref,response}`, where `kind` is `revised_story`, `owner_response` or `approved_subject`. `applied` means the decision route committed, **not** that the owner finished. `review` has the existing `{request_id,digest,revision,binding_revision,subject_artifact_id}` shape only when actionable; use its `binding_revision` for `respond.expected_revision`. `remaining_actions` is `{revise,clarify}`; `allowed_actions` contains only currently acceptable review actions. A completed outcome is the approval authority. Both new reads use DB metadata only and do not verify Story bytes: load and verify a selected body with the existing `/stories/{artifact_id}` endpoint before permitting approval in the UI. The existing full execution read still loads every Story body and may fail if one is damaged; projection/list and Cancel do not depend on them.

Metadata read DTO validation happens inside the HTTP error boundary: invalid recorded metadata or inconsistent review-result provenance returns **409** with `detail`, not an unhandled 500. Owner results must match the applied decision and prepared operation's exact request, action, base ref, feedback and binding revision; activation alone is not proof. `owner_response` requires a valid action-compatible `OwnerResponseV1`; a stored JSON `null` is damage, not an unfinished response. A genuinely unfinished owner operation keeps `result=null`, while a committed ready revision needs no separate response. List reads do not validate historical reviews, and raw recorded graph identity remains inspectable.

## Live Storytell Text Slice

To explicitly use the model settings already written in the repository `.env`, run from the repository root:

```powershell
.\.venv313\Scripts\python.exe -m backend.launch --env-file .env
```

There is still **no automatic `.env` loading** in the API. The optional launcher allowlists `OPENROUTER_API_KEY`, `LLM_MODEL`, `COMFYUI_LOCAL_ENDPOINT`, `COMFYUI_SERVER_ENDPOINT`, `COMFYUI_CONNECTION`, `COMFYUI_AUTH_TOKEN` and `COMFYUI_CA_FILE`. It supports plain or quoted assignments, does not evaluate/interpolate values, never prints them, and preserves existing process-environment values. Optional ComfyUI values may be empty; selected configuration is validated only when preflight is requested, not during saved-project startup. Without `--env-file`, use the existing Uvicorn command and exported environment. No new dependency, environment installation, release launcher or browser-opening mechanism is introduced.

In the workspace choose **«Начать историю»** or **«Новая история»**. Both, including the empty Brief action, open live Storytell by default; a fixture must be selected explicitly under **«Для проверки»**. The browser reads safe server configuration presence/model (not credentials); missing configuration disables live Start with explicit launcher/environment guidance, never a silent substitute. Submit an idea, 1–8 explicit shot keys, up to 16 explicitly declared subjects (`id: description`, one per line), and a visible per-shot duration (default 5000 ms, allowed 1–60000). An empty subject list means an environment-only story; subjects are not extracted or invented by the backend. These fields form `StoryTextInputV1`, a bounded narrative experiment, **not a public cinematic Brief or a render profile**. Only these inputs, the selected Storytell prompt, exact prior Story and bounded relevant discussion/feedback go to OpenRouter; no project/library upload or arbitrary retrieval.

`POST /api/executions/live-story` accepts `{project_id,client_key,input_message,shot_ids,subjects:[{subject_id,description}],shot_duration_ms}` with the same session/CSRF boundary and durable receipt as the fixture. Fresh starts verify public model metadata; unavailable IDs/capabilities block acceptance without substitution. Same-key/same-submission replay uses the original frozen configuration even if the environment changes or credentials are absent. Projection/list/body/controls support both frozen graph identities. Live projections additionally expose `model` and `submitted.text_brief`; fixture projections have null values. The original `/internal-story` command, identity and deterministic owner remain available.

The live graph is **`kinodel.live-story` v1**, with the existing review route and **approve → END**, not Wardrobe. Schema v10 preserves older rows and adds execution-owned frozen model/prompt/schema/input settings plus operation-owned exact model requests/digests and durable attempt counters. Prepared operation digests include the owner configuration pin. Replays never re-read changed prompts, reselect context or redo a committed result. Checkpoints still contain compact refs, not prompts or bodies.

Authenticated `GET /api/story-availability` returns `{configured,model,reason}` from the server environment without reading `.env` or calling a provider. It reports local configuration presence only; fresh Start remains the remote model-capability check. Authenticated `GET /api/executions/{id}/story-activity` returns `{model,system_prompt,prompt_digest,tools:[],operations}` from recorded frozen configuration/operations; fixture returns JSON null, unknown execution 404, corrupt live activity 409. Each operation exposes `{operation_id,action,status,reserved_attempts,repairs,input,story_ref,response}`. Input is the recorded **base** user task, not a claimed per-attempt wire trace; repair count indicates additional format instructions. Outputs are validated saved Story refs or owner explanations, not raw OpenRouter envelopes/private reasoning. Attempt reservation proves neither acceptance nor response; no timing/token/provider-receipt data is invented. Activity read errors do not replace the independent status/body/control reads. No migration, graph routing or command semantics changed for visibility.

Tested model: **`z-ai/glm-5.3-flash`**. Public metadata advertises structured outputs and mandatory reasoning; the frozen profile uses **low** reasoning, not disabled reasoning. Each HTTP call has a **60 s total bound / 8192 completion-token cap**, with **two durable attempt reservations and at most one structured repair per operation**. Transport/408/429/5xx failures block as `owner_unavailable`; an exact OCC/deduplicated Retry authorizes a fresh two-attempt allowance without resetting the lifetime repair counter or changing inputs. Invalid/exhausted structured output, configuration/integrity errors and initial `needs_input`/`out_of_scope` block without a Story; a valid initial explanation is not repaired into invented readiness. At an existing review, clarify and non-ready revise persist an explanation and open a new request on the unchanged Story as before. Cancellation stops active HTTP awaits and prohibits later bindings.

Live acceptance and known output-repair limits are recorded under [Local MVP step 3](../roadmap-mvp.md#remaining-steps); the opt-in paid browser check is documented in [web/README.md](../../web/README.md#opt-in-paid-smoke). Wardrobe, full Brief and media integration remain pending.

## ComfyUI Read-only Connection

Production draft diagnostics are separate: guarded `GET /api/production/profiles`, `POST /api/production/validate` and `POST /api/production/image-only/validate` never call ComfyUI or create executions. In the workspace choose **Новая история → Настройки фильма** for the persisted cinematic draft; it shows total/per-shot duration, modes and unavailable profiles, with Run disabled. [Contracts and acceptance](../roadmap-comfyui.md#3-production-settings-и-профильные-ограничения).

The existing launcher also loads the explicit ComfyUI settings above. `local` is the default connection; `COMFYUI_CONNECTION=server` or an explicit preflight selection uses `COMFYUI_SERVER_ENDPOINT`, with no outage fallback. HTTP/HTTPS and an optional native path prefix are supported. Bearer auth is supplied by `COMFYUI_AUTH_TOKEN`; an absolute `COMFYUI_CA_FILE` configures trusted certificates without disabling TLS verification.

Check the external server without opening project databases or generating content:

```powershell
.\.venv313\Scripts\python.exe -B -m backend.comfyui --env-file .env --connection local
.\.venv313\Scripts\python.exe -B -m backend.comfyui --env-file .env --connection server
```

An optional `--workflow "qwen img2img api v1.1 3img.json"` selects a declared registry candidate; default is `txt2img krea2 api v1_local.json`. Every candidate is exact-file SHA-pinned; a changed file blocks before networking until its registry version is updated after audit. Exit 0 means required node classes/exact models were found and, for the two preparation-enabled image templates, the graph passed installed-schema/mapping validation. It does not prove rendering or measured geometry. Four inspection-only candidates have no graph-readiness claim. Failure returns typed, sanitized issues and nonzero exit status. The CLI never auto-loads `.env`.

After `GET /api/session`, guarded `GET /api/comfyui/workflows` returns `{items:[<basename>,...]}` without networking. Guarded `GET /api/comfyui/preflight?connection=local` (or `server`, optional `workflow` query) returns the same typed report; dependency failures remain HTTP 200 with `dependencies_ready=false` and actionable `issues`, invalid connection query is 422. `workflow_id/version`, `registry_sha256` and `preparation_enabled/graph_ready` identify registry and graph checks; dependency readiness is still inventory-only and may be true alongside graph_ready=false. Graph readiness is null if not checked. The report includes endpoint/workflow digests, real reported runtime versions, GPU/VRAM, used classes/schema digests and exact selected model availability, with explicit unknowns; credentials, endpoint URL, private paths and raw graphs/mappings/schemas/responses/argv are omitted. Startup and saved Story reads never trigger this probe. [Step-1 evidence](../roadmap-comfyui.md#1-подключение-и-read-only-preflight), [image preparation/limits](../roadmap-comfyui.md#2-один-registry-и-image-workflows).

## Acceptance Gate

See [Local MVP acceptance](../roadmap-mvp.md#acceptance) for installation, process death, concurrent launch, existing-store preflight, shutdown and storage-failure checks. This protocol is not proof that any platform already passes them. Automated backup/restore is separate from restart durability.

## Sources

[Python venv](https://docs.python.org/3.13/library/venv.html), [fcntl](https://docs.python.org/3/library/fcntl.html), [msvcrt](https://docs.python.org/3/library/msvcrt.html), [SQLite PRAGMAs](https://www.sqlite.org/pragma.html), and the local saver source in the optional ignored `.reference/langgraph` checkout. Validate behavior against the installed versions; reference checkout is not the running application.

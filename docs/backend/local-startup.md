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

From `web/`, run `npm ci; npm run typecheck; npm run build` before starting the backend; use `npm run build:watch` for rebuilds during development and reload the same origin (no dev proxy/CORS relaxation). Open `http://127.0.0.1:8765/` for the built shell or `/docs` for the local API schema. If the build is missing, `/` gives a 503 guidance page; `/api/session` remains available. The shell is not yet connected to reads or commands ([frontend instructions](../../web/README.md)). The API serves the **internal deterministic Story fixture**, not a public cinematic Run. Data defaults to `%LOCALAPPDATA%\Kinodel`; set `KINODEL_DATA_ROOT` to an absolute local path outside the checkout before starting if you need a separate root. One process owns this root; a second instance refuses startup. Stop with Ctrl+C, then restart with the same command to inspect the same execution and its versions.

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

## Acceptance Gate

See [Local MVP acceptance](../roadmap-mvp.md#acceptance) for installation, process death, concurrent launch, existing-store preflight, shutdown and storage-failure checks. This protocol is not proof that any platform already passes them. Automated backup/restore is separate from restart durability.

## Sources

[Python venv](https://docs.python.org/3.13/library/venv.html), [fcntl](https://docs.python.org/3/library/fcntl.html), [msvcrt](https://docs.python.org/3/library/msvcrt.html), [SQLite PRAGMAs](https://www.sqlite.org/pragma.html), and the local saver source in the optional ignored `.reference/langgraph` checkout. Validate behavior against the installed versions; reference checkout is not the running application.

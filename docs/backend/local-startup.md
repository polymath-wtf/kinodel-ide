# Local Startup And Ownership

Status: **Accepted rules; launcher implementation pending.** This page owns safe process/data lifetime. Installation tasks, package versions and all first-build checks live in [Local MVP](../roadmap-mvp.md).

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

## Acceptance Gate

See [Local MVP acceptance](../roadmap-mvp.md#acceptance) for installation, process death, concurrent launch, existing-store preflight, shutdown and storage-failure checks. This protocol is not proof that any platform already passes them. Automated backup/restore is separate from restart durability.

## Sources

[Python venv](https://docs.python.org/3.13/library/venv.html), [fcntl](https://docs.python.org/3/library/fcntl.html), [msvcrt](https://docs.python.org/3/library/msvcrt.html), [SQLite PRAGMAs](https://www.sqlite.org/pragma.html), and the local saver source in the optional ignored `.reference/langgraph` checkout. Validate behavior against the installed versions; reference checkout is not the running application.

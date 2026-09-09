# Local Startup And Ownership

Status: **Accepted installation goal; proposed physical protocol, unimplemented.** Research checked 2026-09-09. This page refines [runtime ownership](runtime.md#single-writer-ownership), not a claim that `main.py` or a launcher exists.

## First Launch

Accepted targets: Windows and Linux; macOS is not a current target. Clone the repository, launch `main.py` or a small Windows `.bat` / Linux shell launcher, see preparation progress, then the welcome screen. Both launchers use the same Python core; OS lock/process supervision and dependency installation details differ. Download Python requirements into an isolated venv automatically. SQLite is an embedded library exposed by Python's `sqlite3`, not a database server to install or administer.

Proposed bootstrap sequence:

1. Resolve paths from the launcher location, not the shell's current directory. Check supported Python (backend baseline 3.12), `venv`, `ensurepip`, `sqlite3`, writable space and the dependency manifest. Git is a prerequisite for cloning, not every application start. Missing Python needs an actionable installation message; stdlib cannot install the interpreter that must run it. Supported OS versions/architectures and release distribution of the web UI remain Q1.
2. Acquire a bootstrap OS lock beside the clone's private venv, before creating or modifying it. Never mutate an environment used by a running application. The launcher must supervise the entire installer/consumer lifetime: the app remains its supervised child, and launcher exit must terminate that process tree and release the lock. A parent-held lock alone is insufficient if the child survives. On Windows this requires a tested Job Object with kill-on-close (or equivalent). POSIX parent-death behavior remains #todo: a process group or watchdog alone does not guarantee cleanup. `wait` alone is not acceptance.
3. On a fresh install create `.venv` with isolated packages, install the release's pinned requirements using that venv's Python, verify dependencies, then mark its exact requirements digest ready. Do not use global pip, elevate privileges, execute a remote install script, `git pull`, or upgrade to latest packages implicitly. On failure, stop before opening project data; retry only the incomplete venv setup. Existing ready environment with another manifest requires explicit update, not silent replacement.
4. Launch the application with the venv interpreter by its full path; activation scripts and PowerShell execution-policy changes are unnecessary. The bootstrap process never opens the Project DB. The application itself acquires the data-directory lock before SQLite open, migration, saver setup or worker startup. There is no unlock/relock handoff of data ownership between launcher and worker.
5. Under data ownership, distinguish a fresh empty data root from an existing installation. Initialize missing databases only for a fresh root or a recorded incomplete fresh setup. Before the first saver call (including reads that auto-run setup), preflight existing DB identity, integrity, required tables/schema and compatibility with the pinned application/saver versions. Missing DB or required saver tables in an existing store is an integrity error, not permission for auto-setup to recreate them. A newer/unknown version, interrupted unsupported migration or incompatible frozen graph blocks startup with a recoverable diagnostic. After preflight, normal upstream idempotent setup is allowed, including internal `CREATE TABLE IF NOT EXISTS`; do not disable it or introduce a custom saver merely to avoid it.
6. Existing-data migration is an explicit maintenance update with a displayed source/target version. Each application migration and its version receipt commits together where SQLite permits. Check saver compatibility against the pinned package's actual schema/setup mechanism; do not assume or invent a SQLite saver migration journal. There is no claimed atomic transaction across two DB files. If one completes and the other fails, keep workers disabled and continue only the tested migration path on the next launch. Never reset a database to make startup pass. With no MVP automated backup, decline destructive/unsupported upgrades rather than invent rollback safety.
7. Verify FK enforcement on every application connection, configured journaling/synchronous behavior, schema integrity and required pinned graph/resources. Reconcile unfinished operations/checkpoints before enabling production commands. Bind only loopback; expose readiness and then open the browser. A failed readiness check must not open a misleading working screen.

The venv is disposable and recreated after relocation. Project data is not stored in it. A clone-local bootstrap lock does not protect a data root opened by a second clone; the application's data lock does. Minimal ordering is bootstrap lock, then data lock; never acquire in reverse. Do not expose multi-worker/reload flags in the local launcher.

## Process Lock

**Recommendation:** one permanent lock file at the actual data root, held by the application process on one retained non-inherited descriptor for its entire lifetime. Use existing stdlib APIs for the first supported OS pair, not a PID file or a lease service.

| Platform | Proposed primitive | Required details |
|---|---|---|
| Linux | `fcntl.flock(fd, LOCK_EX | LOCK_NB)` | Open read/write without truncate; retain the descriptor. Linux flock belongs to the open file description; fork/dup copies can keep it alive. macOS support is outside the current target |
| Windows | `msvcrt.locking(fd, LK_NBLCK, 1)` at offset zero | Binary read/write open without truncate; seek zero before acquire/release; the byte range may extend past EOF. Retain the descriptor and do not reopen it for lock operations. This is a CRT byte-range lock, not a claim to call LockFileEx directly |

An unavailable lock means another owner or OS cleanup is in progress: refuse startup with the root displayed. Permission/unsupported-filesystem/I/O errors are separate diagnostics, never an unlocked fallback. PID, host and start time may be diagnostic metadata, but are never proof of ownership, grounds for eviction or a kill target. Stale PID reuse is harmless because only kernel acquisition authorizes entry.

Never delete, replace, truncate or rotate the lock file, including after normal exit. Deleting a held POSIX file allows a second inode at the same pathname and two apparent owners. After process death the OS releases ownership once relevant handles are gone; the remaining file is expected, not a stale lock to remove. OS cleanup need not be instantaneous. Do not evict a hung live owner by timeout; ask for application shutdown, then retry actual acquisition.

Resolve symlink/junction/path aliases to the same local root and lock the actual file there; do not name locks from a hash of the input path string. Restrict the root to the OS user. Reject a lock file redirected outside the root. Existing DB/files must not be shared via hard links, symlinks or configurable external paths between two different data roots. A copied root has an independent lock: local locks cannot prevent two writable restored copies on different machines. Manual transfer requires stopping the source; automatic sync, NFS/SMB/FUSE/network shares and cloud-synced folders are unsupported. Canonical path resolution is not a defense against a malicious process running as the same OS user.

## Runner And Shutdown

The local API and one background graph runner execute in the lock-owning application process. No surviving child may invoke LangGraph, migrate, write checkpoints or publish canonical artifacts after this process dies. Blocking SQLite work must not freeze the event loop. Short application write transactions serialize OCC/cancel/result changes; no transaction spans a model or network call. A proposed bounded busy timeout is 5 seconds per connection, followed by a typed retryable storage error, not an endless retry loop. This number is a tunable release default to test, not ownership or a durability guarantee.

Shutdown stops command acceptance and claims, cancels/awaits bounded graph/model tasks, stops and joins saver work/threads, closes DB connections, then releases the data lock last. Failed saver/DB handling stops new effects and leaves durable work recoverable. If bounded shutdown cannot stop all writers, terminate the application, do not release ownership and keep running tasks.

Foundation launches no write-capable child workers. Bootstrap pip children may modify only the isolated environment and must be supervised; a killed bootstrap must not leave pip racing a new install. Before enabling bootstrap subprocesses, prove process-tree cleanup on each supported OS, or keep incomplete environments unavailable while the installer child owns their bootstrap lock. Do not claim that `subprocess` alone kills children on parent death. Later ffmpeg/managed local provider processes need verified supervision (Windows Job Object kill-on-close or a tested POSIX parent-death/watchdog arrangement) and isolated attempt output; they never write canonical metadata. An independently running user ComfyUI is an external provider, not a graph writer; its jobs require reconciliation.

SQLite saver and application commits remain separate even in one process. A lock plus busy timeout does not make them one transaction. Recover through operation receipts and pending checkpoint writes under [runtime.md](runtime.md). Server PostgreSQL retains the same-session advisory-lock/saver design; it is not replaced by this local file lock.

## Acceptance Gate

All checks are **#todo** on both Windows and Linux, not performed by this research:

| Check | Required observation |
|---|---|
| Fresh machine, path with spaces/non-ASCII, missing Python/network/disk | Useful progress/error; no global package changes, no empty replacement DB |
| Two concurrent launchers / two clones, same root via alias | At most one installer per venv and one application per root; loser never migrates |
| Kill during install/migration/LLM/business commit/saver write | No survivor writes; restart reacquires real ownership and recovers or blocks, never resets |
| Live owner with old PID/heartbeat; dead owner with lock file retained | Live cannot be displaced; dead can restart without deleting the file |
| SQLite busy, disk full, saver exception, hung shutdown | Bounded error; no post-release canonical writes; no lost accepted work |
| Newer DB or changed frozen graph/resource | Refuse unsafe startup/resume, preserve data |
| Existing saver DB missing required tables; intact compatible saver on restart | Preflight rejects before any auto-setup call; intact store permits normal idempotent setup without reset |

Automated backup scheduling, RPO/RTO and disk-loss recovery drills are **#future production**. A complete stopped-installation manual transfer remains a separate requirement, not an MVP backup subsystem. Without an independent copy, disk loss can lose all local work. Process restart durability still blocks release.

## Sources

Checked 2026-09-09, documentation only:

- [Python 3.12 venv](https://docs.python.org/3.12/library/venv.html): existing interpreter prerequisite, isolated packages, direct interpreter use, nonportable environments.
- [Python fcntl](https://docs.python.org/3/library/fcntl.html), [Linux flock](https://man7.org/linux/man-pages/man2/flock.2.html): nonblocking kernel locks, descriptor lifetime and network limitations.
- [Python msvcrt](https://docs.python.org/3/library/msvcrt.html), [Windows LockFileEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex): byte-range semantics and OS cleanup; not a tested cross-platform wrapper.
- [SQLite PRAGMAs](https://www.sqlite.org/pragma.html): busy timeout, connection FK enforcement, user version and separate integrity/FK checks.
- [Upstream AsyncSqliteSaver source](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/aio.py), rechecked 2026-09-09: reads/writes call automatic setup, which uses `CREATE TABLE IF NOT EXISTS` and an instance setup guard, not a migration journal. This moving source is evidence, not a pinned-version integration test.

No new lock dependency is required by the current recommendation. Add a small maintained wrapper only if the supported-platform spike shows these direct APIs insufficient; it still must not unlink held files or provide a soft/PID-only fallback.

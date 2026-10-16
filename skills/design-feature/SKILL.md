---
name: design-feature
description: Design changes in Kinodel's Python/LangGraph application using scoped C4, behavior diagrams, architecture review, human approval, then an implementation plan. Supports local fixes, refactors, optimizations and cross-layer features.
argument-hint: "[feature-name] [service-path] [description or ticket link]"
---

# Design Feature — C4 + DFD + Sequence → Code Plan

You are an expert software architect designing a feature using the C4 model with human-in-the-loop approval.

**Core principle:** Design WHAT and WHY before HOW. No code planning until architecture is approved.

**Scope principle:** Scale the documentation, not the reasoning process. For a bounded change, use a compact note or update the relevant existing documents; for a cross-layer change, use separate views below. Keep both approval gates, but summarize them proportionally. Create diagrams and conditional documents only when they clarify the change.

Use repository guidance and documentation routing to discover current architecture, tools and verification commands. Current implementations are evidence, not proof of the best design: preserve required behavior, and justify changes to patterns or contracts rather than copying them blindly. Do not assume a fixed feature, module layout or function name.

---

## Phase 0: Understand the Mission

### 0.1 Parse Arguments

- `$ARGUMENTS[0]` — feature name (slug, used for directory name)
- `$ARGUMENTS[1]` — affected scope path (service, package, frontend or repository root for cross-layer work; called `{service-path}` below)
- `$ARGUMENTS[2+]` — feature description, requirements, or ticket link (everything after service path)

Infer arguments from the request and repository when unambiguous. If essential information is missing, ask:
```
Please provide:
1. Feature name (slug, e.g. "rag-strategy")
2. Affected scope path (service, package, frontend or repository root)
3. Feature description or ticket link
```

If only feature name and service path are provided (no description), ask the user to describe the feature before proceeding.

### 0.2 Read the Feature Request

- Read the feature description/ticket provided by the user
- Understand the **business goal** — what problem does this solve?
- Identify acceptance criteria
- Determine if this touches Backend, Frontend, or infrastructure

### 0.3 Read Project Standards & Discover Codebase Structure

Read applicable repository instructions and follow the documentation index to the relevant design, implementation status and roadmap. Inspect actual entry points, dependencies and checks in the affected scope.
Separate required behavior, current implementation, proposed changes and deferred work. Resolve discrepancies with evidence; do not turn existing structure into an unquestionable constraint.
Choose compact or multi-file output and reuse existing canonical documents. Keep requirements/status, implementation plans and verification evidence in their repository-designated locations; avoid parallel sources of truth.

### 0.4 Decide if Research is Needed

Research is needed when:
- You don't know the current architecture of the affected modules
- The feature touches unfamiliar parts of the codebase
- There are existing implementations that might be reusable
- Integration points are unclear

### 0.5 Determine Feature Context

Analyze the feature to decide which **conditional documents** are needed (see Phase 2.3):

| Condition | Conditional Document |
|-----------|----------------------|
| Feature has domain events | `05-events.md` |
| Change affects persistence or serialization | `06-repo-model.md` |
| Standards need an explicit compliance comparison | `07-standards.md` |
| Change adds or modifies REST endpoints | `08-api-contract.md` |

---

## Phase 1: Research (Optional)

If research is needed, investigate the relevant questions below. When delegation is permitted by repository/user instructions and useful, assign independent questions to available research agents; otherwise research directly. Use only agent types actually available in the current environment.

Inspect only relevant mechanisms; report absent components as absent rather than adding infrastructure to match the examples.

### Research Task 1: Architecture Analysis
```
Analyze the architecture of {service-path}:

Start from these entry points:
1. Application entry points and composition — configuration, dependency wiring and lifetimes
2. Startup/recovery paths — initialization order and ownership
3. API or UI entry points — affected commands, reads and callers
4. Domain/state definitions — validation, transitions and result ownership
5. Application operations or graph definitions — affected flows and dependencies
6. Storage and external adapters — persistence, provider calls and side effects

For each relevant component, report:
- Layer and package structure
- Construction and validation patterns actually used
- Typed schemas and serialization boundaries
- Persistence and recovery patterns
- Graph/state, event or asynchronous work patterns (if relevant)

Report file:line references for all findings.
Save findings — facts only, no critique, no suggestions.
```

### Research Task 2: Pattern Discovery
```
Find patterns relevant to "{feature-name}" in {service-path}:

1. Similar features already implemented — find the closest analog and document the relevant structure
2. Reusable components in the actual shared modules — types, validation, utilities
3. API patterns — endpoint registration, request/response formats, error response structure
4. Testing patterns — test suite setup, mock patterns, stub patterns
5. Error conventions — inspect affected error definitions and callers; check identifier conflicts if new codes are needed

Report file:line references for all findings.
Save findings — facts only, no critique.
```

### Research Task 3: Integration Analysis
```
Analyze integration points for "{feature-name}":

1. External services and gateways — gRPC clients, HTTP clients, LLM pipelines
2. Event-driven communication — event bus, domain events, handlers
3. Shared types and contracts (boundary layer) — interfaces exposed to other modules
4. Persistence affected — application records, managed files, checkpoint storage and indexes, where relevant
5. Auth/middleware — how auth is applied to routes

Report file:line references for all findings.
Save findings — facts only.
```

### Save Research
After research completes, synthesize findings in the repository-designated location. For compact work, keep them in the scoped note. If no convention exists, use the following directory and template:
```bash
mkdir -p {service-path}/docs/{feature-name}
```
Save to: `{service-path}/docs/{feature-name}/research.md`

```markdown
---
date: YYYY-MM-DD
feature: {feature-name}
service: {service-path}
---

# Research: {Feature Name}

## Summary
[2-3 paragraphs: what exists, what's relevant, key patterns found]

## Project Structure (Discovered)
- **Initialization order:** [Actual startup and recovery order, with references]
- **Router pattern:** [How routes registered, middleware — reference file:line]
- **Model/state pattern:** [Construction, validation, transitions — reference closest analog file:line]
- **Persistence pattern:** [Serialization, transactions, recovery — reference file:line]
- **Error conventions in use:** [Actual identifiers, representations and caller expectations]
- **New error identifiers, if needed:** [Conflict check against existing definitions]

## Architecture Overview
[Current architecture of affected modules]

## Existing Patterns
[Patterns found that are relevant to evaluate or reuse — with file:line references]

## Integration Points
[External dependencies, gateways, events]

## Key Files
- `path/to/module.py:line` — description
```

---

## Phase 2: Design (Multi-File, View-Based)

Create the architectural design as **separate documents by view** (inspired by Kruchten's 4+1 model):
- **Logical View** = C4 (structure)
- **Process View** = DFD + Sequences (behavior)
- **Decision View** = ADRs + Risks (rationale)
- **Quality View** = Testing (verification)

For compact work, keep the relevant views as sections in the scoped note. The file tree and templates below are defaults for larger changes, not a requirement to create every file or C4 level. Follow repository documentation routing; all paths, components, schemas and error shapes in examples are illustrative, not prescribed contracts.

For Python/LangGraph changes affecting execution, identify state and durable-result owners, relevant transitions, waits and side effects. Explain checkpoint/resume/replay behavior, cancellation and recovery where affected. Before `interrupt()`, code must be pure or idempotent because the node restarts on resume. Distinguish checkpoint state from application persistence; verify version-sensitive behavior against installed packages and official documentation. Do not introduce graphs or persistence into tasks that do not need them.

### 2.1 Output Structure

```
{service-path}/docs/{feature-name}/
├── README.md              — Index + Business Context + Acceptance Criteria
├── 01-architecture.md     — C4 L1 + L2 + L3 + Module Dependencies (Logical View)
├── 02-behavior.md         — DFD + Sequence Diagrams (Process View)
├── 03-decisions.md        — Design Decisions + Risks + Open Questions (Decision View)
├── 04-testing.md          — Testing Strategy + Test Cases (Quality View)
├── 05-events.md           — Domain Events (conditional)
├── 06-repo-model.md       — Persistence and Serialization Strategy (conditional)
├── 07-standards.md        — Standards Compliance Matrix (conditional)
├── 08-api-contract.md     — HTTP API Contract (conditional, features with REST endpoints)
├── research.md            — Research (from Phase 1, if applicable)
└── plan/                  — Code Plan (added after design approval, Phase 5)
    ├── README.md          — Overview, file map, DI integration, error codes, success criteria
    ├── phase-01.md        — Phase 1 implementation details
    ├── phase-02.md        — Phase 2 implementation details
    └── phase-NN.md        — One file per implementation phase
```

**Core views:** context, architecture, behavior, decisions and verification. In multi-file mode use README.md, 01-architecture.md, 02-behavior.md, 03-decisions.md, 04-testing.md; in compact mode cover only the relevant sections in the scoped note.
**Conditional files:** 05-08, based on Phase 0.5 analysis

### 2.2 Core Document Templates

#### README.md — Index + Context

```markdown
---
date: YYYY-MM-DD
feature: {feature-name}
service: {service-path}
status: draft | reviewed | approved
research: ./research.md (if exists)
---

# {Feature Name} — Design Documents

## Business Context
[WHY this feature exists — business problem, user need, expected outcome. 1-3 paragraphs]

## Acceptance Criteria
1. [Measurable criterion 1]
2. [Measurable criterion 2]
...

## Documents

| File | View | Description |
|------|------|-------------|
| [01-architecture.md](...) | Logical | C4 diagrams (L1 → L2 → L3), module dependencies |
| [02-behavior.md](...) | Process | Data flow diagrams, sequence diagrams |
| [03-decisions.md](...) | Decision | Design decisions (ADR), risks, open questions |
| [04-testing.md](...) | Quality | Test strategy, test cases per module |
| [05-events.md](...) | — | Domain events (if applicable) |
| [06-repo-model.md](...) | — | Persistence and serialization strategy (if affected) |
| [07-standards.md](...) | — | Standards compliance comparison (if needed) |
| [08-api-contract.md](...) | — | HTTP API contract (if REST endpoints) |

[Remove rows for files that don't apply to this feature]
```

#### 01-architecture.md — Logical View (C4 L1 → L2 → L3)

Keep the relevant C4 levels in one file — they form a single "zoom-in" narrative. Omit unchanged or unhelpful levels.

````markdown
---
parent: ./README.md
view: logical
---

# Architecture: {Feature Name}

## C4 Level 1 — System Context

WHO interacts with the system and WHAT external systems are involved.

```mermaid
C4Context
    title System Context — {Feature Name}

    Person(user, "User", "Description")
    System(system, "Our System", "Description")
    System_Ext(ext, "External System", "Description")

    Rel(user, system, "Uses")
    Rel(system, ext, "Calls")
```

### Context Description
- **Actors:** [who uses this feature]
- **System boundaries:** [what's inside vs outside]
- **External dependencies:** [third-party services, APIs]

---

## C4 Level 2 — Container

WHAT services/containers are involved and HOW they communicate.

```mermaid
C4Container
    title Container Diagram — {Feature Name}

    Person(user, "User")

    Container_Boundary(system, "System") {
        Container(api, "API Service", "Python", "Handles requests")
        ContainerDb(db, "Persistence", "Project-selected storage", "Stores data")
        Container(worker, "Execution", "Python/LangGraph where applicable", "Coordinates work")
    }

    Rel(user, api, "HTTPS")
    Rel(api, db, "Read/Write")
    Rel(worker, db, "Poll/Update")
```

### Container Description
- **Services affected:** [which microservices/modules]
- **Databases:** [collections, schemas]
- **Communication:** [HTTP, gRPC, events, polling]

---

## C4 Level 3 — Component

WHAT internal components/modules handle the feature logic.
Create one subsection per major module/component.

### 3.1 [Module Name]

```mermaid
flowchart TB
    subgraph "module-name"
        subgraph "models/state"
            Entity["Entity"]
            Schema["Validated Types"]
        end
        subgraph "operations"
            UC["UseCase"]
        end
        subgraph "interfaces"
            Repo["«interface» Repository"]
        end
    end
```

**Description:** [affected models, validation, state transitions, ownership and key interfaces]

**State machine (if applicable):**
```
State1 → State2 → State3
```

### 3.N [Next Module]
[Repeat for each module]

---

## Module Dependency Graph

```mermaid
flowchart BT
    ModuleA --> SharedPrimitives
    ModuleB --> SharedPrimitives
    ModuleC --> ModuleA
```

**Rule:** [Dependency direction constraints]
````

#### 02-behavior.md — Process View (DFD + Sequences)

When sequence diagrams are useful, use one per use case (not per scenario). Group related error/edge cases under the same use case section.

````markdown
---
parent: ./README.md
view: process
---

# Behavior: {Feature Name}

## Data Flow Diagrams

### DFD 1: [Flow Name]

```mermaid
flowchart LR
    User([User]) -->|Request| API[API Endpoint]
    API -->|Validate| UC[Use Case]
    UC -->|Query| DB[(Database)]
    DB -->|Result| UC
    UC -->|Transform| API
    API -->|Response| User
```

### DFD 2: [Another Flow]
[Add more DFDs as needed — one per major feature flow]

---

## Sequence Diagrams

One diagram per use case that needs one. Show happy path, then list error/edge cases below.

### Use Case 1: [Name]

```mermaid
sequenceDiagram
    actor User
    participant Controller
    participant UseCase
    participant Repository
    participant Database

    User->>Controller: HTTP Request
    Controller->>UseCase: Execute(params)
    UseCase->>Repository: Find(id)
    Repository->>Database: Query
    Database-->>Repository: Result
    Repository-->>UseCase: Entity
    UseCase-->>Controller: Result
    Controller-->>User: HTTP Response
```

**Error cases:**
| Condition | Error Code | HTTP Status | Behavior |
|-----------|------------|-------------|----------|
| Resource not found | [Project error identifier, if used] | 404 | Return error |
| Invalid state | [Project error identifier, if used] | 409 | Return error with current state |
| Validation failed | [Project error identifier, if used] | 400 | Return field-level errors |

**Edge cases:**
- [Race condition: concurrent updates → optimistic locking]
- [Timeout: external service → circuit breaker / fallback]

### Use Case 2: [Name]
[Repeat per use case]

---

## Additional Scenarios

### [Scenario Name]
- **Trigger:** [what causes this]
- **Behavior:** [what happens]
- **Edge cases:** [race conditions, timeouts, etc.]
````

#### 03-decisions.md — Decision View (ADR + Risks)

```markdown
---
parent: ./README.md
view: decision
---

# Design Decisions: {Feature Name}

## Decisions

| # | Decision | Choice | Alternatives Considered | Rationale |
|---|----------|--------|-------------------------|-----------|
| 1 | [Decision 1] | [What was chosen] | [What else was considered] | [Why — reference file:line for codebase evidence] |
| 2 | [Decision 2] | [What was chosen] | [Alternatives] | [Why] |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | High/Medium/Low | [How to mitigate] |

---

## Open Questions

- [ ] [Unresolved question 1]
- [ ] [Unresolved question 2]
- [x] [Resolved question — **Answer**]
```

#### 04-testing.md — Quality View

````markdown
---
parent: ./README.md
view: quality
---

# Testing Strategy: {Feature Name}

## Test Rules
[Reference project test standards — test runner, fixtures, naming, etc.]
[Use applicable project test conventions discovered in Phase 0.3; explain justified departures]

## Test Structure
```
[Directory tree of test files — match project test directory structure]
```

---

## Coverage Mapping

Trace affected business rules, error behavior and state transitions to meaningful verification. Reuse existing checks; add focused tests for new behavior or consequential replay, persistence and side-effect changes. Scale checks to risk; do not create tests that merely mirror the implementation.

### Entity Coverage
| Entity | Business Rule / Invariant | Test |
|--------|---------------------------|------|
| [Model] | [Required input is validated] | `test_required_input_validation` |
| [State] | [State transition X→Y only when Z] | `test_transition_requires_condition` |
| [Operation, if affected] | [Replay does not repeat a committed side effect] | `test_replay_preserves_committed_result` |

### Error Code Coverage
| Error Code | Description | Tested by |
|------------|-------------|-----------|
| [Project identifier, if used] | [Description] | `test_operation_condition_error` |

---

## [Module 1] — Test Cases

### [Entity/Component] ([N] tests)

| Test | What it verifies |
|------|------------------|
| `test_behavior_condition_result` | [Description] |

### Stubs
- [Relevant test double] — [behavior or result it supplies]

---

## [Module 2] — Test Cases
[Repeat per module]

---

## Repo Model Round-Trip Tests (if applicable)

| Test | What it verifies |
|------|------------------|
| `test_round_trip_preserves_required_data` | Model → Stored representation → Model |

---

## Test Count Summary

| Module | Unit | Integration | Recovery (if relevant) | Total |
|--------|------|-------------|------------------------|-------|
| [Module 1] | N | N | N | **N** |
| **TOTAL** | | | | **N** |
````

### 2.3 Conditional Document Templates

#### 05-events.md — Domain Events (if feature emits events)

```markdown
---
parent: ./README.md
---

# Domain Events: {Feature Name}

| Event | Emitted when | Data |
|-------|--------------|------|
| `EventName` | [Trigger] | [Fields] |

## Implementation Pattern
[How events are defined, published, consumed — reference existing event patterns at file:line]
```

#### 06-repo-model.md — Persistence and Serialization Strategy (if affected)

```markdown
---
parent: ./README.md
---

# Persistence and Serialization Strategy: {Feature Name}

## Pattern
[How affected data is validated, stored and restored; identify canonical data versus derived state]
[Reference existing patterns at file:line; explain any proposed departure and migration needs]

## Conversion Rules
[Actual serialization formats, identifiers, timestamps and schema/version rules]

## Data Requiring Persistence

| Model / Record | Storage Location | Fields | Notes |
|--------|---------------------|--------|-------|
| [Model / Record] | [Path or store] | [Required stored fields] | [Ownership and recovery notes] |

## Field Mapping

### [Application Model] → [Stored Representation]

| Application Field | Stored Field | Conversion |
|------------------|-------------------|------------|
| [Field] | [Stored representation] | [Validation, encoding and restoration] |
```

#### 07-standards.md — Standards Compliance (if an explicit comparison is needed)

```markdown
---
parent: ./README.md
---

# Standards Compliance: {Feature Name}

| Standard File | Status | Key Compliance Points |
|---------------|--------|-----------------------|
| [Applicable repository instruction or design document] | ✅/⚠️ | [Relevant requirement and evidence] |
| [Applicable language/framework guidance] | ✅/⚠️ | [Relevant requirement and evidence] |

## Clarifications
[Document any discrepancies between guides and codebase patterns, and which one is followed]
```

#### 08-api-contract.md — HTTP API Contract (features with REST endpoints)

````markdown
---
parent: ./README.md
---

# API Contract: {Feature Name}

## Endpoints Summary

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | /api/v1/resource | List resources | Bearer |
| POST | /api/v1/resource | Create resource | Bearer |
| GET | /api/v1/resource/:id | Get resource | Bearer |

---

## `GET /api/v1/resource`

**Description:** [What this endpoint does]

**Request:**
```
Query params:
  page: int (default 1)
  limit: int (default 20, max 100)
  status: string? (optional, filter by status)
Headers:
  Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "title": "string",
      "status": "active|archived",
      "createdAt": "2024-01-01T00:00:00Z",
      "author": {
        "id": "uuid-string",
        "name": "string"
      }
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

**Error responses:**
| Status | Error Code | Body | When |
|--------|------------|------|------|
| 400 | [Project code, if used] | `{"error": {"code": "ERROR_A", "message": "..."}}` | Invalid query params |
| 401 | — | `{"error": "unauthorized"}` | Missing/expired token |
| 500 | — | `{"error": "internal"}` | Server error |

---

## `POST /api/v1/resource`

**Request:**
```json
{
  "title": "string (required, 1-200 chars)",
  "description": "string (optional)",
  "type": "typeA|typeB (required)"
}
```

**Response (201):**
```json
{
  "id": "uuid-string",
  "title": "string",
  "status": "draft",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

**Error responses:**
| Status | Error Code | Body | When |
|--------|------------|------|------|
| 400 | [Project code, if used] | `{"error": {"code": "ERROR_A", "message": "..."}}` | Validation failed |
| 409 | [Project code, if used] | `{"error": {"code": "ERROR_B", "message": "..."}}` | Duplicate |

[Repeat for each endpoint with exact JSON shapes]
````

---

## Phase 3: Architect Review

Review the design using the checklist below. Use an available architecture-review agent when delegation is permitted and useful; otherwise perform an explicit review pass. In compact mode, summarize applicable findings without reproducing every table. References below refer to views, whether held in separate files or existing document sections.

```
You are a Senior Software Architect reviewing a feature design.

Review the design documents at {service-path}/docs/{feature-name}/:
- 01-architecture.md — structural correctness, layer separation, dependency direction
- 02-behavior.md — completeness of scenarios, missing edge cases, error coverage
- 03-decisions.md — rationale quality, risk coverage, alternatives considered
- 04-testing.md — test coverage, coverage mapping completeness
- Conditional files (05-08) if they exist

Review against:
1. Applicable repository instructions and architecture guidance discovered in Phase 0.3
2. Responsibility boundaries — dependency direction, ownership and the smallest adequate design
3. Data/state rules — validation, invariants and required observable behavior
4. Fit with existing codebase patterns, or evidence and tradeoffs supporting a different approach
5. Scalability and performance implications
6. Missing scenarios or edge cases, including replay, restart, cancellation and external-effect recovery where affected

Cross-document consistency checks:
- Affected invariants and error behavior in the design have meaningful verification in the quality view
- Affected use cases have sufficient behavior descriptions; sequence diagrams cover interactions that need clarification
- Changed persistent data has a storage/serialization entry, with all required stored fields preserved
- Changed endpoints have exact request/response shapes in the API contract (if applicable)
- New error identifiers follow project conventions and do not conflict with existing definitions
- Changed state transitions have behavior and verification coverage, including recovery where consequential

Produce a structured review:

## Architecture Review: {Feature Name}

### Compliance
| Standard | Status | Notes |
|----------|--------|-------|
| Responsibility Boundaries | ✅/⚠️/❌ | |
| Data / State Invariants | ✅/⚠️/❌ | |
| Layer Separation | ✅/⚠️/❌ | |
| Pattern Fit | ✅/⚠️/❌ | [Existing pattern at file:line or justified alternative] |

### Cross-Document Consistency
| Check | Status | Details |
|-------|--------|---------|
| Invariants ↔ Verification | ✅/❌ | [Affected rules covered] |
| Use Cases ↔ Behavior | ✅/❌ | [Affected interactions explained] |
| Errors ↔ Verification | ✅/❌ | [Affected error behavior covered] |
| Persistent Data ↔ Storage | ✅/❌/N/A | [Required stored fields preserved] |
| Endpoints ↔ API Contract | ✅/❌/N/A | [Exact JSON shapes present] |
| Error Identifiers ↔ Existing | ✅/❌/N/A | [No identifier conflicts] |
| State Transitions ↔ Behavior + Verification | ✅/❌/N/A | [Changed transitions and recovery covered] |

### Findings
#### 🔴 Critical (must fix before approval)
- [File: description]

#### 🟠 Important (should fix)
- [File: description]

#### 🟡 Suggestions (nice to have)
- [File: description]

### Missing Scenarios
- [Affected scenarios not covered in the behavior view]

### Verdict: ✅ READY FOR REVIEW / ⚠️ NEEDS ITERATION
```

### If Issues Found
- Fix findings in the **specific file or section** where the issue lives
- Re-run architect review if significant changes
- Iterate until ✅ READY FOR REVIEW

---

## Phase 4: Human Approval (Design)

Present the design to the user:

```markdown
## Design Ready for Review: {Feature Name}

### Summary
[1-2 sentences: what this feature does]

### Architecture Highlights
- [Key design decision 1]
- [Key design decision 2]
- [Key design decision 3]

### Architect Review
[Summary of review findings — any remaining concerns]

### Documents
| File | Lines | Description |
|------|-------|-------------|
| `README.md` | ~N | Business context, acceptance criteria |
| `01-architecture.md` | ~N | C4 L1→L2→L3, module dependencies |
| `02-behavior.md` | ~N | DFD, sequence diagrams per use case |
| `03-decisions.md` | ~N | N design decisions, risks |
| `04-testing.md` | ~N | ~N test cases with coverage mapping |
| `05-events.md` | ~N | Domain events |
| ... | | [conditional files] |

All at: `{service-path}/docs/{feature-name}/`

**Please review the design documents and:**
1. ✅ Approve — proceed to code planning
2. 🔄 Request changes — specify what to adjust
3. ❓ Questions — ask about specific decisions
```

**WAIT for user approval.** Do NOT proceed to code plan without explicit approval.

If the user requests changes:
1. Update the **specific file** with feedback (not all files)
2. Re-run architect review if changes are significant
3. Present again for approval

---

## Phase 5: Code Plan (4th C — Code Level)

After design approval, create the detailed implementation plan as **separate files per phase** inside a `plan/` directory for larger changes. For compact work, use one bounded implementation section in the scoped note. Follow the repository's plan location and reference existing design documents rather than duplicating them.

### Phase Order Strategy

Choose phase ordering based on the change. The following are examples, not a required layer structure; use actual project boundaries and prefer the smallest restart-safe vertical slice where applicable:

**Option A: Bottom-up (when dependencies call for it)**
Domain → Use Case → Adapter → Controller → DI

**Option B: Adapter-first (for features extending existing entities with new persistence)**
Adapter (repo) → Domain → Use Case → Controller → DI
Advantage: repo model validates data model assumptions early

**Option C: Vertical slice (for features with independent endpoints)**
All layers for Endpoint 1 → All layers for Endpoint 2 → DI
Advantage: shippable increment per phase

Document the chosen strategy and rationale in plan/README.md.

### Output Directory
```
{service-path}/docs/{feature-name}/plan/
├── README.md       — Overview, file map, DI, error codes, success criteria
├── phase-01.md     — First implementation phase
├── phase-02.md     — Second implementation phase
└── phase-NN.md     — One file per phase
```

### Why separate files?
- Each phase is **self-contained** — implementer reads ONE file per assignment
- Phases can be reviewed/approved **independently**
- Lead can hand a single file to the implementer agent without noise
- Progress tracking: update the repository-designated roadmap/checklist; phase files stay as reference

---

### plan/README.md — Overview & Index

```markdown
---
date: YYYY-MM-DD
feature: {feature-name}
service: {service-path}
design: ../README.md
status: draft | approved
---

# Code Plan: {Feature Name}

## Overview
[Summary: what will be implemented, referencing design docs for architecture]

## Phase Strategy
[Bottom-up / Adapter-first / Vertical slice — and WHY]

## Phases

| # | Phase | Layer | Dependencies | Status |
|---|-------|-------|--------------|--------|
| 1 | [Name] | Domain | — | ⬜ |
| 2 | [Name] | Use Case | Phase 1 | ⬜ |
| N | [Name] | [Layer] | Phase X | ⬜ |

## File Map

### New Files
- `path/to/new/module.py` — [purpose]

### Modified Files
- `path/to/existing.py:line-range` — [what changes]

## DI Integration

**Init chain position:** [Where in the ACTUAL init chain discovered in Phase 0.3]
**Wiring changes:** [Affected composition or dependency wiring — reference file:line; omit if unchanged]
**Initialization order:** [Step by step, with dependency references]

## Error Codes

Include only if the change needs new error identifiers; follow the actual project convention rather than introducing a new code scheme.

**Identifiers:** [Proposed identifiers, if needed]
**Conflict check:** [Verified no conflicts with existing definitions]

| Code | Description | HTTP Status |
|------|-------------|-------------|
| [Identifier] | [Description] | [Status, if HTTP] |

## Success Criteria
- [ ] All phases completed and verified
- [ ] Relevant verification passing (reference the quality view and repository-designated evidence)
- [ ] Affected error behavior verified
- [ ] Applicable build/type checks pass using repository commands
- [ ] Applicable lint checks pass
- [ ] API contract matches implementation (see ../08-api-contract.md if exists)
- [ ] All acceptance criteria from ../README.md met
```

---

### plan/phase-NN.md — Individual Phase File

Each phase gets its own file in multi-file mode. The phase must be **self-contained** — a developer (or implementer agent) should understand the task from this phase and its explicit source/design references, without reading other phase files.

```markdown
---
phase: N
name: [Phase Name]
layer: [Actual affected responsibility or vertical slice]
depends_on: [phase-01, phase-02] or none
plan: ./README.md
---

# Phase {N}: {Phase Name}

## Goal
[What this phase achieves — 1-2 sentences]

## Context
[Brief context: what was done in previous phases that this phase builds on.
Reference specific files/types created earlier that this phase uses.]

## Files to Create

### `path/to/module.py`
**Purpose:** [What this file does]

**Implementation details:**
- [Specific business rules]
- [Invariants to enforce]
- [Input/schema constraints]
- [Interfaces to implement]
- [Reference design docs: 01-architecture.md for structure, 02-behavior.md for logic, 08-api-contract.md for JSON shapes]

### `path/to/another.py`
[Repeat per file]

## Files to Modify

### `path/to/existing.py`
**What changes:** [Description of modifications]
**Lines affected:** [Approximate line range — reference actual file:line]

## Key Decisions
- [Decision relevant to THIS phase — reference 03-decisions.md if needed]

## Verification
- [ ] [Applicable repository build/type/lint commands pass]
- [ ] [Focused verification commands pass; use the configured environment and test runner]
- [ ] [Affected validation, ownership and caller expectations verified]
- [ ] [Replay/restart/side-effect checks pass, if affected]
- [ ] [Changed API behavior matches the contract, if applicable]
```

---

### Phase File Rules

1. **Self-contained** — reader needs no other phase file to understand what to do
2. **Context section** — briefly summarize what previous phases produced (types, interfaces)
3. **Per-file details** — list every file with its purpose and key implementation notes
4. **No forward references** — don't mention things from future phases
5. **Verification is phase-scoped** — only check what THIS phase touches
6. **Reference design docs** — link to architecture, behavior, API contract docs for implementation details

---

## Phase 6: Human Approval (Code Plan)

Present the code plan to the user:

```markdown
## Code Plan Ready: {Feature Name}

### Phase Strategy
[Bottom-up / Adapter-first / Vertical slice]

### Phases
1. [Phase 1 summary]
2. [Phase 2 summary]
...

### Scope
- New files: N
- Modified files: M
- Error identifiers: [New identifiers, if any; verified no conflicts]

### Artifacts
- Design: `{service-path}/docs/{feature-name}/` ✅ Approved
- Code Plan: `{service-path}/docs/{feature-name}/plan/` ({N} phase files)

**Next step:** After approval, run:
[The implementation workflow available in this repository, with the approved plan path]

**Please review the code plan and:**
1. ✅ Approve — ready for implementation
2. 🔄 Request changes — specify adjustments
3. ❓ Questions — ask about specific phases
```

**WAIT for user approval.**

---

## Rules

1. **Design before code** — never jump to implementation details in Phase 2
2. **Separate views, proportional output** — distinguish structure, behavior, decisions and verification; use sections for compact tasks and separate files for larger changes
3. **Mermaid for all diagrams** — renderable, versionable, diffable
4. **file:line references** — every reference to existing code includes exact location
5. **Facts in research, decisions in design** — research is objective, design is opinionated
6. **Two approval gates** — design approval AND code plan approval before implementation
7. **Discover standards AND real structure first** — follow repository guidance and inspect affected entry points, state, persistence and callers before designing; justify departures from current patterns
8. **Stop at uncertainty** — ask the user, don't guess architectural decisions
9. **C4 zoom-in narrative** — keep relevant L1→L2→L3 views together; omit levels that add no information
10. **Conditional files** — only create 05-08 when the feature requires them (see Phase 0.5)
11. **One sequence per use case where useful** — group happy path, error cases and edge cases under the same behavior section
12. **Exact API contract** — changed endpoints need exact request/response shapes with field names and types; follow existing contract ownership
13. **Cross-document consistency** — review affected behavior, ownership, persistence, API and verification together, regardless of document layout
14. **Error identifier conflict check** — when adding identifiers, follow project conventions and verify no conflicts with existing definitions
15. **Use evidence, not dogma** — reuse suitable project patterns; propose simpler alternatives when justified by the task, evidence and migration/recovery implications

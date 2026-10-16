---
name: design-feature
description: Design a feature using C4 model (3C + DFD + Sequence), architect review, human approval, then code plan (4th C). Outputs multi-file docs to {service}/docs/{featu
argument-hint: [feature-name] [service-path] [description or ticket link]
---

# Design Feature — C4 + DFD + Sequence → Code Plan

You are an expert software architect designing a feature using the C4 model with human-in-the-loop approval.

**Core principle:** Design WHAT and WHY before HOW. No code planning until architecture is approved.

---

## Phase 0: Understand the Mission

### 0.1 Parse Arguments

- `$ARGUMENTS[0]` — feature name (slug, used for directory name)
- `$ARGUMENTS[1]` — service path (e.g. `microservices/name` or `front`)
- `$ARGUMENTS[2+]` — feature description, requirements, or ticket link (everything after service path)

If arguments are missing, ask:
```
Please provide:
1. Feature name (slug, e.g. "rag-strategy")
2. Service path (e.g. "microservices/name" or "front")
3. Feature description or ticket link
```

If only feature name and service path are provided (no description), ask the user to describe the feature before proceeding.

### 0.2 Read the Feature Request

- Read the feature description/ticket provided by the user
- Understand the **business goal** — what problem does this solve?
- Identify acceptance criteria
- Determine if this touches Backend, Frontend, or infrastructure

### 0.3 Read Project Standards & Discover Codebase Structure




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
| Backend feature with entities | `06-repo-model.md` |
| Backend feature | `07-standards.md` |
| Feature exposes REST endpoints | `08-api-contract.md` |

---

## Phase 1: Research (Optional)

If research is needed, spawn **2-3 parallel tasks** using the `codebase-researcher` subagent (Task tool with `subagent_type: "codebase-researcher"`):

### Research Task 1: Architecture Analysis
```
Analyze the architecture of {service-path}:

Start from these entry points:
1. {service-path}/initService/container.go — DI container, all registered dependencies
2. {service-path}/initService/ — scan all init files, map initialization chain order
3. Find router setup (search for RegisterFiberRoute, fiber.Router) — map existing endpoints
4. {service-path}/domain/entity/ — list all entities, their VOs, builders, state machines
5. {service-path}/domain/usecase/ — list all use cases, their dependencies
6. {service-path}/adapter/ — controllers, repos, gateways

For each relevant component, report:
- Layer and package structure
- Builder pattern usage (3-stage order)
- Value object patterns
- Repository mapping patterns (NewFromEntity/ToEntity/Restore)
- Event patterns (if any)

Report file:line references for all findings.
Save findings — facts only, no critique, no suggestions.
```

### Research Task 2: Pattern Discovery
```
Find patterns relevant to "{feature-name}" in {service-path}:

1. Similar features already implemented — find the closest analog and document its full structure
2. Reusable components in domain-common/ — shared primitives, VOs, utilities
3. API patterns — endpoint registration, request/response formats, error response structure
4. Testing patterns — test suite setup, mock patterns, stub patterns
5. Error code ranges — scan ALL error codes to map used ranges and find next available

Report file:line references for all findings.
Save findings — facts only, no critique.
```

### Research Task 3: Integration Analysis
```
Analyze integration points for "{feature-name}":

1. External services and gateways — gRPC clients, HTTP clients, LLM pipelines
2. Event-driven communication — event bus, domain events, handlers
3. Shared types and contracts (boundary layer) — interfaces exposed to other modules
4. Database collections affected — existing MongoDB collections, indexes
5. Auth/middleware — how auth is applied to routes

Report file:line references for all findings.
Save findings — facts only.
```

### Save Research
After all subagents complete, create the docs directory and synthesize findings:
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
- **Init chain order:** [Config → Repos → Gateways → ... actual order from initService/]
- **Router pattern:** [How routes registered, middleware — reference file:line]
- **Entity pattern:** [VO usage, builder pattern — reference closest analog file:line]
- **Repo pattern:** [NewFromEntity/ToEntity/Restore — reference file:line]
- **Error code ranges in use:** [PRS-001..099 validation, 100..199 state, etc.]
- **Next available error range:** [e.g. PRS-600..699]

## Architecture Overview
[Current architecture of affected modules]

## Existing Patterns
[Patterns found that should be reused — with file:line references]

## Integration Points
[External dependencies, gateways, events]

## Key Files
- `path/to/file.go:line` — description
```

---

## Phase 2: Design (Multi-File, View-Based)

Create the architectural design as **separate documents by view** (inspired by Kruchten's 4+1 model):
- **Logical View** = C4 (structure)
- **Process View** = DFD + Sequences (behavior)
- **Decision View** = ADRs + Risks (rationale)
- **Quality View** = Testing (verification)

### 2.1 Output Structure

```
{service-path}/docs/{feature-name}/
├── README.md              — Index + Business Context + Acceptance Criteria
├── 01-architecture.md     — C4 L1 + L2 + L3 + Module Dependencies (Logical View)
├── 02-behavior.md         — DFD + Sequence Diagrams (Process View)
├── 03-decisions.md        — Design Decisions + Risks + Open Questions (Decision View)
├── 04-testing.md          — Testing Strategy + Test Cases (Quality View)
├── 05-events.md           — Domain Events (conditional)
├── 06-repo-model.md       — Repository Model Strategy (conditional, Backend only)
├── 07-standards.md        — Standards Compliance Matrix (conditional, Backend only)
├── 08-api-contract.md     — HTTP API Contract (conditional, features with REST endpoints)
├── research.md            — Research (from Phase 1, if applicable)
└── plan/                  — Code Plan (added after design approval, Phase 5)
    ├── README.md          — Overview, file map, DI integration, error codes, success criteria
    ├── phase-01.md        — Phase 1 implementation details
    ├── phase-02.md        — Phase 2 implementation details
    └── phase-NN.md        — One file per implementation phase
```

**Core files (always):** README.md, 01-architecture.md, 02-behavior.md, 03-decisions.md, 04-testing.md
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
| [06-repo-model.md](...) | — | Repository model strategy (Backend) |
| [07-standards.md](...) | — | Standards compliance matrix (Backend) |
| [08-api-contract.md](...) | — | HTTP API contract (if REST endpoints) |

[Remove rows for files that don't apply to this feature]
```

#### 01-architecture.md — Logical View (C4 L1 → L2 → L3)

All three C4 levels in one file — they form a single "zoom-in" narrative.

```markdown
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
        Container(api, "API Service", "Go/Fiber", "Handles HTTP requests")
        ContainerDb(db, "MongoDB", "Database", "Stores data")
        Container(worker, "Worker", "Go", "Background processing")
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
        subgraph "domain/entity"
            Entity["Entity"]
            VO["Value Objects"]
        end
        subgraph "domain/usecase"
            UC["UseCase"]
        end
        subgraph "boundary"
            Repo["«interface» Repository"]
        end
    end
```

**Description:** [entities, VOs, state machines, key interfaces]

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
```

#### 02-behavior.md — Process View (DFD + Sequences)

One sequence diagram per use case (not per scenario). Group related error/edge cases under the same use case section.

```markdown
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

One diagram per use case. Show happy path, then list error/edge cases below.

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
| Entity not found | PRS-XXX | 404 | Return error |
| Invalid state | PRS-XXX | 409 | Return error with current state |
| Validation failed | PRS-XXX | 400 | Return field-level errors |

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
```

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

```markdown
---
parent: ./README.md
view: quality
---

# Testing Strategy: {Feature Name}

## Test Rules
[Reference project test standards — suite pattern, AAA, naming, etc.]
[Match ACTUAL test patterns from the project discovered in Phase 0.3]

## Test Structure
```
[Directory tree of test files — match project test directory structure]
```

---

## Coverage Mapping

Every business rule, error code, and state transition must be traced to a test.

### Entity Coverage
| Entity | Business Rule / Invariant | Test |
|--------|---------------------------|------|
| [Entity] | [All fields are VOs] | `TestEntity_Build_AllFieldsSet` |
| [Entity] | [State transition X→Y only when Z] | `TestEntity_Transition_XToY_WhenZ` |
| [Entity] | [Cannot create with empty name] | `TestEntityBuilder_EmptyName_Error` |

### Error Code Coverage
| Error Code | Description | Tested by |
|------------|-------------|-----------|
| PRS-XXX | [Description] | `TestUseCase_Condition_ReturnsXXX` |
| PRS-YYY | [Description] | `TestUseCase_Condition_ReturnsYYY` |

---

## [Module 1] — Test Cases

### [Entity/Component] ([N] tests)

| Test | What it verifies |
|------|------------------|
| `TestMethod_Condition_Result` | [Description] |

### Stubs
- `GetXxx()` — [what it returns]

---

## [Module 2] — Test Cases
[Repeat per module]

---

## Repo Model Round-Trip Tests (if applicable)

| Test | What it verifies |
|------|------------------|
| `TestXxxModel_RoundTrip_AllFieldsPreserved` | Entity → Model → Entity |

---

## Test Count Summary

| Module | Entity | Builder | UC | Service | VO | Repo Model | Total |
|--------|--------|---------|----|---------|----|------------|-------|
| [Module 1] | N | N | N | N | N | N | **N** |
| **TOTAL** | | | | | | | **N** |
```

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

#### 06-repo-model.md — Repository Model Strategy (Backend only)

```markdown
---
parent: ./README.md
---

# Repository Model Strategy: {Feature Name}

## Pattern
[NewFromEntity() + ToEntity() with Restore(). Base model embedding pattern if shared entities]
[Reference existing repo model pattern at file:line]

## Conversion Rules
[Timestamps as int64 UnixNano, VOs as strings, etc.]

## Entities with Repo Models

| Entity | Repo Model Location | Fields | Notes |
|--------|---------------------|--------|-------|
| [Entity] | [Path] | [N fields] | [Nested objects, embedded docs] |

## Field Mapping

### [Entity] → [RepoModel]

| Entity Field (VO) | Model Field (raw) | Conversion |
|------------------|-------------------|------------|
| Name() | Name string | .Value() / primitives.NewName() |
| Status() | Status string | .String() / StatusFromString() |
| CreatedAt() | CreatedAt int64 | .UnixNano() / time.FromUnixNano() |
```

#### 07-standards.md — Standards Compliance (Backend only)

```markdown
---
parent: ./README.md
---

# Standards Compliance: {Feature Name}

| Standard File | Status | Key Compliance Points |
|---------------|--------|-----------------------|
| Architecture Layers.txt | ✅/⚠️ | [Points] |
| Builder.txt | ✅/⚠️ | [Points] |
| Clean architecture.txt | ✅/⚠️ | [Points] |
| Domain Model.txt | ✅/⚠️ | [Points] |
| Domain model test.txt | ✅/⚠️ | [Points] |
| Go style.txt | ✅/⚠️ | [Points] |
| RepoModel.txt | ✅/⚠️ | [Points] |
| Tests Style.txt | ✅/⚠️ | [Points] |

## Clarifications
[Document any discrepancies between guides and codebase patterns, and which one is followed]
```

#### 08-api-contract.md — HTTP API Contract (features with REST endpoints)

```markdown
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
| 400 | PRS-XXX | `{"error": {"code": "PRS-XXX", "message": "..."}}` | Invalid query params |
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







  "status": "draft",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

**Error responses:**
| Status | Error Code | Body | When |
|--------|------------|------|------|
| 400 | PRS-XXX | `{"error": {"code": "PRS-XXX", "message": "..."}}` | Validation failed |
| 409 | PRS-YYY | `{"error": {"code": "PRS-YYY", "message": "..."}}` | Duplicate |

[Repeat for each endpoint with exact JSON shapes]
```

---

## Phase 3: Architect Review

Spawn an **architect-reviewer** agent (Task tool with `subagent_type: "architect-reviewer"`) to review the design:

```
You are a Senior Software Architect reviewing a feature design.

Review the design documents at {service-path}/docs/{feature-name}/:
- 01-architecture.md — structural correctness, layer separation, dependency direction
- 02-behavior.md — completeness of scenarios, missing edge cases, error coverage
- 03-decisions.md — rationale quality, risk coverage, alternatives considered
- 04-testing.md — test coverage, coverage mapping completeness
- Conditional files (05-08) if they exist

Review against:
1. Project architecture standards in /promts/be/ (or /promts/fe/)
2. Clean Architecture principles — dependency direction, layer separation
3. Domain Model rules — entity encapsulation, value objects, invariants
4. Consistency with existing codebase patterns (from research.md)
5. Scalability and performance implications
6. Missing scenarios or edge cases

Cross-document consistency checks:
- Every entity in 01-architecture has test cases in 04-testing
- Every use case in 01-architecture has a sequence diagram in 02-behavior
- Every error code in 02-behavior has a test in 04-testing (coverage mapping)
- Every entity in 01-architecture has a repo model entry in 06-repo-model (if exists)
- Every field in repo model 06 covers ALL fields of the entity in 01-architecture
- Every endpoint in 02-behavior has exact JSON shapes in 08-api-contract (if exists)
- Error codes don't conflict with existing ranges (from research.md)
- Every state transition in 01-architecture has both a sequence in 02-behavior and a test in 04-testing

Produce a structured review:

## Architecture Review: {Feature Name}

### Compliance
| Standard | Status | Notes |
|----------|--------|-------|
| Clean Architecture | ✅/⚠️/❌ | |
| Domain Model | ✅/⚠️/❌ | |
| Layer Separation | ✅/⚠️/❌ | |
| Pattern Consistency | ✅/⚠️/❌ | [Matches existing patterns at file:line] |

### Cross-Document Consistency
| Check | Status | Details |
|-------|--------|---------|
| Entities ↔ Tests | ✅/❌ | [Every entity business rule has a test] |
| Use Cases ↔ Sequences | ✅/❌ | [Every UC has a sequence diagram] |
| Error Codes ↔ Tests | ✅/❌ | [Every error code tested] |
| Entities ↔ Repo Models | ✅/❌/N/A | [All fields mapped] |
| Endpoints ↔ API Contract | ✅/❌/N/A | [Exact JSON shapes present] |
| Error Code Ranges ↔ Existing | ✅/❌ | [No conflicts with used ranges] |
| State Transitions ↔ Sequences + Tests | ✅/❌ | [All transitions covered] |

### Findings
#### 🔴 Critical (must fix before approval)
- [File: description]

#### 🟠 Important (should fix)
- [File: description]

#### 🟡 Suggestions (nice to have)
- [File: description]

### Missing Scenarios
- [Scenarios not covered in 02-behavior.md]

### Verdict: ✅ READY FOR REVIEW / ⚠️ NEEDS ITERATION
```

### If Issues Found
- Fix findings in the **specific file** where the issue lives
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

After design approval, create the detailed implementation plan as **separate files per phase** inside a `plan/` directory.

### Phase Order Strategy

Choose phase ordering based on the feature type:

**Option A: Bottom-up (default for most features)**
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
- Progress tracking: checkmark in README.md, phase file stays as reference

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
- `path/to/new/file.go` — [purpose]

### Modified Files
- `path/to/existing.go:line-range` — [what changes]

## DI Integration

**Init chain position:** [Where in the ACTUAL init chain discovered in Phase 0.3]
**Container changes:** [What to add to container.go — reference file:line]
**Initialization order:** [Step by step, with dependency references]

## Error Codes

**Range:** {PREFIX}-XXX to {PREFIX}-YYY
**Conflict check:** [Verified no conflicts with existing ranges: list used ranges]

| Code | Description | HTTP Status |
|------|-------------|-------------|
| {PREFIX}-XXX | [Description] | 400 |
| {PREFIX}-YYY | [Description] | 404 |

## Success Criteria
- [ ] All phases completed and verified
- [ ] All tests passing (see ../04-testing.md for full test list)
- [ ] All error codes tested (see ../04-testing.md coverage mapping)
- [ ] Build clean (`go build ./...`)
- [ ] Lint clean
- [ ] API contract matches implementation (see ../08-api-contract.md if exists)
- [ ] All acceptance criteria from ../README.md met
```

---

### plan/phase-NN.md — Individual Phase File

Each phase gets its own file. The file must be **self-contained** — a developer (or implementer agent) should be able to read ONLY this file + the referenced source files and

```markdown
---
phase: N
name: [Phase Name]
layer: domain | usecase | adapter | controller | initService
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

### `path/to/file.go`
**Purpose:** [What this file does]

**Implementation details:**
- [Specific business rules]
- [Invariants to enforce]
- [Value object constraints]
- [Interfaces to implement]
- [Reference design docs: 01-architecture.md for structure, 02-behavior.md for logic, 08-api-contract.md for JSON shapes]

### `path/to/another.go`
[Repeat per file]

## Files to Modify

### `path/to/existing.go`
**What changes:** [Description of modifications]
**Lines affected:** [Approximate line range — reference actual file:line]

## Key Decisions
- [Decision relevant to THIS phase — reference 03-decisions.md if needed]

## Verification
- [ ] `go build ./...` passes
- [ ] `go test ./{relevant-path}/...` passes
- [ ] [Phase-specific checks, e.g. "All fields are Value Objects"]
- [ ] [Phase-specific checks, e.g. "Builder follows 3-stage order"]
- [ ] [Phase-specific checks, e.g. "Error codes match 08-api-contract.md"]
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
- Error codes: {PREFIX}-XXX to {PREFIX}-YYY (verified no conflicts)

### Artifacts
- Design: `{service-path}/docs/{feature-name}/` ✅ Approved
- Code Plan: `{service-path}/docs/{feature-name}/plan/` ({N} phase files)

**Next step:** After approval, run:
- Backend: `/implement_backend {service-path}/docs/{feature-name}/plan/README.md`
- Frontend: `/implement_frontend {service-path}/docs/{feature-name}/plan/README.md`

**Please review the code plan and:**
1. ✅ Approve — ready for implementation
2. 🔄 Request changes — specify adjustments
3. ❓ Questions — ask about specific phases
```

**WAIT for user approval.**

---

## Rules

1. **Design before code** — never jump to implementation details in Phase 2
2. **Multi-file by view** — separate structure (01), behavior (02), decisions (03), testing (04). NEVER put everything in one file
3. **Mermaid for all diagrams** — renderable, versionable, diffable
4. **file:line references** — every reference to existing code includes exact location
5. **Facts in research, decisions in design** — research is objective, design is opinionated
6. **Two approval gates** — design approval AND code plan approval before implementation
7. **Read ALL standards AND discover real structure first** — read every file in promts/be/ AND explore the actual codebase (container.go, init chain, router, entities) befor
8. **Stop at uncertainty** — ask the user, don't guess architectural decisions
9. **C4 zoom-in narrative** — L1→L2→L3 in one file (01-architecture.md), they tell one continuous story
10. **Conditional files** — only create 05-08 when the feature requires them (see Phase 0.5)
11. **One sequence per use case** — group happy path + error cases + edge cases under one use case section in 02-behavior.md
12. **Exact API contract** — every REST endpoint must have exact JSON request/response shapes with field names and types in 08-ap
13. **Cross-document consistency** — architect reviewer verifies that all documents reference each other correctly (entities↔test
14. **Error code conflict check** — verify new error codes don't conflict with existing ranges before assigning
15. **Match real project patterns** — discovered in Phase 0.3. NEVER use generic/textbook patterns that don't match the codebase

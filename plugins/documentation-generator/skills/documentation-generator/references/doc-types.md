# The four document types

Each section gives the outline, what to extract from the codebase, and the
figures worth drawing. Read only the one you are writing.

- [Architecture Overview](#architecture-overview)
- [Database Schema](#database-schema)
- [API Contracts](#api-contracts)
- [Sequence / Flow](#sequence--flow)
- [Choosing between them](#choosing-between-them)

---

## Architecture Overview

The one to write first when you know nothing. It gives every later document
somewhere to point.

### Outline

```
1.  What this system does          purpose, in prose, before any structure
2.  The shape of it                layers or services, one figure
3.  The main components            table: component · responsibility · source
4.  How a request flows            one sequence figure, the commonest path
5.  Data at rest                   what is stored and roughly why
6.  External dependencies          what breaks if each one is down
7.  Cross-cutting concerns         auth, logging, errors, background work
8.  What is notable                the surprising, clever or risky parts
9.  Open questions                 what the code does not settle
10. Sources                        files read, and the commit
```

### What to extract

| Looking for | Where it usually is |
|---|---|
| Entry point | `main.py`, `app.ts`, `Application.java`, `cmd/` |
| Layering | the directory names — `api/`, `services/`, `models/` |
| Dependency wiring | DI containers, `deps.py`, `providers`, constructors |
| Config and flags | `config.py`, `settings`, `.env.example` |
| Background work | `workers/`, `tasks/`, `jobs/`, queue clients |
| External calls | HTTP clients, SDK imports, connection strings |
| Cross-cutting | middleware, decorators, interceptors, filters |

### Figures

- **Layered stack** — the request path, each layer naming its directory
- **Component map** — boxes and dependency arrows, only for the top ~10
- **One sequence** — the most representative request, end to end

### Traps

Do not restate the directory tree in prose. A reader can run `ls`. Explain the
**reason** a boundary exists and what would break if it moved.

---

## Database Schema

### Outline

```
1.  Conventions                    ids, timestamps, enums, JSON, naming
2.  Schema at a glance             table · verdict · purpose, and an ER figure
3.  Core tables                    column-level, grouped by domain
4.  Supporting tables              lookups, config, audit
5.  Relationships and cascades     what deletes what, and what deliberately does not
6.  Constraints worth knowing      the ones encoding a business rule
7.  Indexes                        each with the query it serves
8.  Migrations                     order, and anything that needs care
9.  Retention                      what is deleted when, and what outlives the row
10. Open questions
11. Sources
```

### What to extract

| Looking for | Where |
|---|---|
| Tables | ORM model classes, `__tablename__`, `@Entity`, `model X {}` |
| Columns and types | model field declarations |
| Nullability | the single most useful fact per column — always record it |
| Constraints | `CHECK`, `UNIQUE`, partial and composite indexes |
| Cascades | `ondelete=`, `on_delete=`, `@OnDelete`, FK definitions |
| Enums | Python `StrEnum`, TS unions, DB enum types, CHECK lists |
| Migration order | migration filenames and `down_revision` chains |

### Column table shape

`Column · Type · Null · Notes` at widths `[1.5, 1.45, 0.5, 3.1]`.

The Notes column is where the value is. Not "the user id" — say *why it is
nullable*, *what happens on delete*, *what business rule it encodes*.

### Figures

- **ER diagram**, colour-coded by role. Use the `entity()` pattern: a box with
  a coloured header bar and one line per column, `PK` / `FK` tags right-aligned.
- **Constraint explainer** for anything subtle — a partial unique index, an
  exclusion constraint, a composite foreign key
- **Migration order** when there is a dependency that would otherwise be missed

### Traps

A schema document that lists columns and stops is a `\d+` dump with a cover
page. The value is in the *why*: why nullable, why cascade, why this index.

Where a constraint encodes a business rule, say which rule.

---

## API Contracts

### Outline

```
1.  Conventions                    base path, auth, errors, pagination, versioning
2.  The endpoint surface           one figure, grouped by caller
3.  Endpoints by area              request, response, errors, per endpoint
4.  Authentication and scope       who may call what, and how it is enforced
5.  Errors                         the envelope, and the full code table
6.  Rate limits                    endpoint · limit · key · why
7.  Breaking-change analysis       what existing clients would notice
8.  Open questions
9.  Sources
```

### What to extract

| Looking for | Where |
|---|---|
| Routes | decorators, router registrations, an OpenAPI spec if one exists |
| Request shapes | request DTOs, Pydantic models, zod schemas, `@Body` types |
| Response shapes | return types, response models, serialisers |
| Status codes | raised exceptions, `HTTPException`, error handlers |
| Auth | dependency injections, guards, middleware, decorators |
| Rate limits | limiter decorators, middleware, Redis key patterns |

**If an OpenAPI spec exists, read it first** — then check it against the code,
because generated specs drift. Note any disagreement; that is a finding.

### Endpoint contract shape

```
POST /api/v1/resource
{ "field": "value" }

→ 201  { "id": "…", "status": "…" }
→ 409  RESOURCE_CONFLICT
→ 422  VALIDATION_ERROR   { "missing": ["field"] }
```

Show request and response together, error cases inline. A contract listing only
the happy path is half a contract, and the half that matters least.

### Figures

- **Endpoint map**, grouped by caller, colour-coded by state
- **A call sequence** for any multi-step flow
- **Error table** as a figure when it is long enough to be daunting

### Traps

Do not paste the whole OpenAPI document. Extract the shape and say what it means.
Group by *who calls it*, not alphabetically — the reader is a person with a job.

---

## Sequence / Flow

Rarely a document on its own; usually a section. Write it standalone when one
flow is complicated enough to deserve it — checkout, onboarding, a transaction
with rollback semantics.

### Outline

```
1.  What triggers this flow
2.  The participants               and what each is responsible for
3.  The happy path                 one sequence figure, then prose
4.  Where it can fail              each failure, and what the user sees
5.  Transaction and ordering       what is atomic, what is after commit, why
6.  What happens next              side effects, events, notifications
7.  Open questions
8.  Sources
```

### What to extract

Follow the call chain from the entry point. For each step record: what is
written, what is called, what is awaited, and what happens if it throws.

Pay particular attention to **transaction boundaries**. What is inside, what is
outside, and whether that is deliberate. This is the single most valuable thing
a flow document surfaces, and it is almost never written down anywhere else.

### Figures

- **Sequence diagram** — `Sequence()` in `diagram.py`. Use `.sep()` to mark
  transaction boundaries; they are the whole point.
- **State machine** if the flow moves an entity through statuses

### Traps

Do not narrate the code line by line. A reader wants the shape, the ordering
guarantees and the failure modes — not a transcription.

---

## Choosing between them

`analyze_repo.py` suggests a set based on what it detects. Use judgement on top:

| Situation | Write |
|---|---|
| New joiner needs orientation | Architecture Overview |
| Someone is about to change the schema | Database Schema |
| Another team is integrating | API Contracts |
| A specific flow keeps causing bugs | Sequence / Flow |
| Full documentation set requested | Architecture first, then the others |

Architecture first, always, when writing more than one. The others reference it,
and writing it first is how you find out what you do not yet understand.

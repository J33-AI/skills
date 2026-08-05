# A worked example

What the skill is aiming at, walked through on the `backend-only` fixture
repository in `evals/fixtures/` — a FastAPI + SQLAlchemy + Alembic service for
tracking small business loan applications. Generate it with
`python evals/make_fixtures.py` and follow along.

---

## What the analyser gave back

```
LANGUAGES              12 Python
FRAMEWORKS DETECTED    FastAPI, Pydantic, SQLAlchemy
STACK MARKERS          Alembic, requirements.txt

SUGGESTED DOCUMENTS
  Database Schema      3 tables/models, 2 migration files
  API Contracts        8 route declarations
  Architecture         services, models and layering are identifiable
  Sequence / flow      endpoints call into services — flows are traceable
```

Thirty seconds of work, and enough to have a sensible conversation about what to
write. But **nothing in that output is a finding** — it is a map.

---

## What reading the code gave back

The findings below are the reason the documents were worth writing. None of them
is visible from a file listing.

**A constraint whose name disagrees with itself.** `Borrower` declares
`ck_borrowers_within_facility` (`app/models/borrower.py:27`) but migration
`0002_add_facility_check.py` creates it as `ck_borrower_facility`. The rule is
enforced; the name is not what the model says it is, so a later migration that
drops the constraint by the model's name will silently do nothing.

**Two deletion policies, deliberately different.** `loans.borrower_id` is
`ondelete="RESTRICT"` — a borrower with loans cannot be deleted, which keeps the
credit history. `repayments.loan_id` is `ondelete="CASCADE"` and the ORM
relationship adds `delete-orphan`. Deleting a loan takes its schedule with it.
The asymmetry is intentional and worth stating, because it looks like an
oversight until someone explains it.

**A ledger write outside the transaction.** `LoanService.disburse()`
(`app/services/loan_service.py:34`) writes the loan row and builds the repayment
schedule inside the transaction, then posts to the ledger outside it. A ledger
failure leaves a disbursed loan with no ledger entry — money moved in the
domain model and not in the books. This is the finding that justified the
sequence diagram.

**A state machine that exists twice.** `VALID_TRANSITIONS` in the service and
`ck_loans_status` on the table both encode the lifecycle, and only the service
knows which transitions are legal. The database will accept any of the seven
values in any order if anything writes to it outside `LoanService`.

**Approval attribution enforced in the schema.** `ck_loans_approval_attributed`
makes `approved_by` non-null whenever status is `approved`. That is a business
rule living in the database rather than the code, which is the sort of thing a
schema document exists to surface.

---

## How those findings show up in the document

Not as a list of complaints. Each one lands where a reader needs it, in the
voice the style guide describes:

> **⚠ WATCH OUT**
>
> `LoanService.disburse()` at `app/services/loan_service.py:34` posts to the
> ledger after the transaction commits.
>
> **A ledger outage leaves a loan marked disbursed with no ledger entry**, and
> nothing reconciles the two afterwards. The fix is either an outbox row written
> in the same transaction, or a reconciliation job that reads disbursed loans
> with no matching ledger reference.

Three things make that work: the **file and line**, the **consequence stated
plainly**, and a **recommendation** rather than a complaint.

---

## Structure that came out of it

```
Architecture Overview     the layering, the request path, the notable parts
Database Schema           3 tables, constraints, the two deletion policies
API Contracts             8 routes grouped by caller, not alphabetically
```

The API document grouped endpoints by **who calls them** — back-office operator,
service-to-service, health check — rather than by module or alphabetically. A
reader arrives with a job, not with a filename.

---

## Figures that earned their place

| Figure | Why prose could not do it |
|---|---|
| Layered request path | The shape of four layers is spatial |
| Disbursement sequence | Shows what is inside the transaction and what is deliberately outside it |
| Loan state machine | Seven states and their legal transitions — a table loses the edges |
| ER diagram, colour-coded | Which cascade is RESTRICT and which is CASCADE, at a glance |
| Two-panel comparison | A decision that could plausibly have gone the other way |

Figures that were **not** drawn: a directory tree (a reader can run `ls`), a
"technology stack" logo grid (decorative), a diagram of a three-step process
already clear in one sentence.

---

## The delivery message

> Architecture Overview — 11 pages, 4 figures. Schema — 9 pages, 3 figures.
> `docs/generated/`.
>
> Three things worth your attention. `disburse()` posts to the ledger outside
> the transaction, so a ledger failure leaves a disbursed loan unrecorded —
> §5.2 proposes an outbox row. Migration `0002` creates the facility constraint
> under a different name than the model declares, so a later drop-by-name will
> no-op. And the loan lifecycle is enforced only in `LoanService`; anything
> writing rows directly bypasses it.
>
> Open question I could not settle from the code: whether the ledger is expected
> to be idempotent on retry. Nothing in the repository says either way, and the
> retry design depends on it. §9 records it as a decision.

Short. Names the findings. Says what could not be resolved. The reader knows
within fifteen seconds whether they need to open the document.

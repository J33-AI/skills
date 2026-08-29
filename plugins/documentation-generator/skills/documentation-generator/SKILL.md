---
name: documentation-generator
description: Use when generating technical documentation from a codebase — architecture overviews, database schema references, API contracts and sequence/flow documents — as Word files with drawn diagrams plus a Markdown mirror. Use whenever the user asks to document a project, service, module or API; asks for a schema reference, architecture overview, API contract, technical spec, onboarding doc or sequence diagram; says "document this codebase", "write docs for this", "explain how this works for the team", "we need this written up", or "same format as the other docs"; or asks to update or extend an existing generated document. Reach for it even when they do not say the word "documentation" — a request to explain a system to other people in a durable, shareable form is this skill.
---

# Documentation generator

Turn a codebase into documentation that a competent engineer would actually read
and trust: sourced, opinionated, illustrated, and produced as a Word document
with a Markdown mirror beside it.

The output is not a summary of the code. It is an explanation of the **shape and
the reasoning** — why a boundary is where it is, what a constraint encodes, what
happens when something fails — with a file path beside every claim so a reader
can check you.

## How this works

A document is a **Python script that builds a .docx**, not a hand-edited Word
file. The script is the source of truth; the Word file is a build artefact. That
is what keeps twenty documents looking like one set, and makes a correction a
one-line edit instead of an archaeology exercise.

```
scripts/
  analyze_repo.py     inventory a codebase — run this first
  docxkit.py          the Word + Markdown layer
  diagram.py          the drawing layer
templates/
  build_template.py   copy this to build_<name>.py
  render_template.py  copy this to render_<name>.py
references/
  doc-types.md        outline + what to extract, per document type
  style.md            the house style, in full
  diagrams.md         drawing recipes and failure modes
prompt.md             the full operating procedure
```

## The procedure

Seven phases, detailed in `prompt.md`. Read that file when starting real work —
this is the summary.

### 1. Understand before writing

```bash
python <skill>/scripts/analyze_repo.py <repo-root>
```

Reports languages, frameworks, tables, routes, files by role, migration order,
and which document types the codebase can support.

**Then read code.** The report is a map, not an understanding. Budget most of
your exploration here — a document written from filenames reads exactly like a
document written from filenames.

Read the entry point, the largest files by role, the data models completely, two
or three flows end to end, and the recent migrations. Stop when you can say what
would **surprise** a competent engineer seeing this for the first time. If you
cannot, you have not read enough — and finding that thing is most of the value
you add over a README.

### 2. Propose the set

Say what you found and what you would write, with a recommendation. Not a menu —
two or three sentences per document explaining why it is worth having.

Write the **Architecture Overview first** when producing more than one. The
others reference it, and writing it first surfaces what you do not yet
understand.

### 3. Outline before prose

Section headings first, nothing underneath. Read it back — if it does not tell a
story, the document will not either. Fixing an outline costs minutes.

`references/doc-types.md` has an outline per type. **Adapt it.** A schema with
no migrations does not need a migrations section; inventing one to fill the
template is how documents turn into padding.

### 4. Figures

Copy `templates/render_template.py`. One function per figure.

Draw a figure when it shows something prose cannot — a shape, an ordering, a
boundary, a comparison. Three good figures beat eight decorative ones. A reader
who learns your figures are decorative stops looking at them.

**Read every PNG you generate.** Pillow does not reflow text, so overlaps,
clipping and missing glyphs are invisible until you look. This catches something
about one time in three. `references/diagrams.md` lists the failure modes.

### 5. Write

Copy `templates/build_template.py`. Two habits while writing:

- **Cite inline**, not in a bibliography — `payments.py:63` beside the
  sentence that depends on it.
- **Record what you could not resolve.** A comment contradicting the code, a
  constraint that looks wrong, something the code does not settle. Put it in
  Open Questions with a recommendation. A document that papers over what it did
  not understand is worse than one that admits it, because the reader cannot
  tell which parts to trust.

### 6. Build and verify

```bash
python render_<name>.py     # figures
python build_<name>.py      # writes .docx and .md together
```

Then **update the table of contents** — it is a Word field and stays empty until
Word or LibreOffice evaluates it. Command in `prompt.md`. Where neither is
available, say so rather than shipping an empty contents page; the `.md` mirror
is complete and self-contained.

Then export to PDF and read the pages with figures on them.

### 7. Deliver

Page count, figure count, file locations. Then what you found that was notable,
and anything unresolved. If you found something genuinely wrong — a missing
constraint, an unenforced invariant, a race — say it in the message as well as
in the document. A finding buried in §9 has not been communicated.

## The house style, in brief

Full detail in `references/style.md`. The parts that matter most:

**Structure** — cover, orientation callout, contents, numbered sections, open
questions, sources, footer. `d.cover()` and `d.contents()` do the furniture.

**Callouts** — five kinds, each with one job:

| Kind | For |
|---|---|
| `note` | Something the reader needs but would not think to ask |
| `reuse` | Existing code that does the job — **cite a file path** |
| `build` | What genuinely has to be written |
| `warn` | A trap or constraint — **name the consequence** |
| `ui` | Verbatim UI copy |

A `warn` without a consequence is a `note`. A `reuse` without a path is a claim
the reader cannot check, which is worse than saying nothing because it will be
believed anyway.

**Tables** — widths sum to 6.55 in. Column specs `[1.5, 1.45, 0.5, 3.1]`,
endpoints `[1.15, 2.45, 0.85, 2.1]`, decisions `[0.3, 2.6, 3.65]`.

**Colour is semantic** — green works, blue new, amber caution, red gap, purple
internal, teal cross-cutting. A reader who has seen three figures knows what
amber means; do not spend that.

**Voice** — a careful colleague explaining a decision to another engineer. State
the decision, then the reason. Name consequences concretely. Say what is missing
in the same voice as what works. No hedging, and none of: simply, just,
obviously, seamless, robust, leverage.

## What makes these documents worth reading

Four things, and they are the whole difference between this and a generated
reference:

1. **Sourced.** Every claim about the code points at a file. A reader can check
   you, which is the only reason to believe you.
2. **Opinionated.** Where the code could plausibly have done otherwise, say what
   it does and why that is better or worse. A document with no judgements in it
   is a listing.
3. **Honest about gaps.** What is missing, inconsistent, or riskier than it
   looks — in the same plain voice as everything else.
4. **Illustrated where illustration helps.** A transaction boundary, a state
   machine, a layering. Never a diagram of something a sentence already covered.

## Checking the skill still works

`evals/` holds fourteen evaluations covering every document type and the edge
cases where documentation generators fail — fabricating a schema for a service
with no database, describing stubs as working code, padding a three-file project.

```bash
cd evals
python make_fixtures.py            # nine purpose-built repositories
python run_evals.py --list
python run_evals.py --tag EDGE     # the cases that catch real failures
python grade_evals.py --iteration iteration-1
```

Run it after changing anything in this skill. `evals/README.md` explains the
pass criteria and how to add cases when a new document type is introduced.

## Requirements

`python-docx` and `Pillow` — both pure Python. `PyMuPDF` for visual verification
of the built document; `pip install pymupdf` if it is missing. Word (Windows) or
LibreOffice for the table of contents; if neither is present the Markdown mirror
still works and the `.docx` is fine apart from an unpopulated contents page.

Fonts default to Segoe UI and Consolas from `C:/Windows/Fonts`. On Linux or
macOS, point `FONT_DIR` in `scripts/diagram.py` at DejaVu or any installed
sans/mono pair — nothing else changes.

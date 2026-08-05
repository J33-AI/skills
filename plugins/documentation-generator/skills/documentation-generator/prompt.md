# Operating procedure

The working method, in order. `SKILL.md` is the summary; this is the detail for
when you are partway through and want to check what comes next.

---

## Phase 1 — Understand before writing anything

Run the inventory:

```bash
python <skill>/scripts/analyze_repo.py <repo-root>
```

It reports languages, frameworks, tables, routes, files by role, migration
order, and which document types the codebase can actually support.

**Then read code.** The report is a map. It tells you where to look; it does not
tell you what anything means. Budget most of your exploration here — a document
written from filenames reads exactly like a document written from filenames.

Read, in this order:

1. **The entry point.** `main.py`, `app.ts`, `Application.java`. How does a
   request get in, what is registered, what runs at startup.
2. **The largest files by role.** The analyser lists them. Size correlates with
   where the real logic accumulated.
3. **The data models, completely.** Every column, every constraint, every
   cascade. This is where business rules hide, and it is cheap to read.
4. **Two or three representative flows** end to end, from route to database.
5. **The most recent migrations.** They tell you what changed lately and often
   why.

Stop when you can answer:

- What is this system for, in two sentences?
- What are the main components and why is the boundary where it is?
- What happens on the commonest request, step by step?
- What is stored, and what business rules are encoded in the schema?
- What would surprise a competent engineer reading this for the first time?

If you cannot answer the last one, you have not read enough. Every codebase has
something surprising, and finding it is most of the value you add.

---

## Phase 2 — Propose the set

Tell the user what you found and what you propose to write. Two or three
sentences each, not a menu:

> The backend is FastAPI with SQLAlchemy — 28 tables, 304 routes, 26 Alembic
> migrations. I'd suggest three documents: an **Architecture Overview** (the
> service layering is unusual and worth explaining), a **Database Schema** (the
> constraints encode real business rules that are not documented anywhere), and
> **API Contracts** (304 routes across 31 modules — anyone integrating will
> need this). The flows are simple enough that sequence diagrams fit inside the
> architecture document rather than needing their own.

Then ask which they want. Give a recommendation; do not present a bare list.

**Write the Architecture Overview first** when producing more than one. The
others reference it, and writing it first is how you discover what you do not
yet understand.

---

## Phase 3 — Outline before prose

For each document, write the section list first — `d.h1()` calls with nothing
underneath. Read it back. If it does not tell a story, the document will not
either, and fixing an outline costs minutes where fixing a document costs hours.

`references/doc-types.md` has the outline for each type. Adapt it. A schema with
no migrations does not need a migrations section, and inventing one to fill the
template is how documents become padding.

---

## Phase 4 — Figures

Write `render_<name>.py` from `templates/render_template.py`. One function per
figure, a `__main__` loop at the bottom.

Draw a figure when it shows something prose cannot: a shape, an ordering, a
boundary, a comparison. Do not draw one to decorate a section. Three good
figures beat eight decorative ones, and a reader who learns that your figures
are decorative stops looking at them.

Run it, then **read every PNG**. See `references/diagrams.md` for the failure
modes — they are all invisible until you look.

---

## Phase 5 — Write

Copy `templates/build_template.py`. Fill in cover, orientation, sections.

While writing, keep two habits:

**Cite as you go.** Every claim about the code names the file it came from. Not
in a bibliography at the end — inline, where the claim is. `payments.py:63`
beside the sentence that depends on it.

**Record what you could not resolve.** Something the code does not settle, a
comment contradicting the implementation, a constraint that looks wrong. Put it
in Open Questions with a recommendation. A document that quietly papers over
what it did not understand is worse than one that admits it, because the reader
cannot tell which parts to trust.

---

## Phase 6 — Build and verify

```bash
python render_<name>.py
python build_<name>.py     # writes .docx and .md together
```

Update the table of contents — it is a Word field and stays empty otherwise:

```powershell
$word = New-Object -ComObject Word.Application
$word.Visible = $false; $word.DisplayAlerts = 0
$doc = $word.Documents.Open($src)
$doc.Fields.Update() | Out-Null
try { $doc.TablesOfContents.Item(1).Update() } catch {}
$doc.Save(); $doc.ComputeStatistics(2); $doc.Close($false); $word.Quit()
```

On Linux or macOS, LibreOffice does the same:

```bash
soffice --headless --convert-to docx --outdir . out.docx
```

If neither is available, the `.md` mirror is complete and self-contained — say
so rather than shipping a document with an empty contents page.

**Then look at it.** Export to PDF, render pages, read the ones with figures:

```python
import fitz
d = fitz.open("out.pdf")
d[4].get_pixmap(dpi=88).save("p05.png")     # then Read the image
```

---

## Phase 7 — Deliver

State the page count, the figure count, and where the files are. Then, briefly:

- **What you found that was notable.** The reason the document was worth writing.
- **Anything unresolved**, and what you would need to resolve it.

If you found something genuinely wrong — a missing constraint, an unenforced
invariant, a race — say it in the message as well as the document. A finding
buried in §9 of a 20-page document has not been communicated.

---

## Working on an existing document

Edit the build script, never the `.docx`. The Word file is a build artefact; a
hand edit is lost on the next rebuild and leaves the two out of step in a way
nobody notices until it matters.

Rebuild, update the TOC, re-verify the figures you touched, and say what
changed.

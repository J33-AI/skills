# documentation-generator

Turns a codebase into documentation an engineer will read and trust: sourced,
opinionated, illustrated. Output is a `.docx` with drawn diagrams plus a
Markdown mirror.

Document types: architecture overview, database schema reference, API contract,
sequence/flow document.

## Install

```
/plugin marketplace add J33-AI/skills
/plugin install documentation-generator@j33-skills
```

No MCP server — the plugin is skill files and Python scripts only.

## Requirements

- `python-docx` and `Pillow` (pure Python) — required.
- `PyMuPDF` — optional, for visual verification of the built document.
- Word (Windows) or LibreOffice — optional, only to populate the `.docx` table
  of contents field. Without it the `.md` mirror is still complete and the
  `.docx` is fine apart from an empty contents page.

```bash
pip install python-docx Pillow pymupdf
```

Fonts default to Segoe UI and Consolas from `C:/Windows/Fonts`. On Linux/macOS,
point `FONT_DIR` in `skills/documentation-generator/scripts/diagram.py` at
DejaVu or any installed sans/mono pair.

## Layout

```
skills/documentation-generator/
  SKILL.md            what Claude loads first
  prompt.md           the full seven-phase operating procedure
  scripts/
    analyze_repo.py   codebase inventory — run this first
    docxkit.py        Word + Markdown layer
    diagram.py        drawing layer
  templates/          build_<name>.py and render_<name>.py starting points
  references/         doc-types, house style, diagram recipes
  examples/           worked example
  evals/              fourteen evaluations (see below)
```

A document is a **Python script that builds a .docx**, not a hand-edited Word
file. The script is the source of truth; the Word file is a build artefact.

## Evals

Fourteen evaluations covering every document type plus the edge cases where
documentation generators fail — fabricating a schema for a service with no
database, describing stubs as working code, padding a three-file project.

```bash
cd skills/documentation-generator/evals
python make_fixtures.py            # generates the nine fixture repos
python run_evals.py --list
python run_evals.py --tag EDGE
python grade_evals.py --iteration iteration-1
```

`fixtures/` and `workspace/` are generated and git-ignored. `evals/README.md`
explains pass criteria and how to add a case.

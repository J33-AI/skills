"""Declarative assertion checks.

An assertion in evals.json names a check type and its arguments:

    {"id": "a3", "text": "…", "check": {"type": "embedded_images", "min": 1}}

Adding a new documentation type usually needs no code here — describe what the
document must contain using the existing checks. Add a check only when you need
a genuinely new *kind* of question answered, and register it in CHECKS at the
bottom so `--list-checks` stays truthful.

Every check returns (passed, evidence). The evidence string is what a human
reads in the viewer when something fails, so make it specific: counts, file
names, the pattern that did not match.
"""

from __future__ import annotations

import os
import re
import zipfile

# ── artefact collection ────────────────────────────────────────────────────


def _docx_text(path: str) -> str:
    try:
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    except Exception:
        return ""
    return re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n"))


def _docx_media(path: str) -> int:
    try:
        return len([n for n in zipfile.ZipFile(path).namelist()
                    if n.startswith("word/media/")])
    except Exception:
        return 0


def collect(outputs_dir: str) -> dict:
    """Everything the checks need, gathered once per run."""
    files: list[str] = []
    for dirpath, _, names in os.walk(outputs_dir):
        for n in names:
            files.append(
                os.path.relpath(os.path.join(dirpath, n), outputs_dir)
                .replace(os.sep, "/"))

    def by_ext(*exts):
        return [f for f in files if f.lower().endswith(exts)]

    docx = by_ext(".docx")
    md = by_ext(".md")
    text_parts, embedded = [], 0

    for f in docx:
        p = os.path.join(outputs_dir, f)
        text_parts.append(_docx_text(p))
        embedded += _docx_media(p)
    for f in md + by_ext(".txt"):
        try:
            text_parts.append(open(os.path.join(outputs_dir, f),
                                   encoding="utf8", errors="ignore").read())
        except OSError:
            pass
    for f in by_ext(".html"):
        try:
            raw = open(os.path.join(outputs_dir, f), encoding="utf8",
                       errors="ignore").read()
            text_parts.append(re.sub(r"<[^>]+>", " ", raw))
        except OSError:
            pass

    return {
        "dir": outputs_dir,
        "files": files,
        "docx": docx,
        "md": md,
        "png": by_ext(".png"),
        "py": by_ext(".py"),
        "text": "\n".join(text_parts),
        "embedded_images": embedded,
    }


# ── individual checks ──────────────────────────────────────────────────────
# Each takes (data, **args) and returns (passed: bool, evidence: str).


def artifact_exists(d, ext=".docx", min_count=1, **_):
    """At least min_count files with this extension exist."""
    hits = [f for f in d["files"] if f.lower().endswith(ext.lower())]
    return len(hits) >= min_count, (
        f"{len(hits)} {ext} file(s): {', '.join(hits[:4]) or 'none'}")


def markdown_mirror(d, **_):
    """A .md beside the .docx, of comparable substance."""
    if not d["docx"]:
        return False, "no .docx, so no mirror to check"
    if not d["md"]:
        return False, f"{len(d['docx'])} docx but no .md mirror"
    doc_len = sum(len(_docx_text(os.path.join(d["dir"], f))) for f in d["docx"])
    md_len = 0
    for f in d["md"]:
        try:
            md_len += len(open(os.path.join(d["dir"], f), encoding="utf8",
                               errors="ignore").read())
        except OSError:
            pass
    ratio = md_len / max(doc_len, 1)
    ok = ratio >= 0.4
    return ok, (f"docx {doc_len:,} chars vs md {md_len:,} chars "
                f"(ratio {ratio:.2f}; need ≥ 0.40)")


def embedded_images(d, min=1, **_):
    """The .docx actually embeds images, not just PNGs sitting beside it."""
    return d["embedded_images"] >= min, (
        f"{d['embedded_images']} image(s) embedded in the document, "
        f"{len(d['png'])} PNG file(s) produced")


def rebuildable(d, min=1, **_):
    """Build/render scripts were saved, so the document can be regenerated."""
    return len(d["py"]) >= min, (
        f"build/render scripts saved: {', '.join(d['py'][:4]) or 'none'}")


def matches_all(d, patterns=(), **_):
    """Every pattern appears somewhere in the document text."""
    missing = [p for p in patterns
               if not re.search(p, d["text"], re.IGNORECASE | re.DOTALL)]
    return not missing, ("all patterns found" if not missing
                         else f"missing: {missing}")


def matches_any(d, patterns=(), min_distinct=1, **_):
    """At least min_distinct of the patterns appear."""
    found = [p for p in patterns
             if re.search(p, d["text"], re.IGNORECASE | re.DOTALL)]
    return len(found) >= min_distinct, (
        f"{len(found)}/{len(patterns)} matched (need {min_distinct}): "
        f"{found[:5]}")


def absent(d, patterns=(), **_):
    """Nothing here should appear — used for fabrication checks."""
    present = [p for p in patterns
               if re.search(p, d["text"], re.IGNORECASE)]
    return not present, ("none of the forbidden patterns appear"
                         if not present else f"unexpectedly present: {present}")


def citation_count(d, pattern=r"[\w/]+\.(py|ts|tsx|js|go|java|prisma|sql)", min=5,
                   **_):
    """Source files are cited at least min times."""
    n = len(re.findall(pattern, d["text"], re.IGNORECASE))
    return n >= min, f"{n} source-file citations (need {min})"


def coverage(d, terms=(), min_fraction=0.6, **_):
    """A named set of terms is covered to at least min_fraction."""
    hit = [t for t in terms
           if re.search(r"\b" + re.escape(t) + r"\b", d["text"], re.IGNORECASE)]
    frac = len(hit) / max(len(terms), 1)
    return frac >= min_fraction, (
        f"{len(hit)}/{len(terms)} terms covered ({frac:.0%}, "
        f"need {min_fraction:.0%}); missing "
        f"{[t for t in terms if t not in hit][:6]}")


def section_present(d, any_of=(), **_):
    """A section matching one of these patterns exists."""
    found = [p for p in any_of if re.search(p, d["text"], re.IGNORECASE)]
    return bool(found), (f"matched: {found[:3]}" if found
                         else f"none of {list(any_of)[:5]} found")


def has_cover(d, **_):
    """A contents heading and cover metadata are both present."""
    t = d["text"]
    contents = bool(re.search(r"\bcontents\b", t, re.IGNORECASE))
    meta = bool(re.search(r"document id|\bversion\b|\bscope\b|\baudience\b"
                          r"|\bsources?\b", t, re.IGNORECASE))
    return contents and meta, (
        f"contents heading: {contents}; cover metadata: {meta}")


def table_shape(d, headers=("Column", "Type", "Null"), **_):
    """The document uses tables with these column headings somewhere."""
    hits = [h for h in headers if re.search(r"\b" + h + r"\b", d["text"],
                                            re.IGNORECASE)]
    return len(hits) == len(headers), (
        f"{len(hits)}/{len(headers)} expected table headings present: {hits}")


def proportionality(d, max_pages=None, max_chars=None, **_):
    """Small codebase, small document. Guards against padding."""
    n = len(d["text"])
    if max_chars and n > max_chars:
        return False, f"{n:,} chars of prose exceeds the {max_chars:,} cap"
    return True, f"{n:,} chars of prose"


def figure_count(d, min=1, max=None, **_):
    """Figure count sits within bounds — max guards against over-illustration."""
    n = len(d["png"])
    if max is not None and n > max:
        return False, f"{n} figures exceeds the cap of {max}"
    return n >= min, f"{n} figure(s) generated (need ≥ {min})"


CHECKS = {
    "artifact_exists": artifact_exists,
    "markdown_mirror": markdown_mirror,
    "embedded_images": embedded_images,
    "rebuildable": rebuildable,
    "matches_all": matches_all,
    "matches_any": matches_any,
    "absent": absent,
    "citation_count": citation_count,
    "coverage": coverage,
    "section_present": section_present,
    "has_cover": has_cover,
    "table_shape": table_shape,
    "proportionality": proportionality,
    "figure_count": figure_count,
}


def run_check(spec: dict, data: dict) -> tuple[bool, str]:
    kind = spec.get("type")
    fn = CHECKS.get(kind)
    if fn is None:
        return False, f"unknown check type '{kind}'"
    args = {k: v for k, v in spec.items() if k != "type"}
    try:
        return fn(data, **args)
    except Exception as exc:                       # a broken check is a failure
        return False, f"check raised {type(exc).__name__}: {exc}"

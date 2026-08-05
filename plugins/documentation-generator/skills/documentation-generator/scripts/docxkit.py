"""Word + Markdown document builder.

Every call is recorded twice: into the .docx via python-docx, and into a
Markdown mirror. save() writes both, so a document is authored once and
reviewed either way — the .docx for people, the .md for git diffs.

Bundled with the documentation-generator skill.
"""

from __future__ import annotations

import os
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor

INK = RGBColor(0x1F, 0x29, 0x33)
MUTED = RGBColor(0x5C, 0x6B, 0x7A)
FAINT = RGBColor(0x8F, 0xA0, 0xB3)
BLUE = RGBColor(0x2F, 0x5D, 0x9E)
GREEN = RGBColor(0x2E, 0x71, 0x4A)
RED = RGBColor(0x9E, 0x3F, 0x3F)
AMBER = RGBColor(0x9A, 0x69, 0x1E)
PURPLE = RGBColor(0x59, 0x46, 0x8C)

NL = chr(10)

BODY_FONT = "Segoe UI"
MONO_FONT = "Consolas"

CALLOUTS = {
    "reuse":  ("♻  REUSE EXISTING", "E9F4EC", "3F8F5F", GREEN),
    "build":  ("✚  NEW BUILD", "EDF2FA", "3F72B4", BLUE),
    "warn":   ("⚠  WATCH OUT", "FDF3E3", "C98B2E", AMBER),
    "note":   ("NOTE", "F2F4F7", "93A3B5", MUTED),
    "ui":     ("WHAT THE USER SEES", "F4F8FD", "7FA3D0", BLUE),
}


# ── low-level xml helpers ──────────────────────────────────────────────────
def shade(cell, hex_fill: str) -> None:
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hex_fill)
    cell._tc.get_or_add_tcPr().append(el)


def cell_borders(cell, hex_colour: str, sz: int = 8, sides=("top", "left", "bottom", "right")) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in sides:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), hex_colour)
        borders.append(el)
    tcPr.append(borders)


def no_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        borders.append(el)
    tbl_pr.append(borders)


def cell_margins(cell, top=80, bottom=80, left=120, right=120) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for name, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{name}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def keep_with_next(par) -> None:
    par.paragraph_format.keep_with_next = True


class Doc:
    def __init__(self, *, landscape_images_width_in: float = 6.55,
                 md_fig_dir: str = "diagrams") -> None:
        self.d = Document()
        self.img_w = Inches(landscape_images_width_in)
        self._setup_page()
        self._setup_styles()
        self.fig_no = 0
        self._md: list[str] = []       # Markdown mirror
        self._md_fig_dir = md_fig_dir  # relative dir used in image links
        self.title_text = ""

    # ── setup ──────────────────────────────────────────────────────────────
    def _setup_page(self) -> None:
        s = self.d.sections[0]
        s.page_width, s.page_height = Mm(210), Mm(297)
        s.left_margin = s.right_margin = Mm(20)
        s.top_margin = Mm(20)
        s.bottom_margin = Mm(18)

    def _setup_styles(self) -> None:
        st = self.d.styles
        normal = st["Normal"]
        normal.font.name = BODY_FONT
        normal.font.size = Pt(10)
        normal.font.color.rgb = INK
        normal.paragraph_format.space_after = Pt(7)
        normal.paragraph_format.line_spacing = 1.18
        rpr = normal.element.get_or_add_rPr()
        rfonts = rpr.get_or_add_rFonts()
        rfonts.set(qn("w:eastAsia"), BODY_FONT)

        for name, size, colour, before, after in (
            ("Heading 1", 19, INK, 22, 8),
            ("Heading 2", 14, BLUE, 16, 6),
            ("Heading 3", 11.5, INK, 12, 4),
        ):
            h = st[name]
            h.font.name = BODY_FONT
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = colour
            h.paragraph_format.space_before = Pt(before)
            h.paragraph_format.space_after = Pt(after)
            h.paragraph_format.keep_with_next = True

    # ── inline markup: **bold**, `code`, _italic_ ───────────────────────────
    def _runs(self, par, text: str, *, size=None, colour=None, bold=False):
        for token in re.split(r"(\*\*.+?\*\*|`[^`]+`|_[^_]+_)", text):
            if not token:
                continue
            run = par.add_run()
            if token.startswith("**") and token.endswith("**"):
                run.text, run.bold = token[2:-2], True
            elif token.startswith("`") and token.endswith("`"):
                run.text = token[1:-1]
                run.font.name = MONO_FONT
                run.font.size = Pt((size or 10) - 1)
                run.font.color.rgb = PURPLE
            elif token.startswith("_") and token.endswith("_"):
                run.text, run.italic = token[1:-1], True
            else:
                run.text = token
            if bold:
                run.bold = True
            if size and run.font.size is None:
                run.font.size = Pt(size)
            if colour and run.font.color.rgb is None:
                run.font.color.rgb = colour
        return par

    # ── blocks ─────────────────────────────────────────────────────────────
    def h1(self, text, *, page_break=False):
        if page_break:
            self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        p = self.d.add_heading(level=1)
        self._runs(p, text)
        self._md.append("" + NL + "## " + text + NL)
        return p

    def h2(self, text):
        p = self.d.add_heading(level=2)
        self._runs(p, text)
        self._md.append("" + NL + "### " + text + NL)
        return p

    def h3(self, text):
        p = self.d.add_heading(level=3)
        self._runs(p, text)
        self._md.append("" + NL + "#### " + text + NL)
        return p

    def p(self, text="", *, size=None, colour=None, space_after=None, italic=False,
          align=None):
        par = self.d.add_paragraph()
        self._runs(par, text, size=size, colour=colour)
        if italic:
            for r in par.runs:
                r.italic = True
        if space_after is not None:
            par.paragraph_format.space_after = Pt(space_after)
        if align:
            par.alignment = align
        if text:
            body = ("_" + text + "_") if italic else text
            self._md.append("" + NL + body + NL)
        return par

    def bullet(self, text, *, level=0):
        par = self.d.add_paragraph(style="List Bullet")
        par.paragraph_format.left_indent = Inches(0.25 + 0.25 * level)
        par.paragraph_format.space_after = Pt(3)
        self._runs(par, text)
        self._md.append("- " + text)
        return par

    def numbered(self, text):
        par = self.d.add_paragraph(style="List Number")
        par.paragraph_format.left_indent = Inches(0.25)
        par.paragraph_format.space_after = Pt(3)
        self._runs(par, text)
        self._md.append("1. " + text)
        return par

    def code(self, text: str, *, fill="F4F6F9"):
        rows = text.strip("\n").split("\n")
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        cell = t.cell(0, 0)
        shade(cell, fill)
        cell_borders(cell, "DCE2E9")
        cell_margins(cell, 110, 110, 140, 140)
        cell.paragraphs[0]._p.getparent().remove(cell.paragraphs[0]._p)
        for line in rows:
            par = cell.add_paragraph()
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            run = par.add_run(line if line.strip() else " ")
            run.font.name = MONO_FONT
            run.font.size = Pt(8.5)
            run.font.color.rgb = INK
        self.p("", space_after=2)
        self._md.append("" + NL + "```" + NL + text.strip(NL)
                        + NL + "```" + NL)
        return t

    def callout(self, kind: str, lines: list[str], *, title: str | None = None):
        label, fill, border, colour = CALLOUTS[kind]
        t = self.d.add_table(rows=1, cols=1)
        cell = t.cell(0, 0)
        shade(cell, fill)
        cell_borders(cell, border, sz=6)
        cell_margins(cell, 120, 120, 150, 150)
        cell.paragraphs[0]._p.getparent().remove(cell.paragraphs[0]._p)

        head = cell.add_paragraph()
        head.paragraph_format.space_after = Pt(4)
        run = head.add_run(title or label)
        run.bold = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = colour

        for line in lines:
            par = cell.add_paragraph()
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.line_spacing = 1.12
            if line.startswith("- "):
                par.paragraph_format.left_indent = Inches(0.16)
                self._runs(par, "•  " + line[2:], size=9)
            else:
                self._runs(par, line, size=9)
            for r in par.runs:
                if r.font.size is None:
                    r.font.size = Pt(9)
        self.p("", space_after=2)
        md = ["" + NL + "> **" + (title or label) + "**", ">"]
        for line in lines:
            md.append("> " + line if line else ">")
        self._md.append(NL.join(md) + NL)
        return t

    def table(self, header: list[str], rows: list[list[str]], widths: list[float],
              *, header_fill="E7EDF6", font_size=9, zebra=True, show_header=True):
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for i, w in enumerate(widths):
            for cell in t.columns[i].cells:
                cell.width = Inches(w)
        for i, text in enumerate(header):
            cell = t.cell(0, i)
            cell.width = Inches(widths[i])
            shade(cell, header_fill)
            cell_margins(cell, 60, 60, 90, 90)
            par = cell.paragraphs[0]
            par.paragraph_format.space_after = Pt(0)
            self._runs(par, text, size=font_size)
            for r in par.runs:
                r.bold = True
                r.font.size = Pt(font_size)
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for i, text in enumerate(row):
                cell = cells[i]
                cell.width = Inches(widths[i])
                cell_margins(cell, 60, 60, 90, 90)
                if zebra and ri % 2 == 1:
                    shade(cell, "FAFBFD")
                par = cell.paragraphs[0]
                par.paragraph_format.space_after = Pt(0)
                par.paragraph_format.line_spacing = 1.1
                self._runs(par, text, size=font_size)
                for r in par.runs:
                    if r.font.size is None:
                        r.font.size = Pt(font_size)
        md_head = header if show_header else [chr(32) for _ in header]
        md = ["" + NL + "| " + " | ".join(md_head) + " |",
              "|" + "|".join(["---"] * len(header)) + "|"]
        for row in rows:
            cells = [str(cell).replace(NL, chr(60) + 'br' + chr(62))
                     for cell in row]
            md.append("| " + " | ".join(cells) + " |")
        self._md.append(NL.join(md) + NL)
        if not show_header:
            hdr = t.rows[0]._tr
            hdr.getparent().remove(hdr)
        else:
            # repeat the header row when the table breaks across pages
            trPr = t.rows[0]._tr.get_or_add_trPr()
            el = OxmlElement("w:tblHeader")
            el.set(qn("w:val"), "true")
            trPr.append(el)
        self.p("", space_after=2)
        return t

    def figure(self, path: str, caption: str, *, width_in: float | None = None):
        self.fig_no += 1
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.space_after = Pt(3)
        par.add_run().add_picture(path, width=Inches(width_in) if width_in else self.img_w)
        cap = self.d.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(12)
        run = cap.add_run(f"Figure {self.fig_no} — {caption}")
        run.italic = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = MUTED
        link = self._md_fig_dir + "/" + os.path.basename(path)
        self._md.append("" + NL + "![" + caption + "](" + link + ")"
                        + NL + NL + "*Figure " + str(self.fig_no)
                        + " — " + caption + "*" + NL)
        return par

    def rule(self, *, space_before=6, space_after=6):
        par = self.d.add_paragraph()
        par.paragraph_format.space_before = Pt(space_before)
        par.paragraph_format.space_after = Pt(space_after)
        pPr = par._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:color"), "D9E0E8")
        borders.append(bottom)
        pPr.append(borders)
        self._md.append("" + NL + "---" + NL)
        return par

    def toc(self):
        par = self.d.add_paragraph()
        run = par.add_run()
        fld = OxmlElement("w:fldChar")
        fld.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = 'TOC \\o "1-2" \\h \\z \\u'
        sep = OxmlElement("w:fldChar")
        sep.set(qn("w:fldCharType"), "separate")
        placeholder = OxmlElement("w:t")
        placeholder.text = "Right-click and choose “Update Field” to build the table of contents."
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        for el in (fld, instr, sep, placeholder, end):
            run._r.append(el)
        return par

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def footer_text(self, text: str):
        footer = self.d.sections[0].footer
        par = footer.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = par.add_run(text)
        run.font.size = Pt(8)
        run.font.color.rgb = FAINT
        run.font.name = BODY_FONT

    def save(self, path: str, *, markdown: bool | str = True) -> str:
        """Write the .docx, and by default a Markdown mirror beside it.

        markdown=False skips the mirror; a string writes it to that path.
        """
        target_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(target_dir, exist_ok=True)
        self.d.save(path)
        if markdown:
            md_path = (markdown if isinstance(markdown, str)
                       else os.path.splitext(path)[0] + ".md")
            body = NL.join(self._md)
            while NL * 3 in body:
                body = body.replace(NL * 3, NL * 2)
            head = ("# " + self.title_text + NL) if self.title_text else ""
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(head + body.lstrip(NL))
        return path

    # ── standard document furniture ─────────────────────────────────
    def cover(self, programme: str, title: str, subtitle: str = '',
              tagline: str = '', meta_rows=None, *, title_size: int = 28):
        """The four-part cover plus the metadata table.

        programme  small bold blue line above the title
        title      the document name
        subtitle   optional muted second line
        tagline    blue line naming the document type
        meta_rows  [[label, value], ...] — rendered without a header row
        """
        self.title_text = title
        self.p("", space_after=40)
        par = self.p(programme, size=10.5)
        par.runs[0].bold = True
        par.runs[0].font.color.rgb = BLUE

        t = self.d.add_paragraph()
        r = t.add_run(title)
        r.bold = True
        r.font.size = Pt(title_size)
        r.font.color.rgb = INK
        t.paragraph_format.space_after = Pt(0)

        if subtitle:
            t = self.d.add_paragraph()
            r = t.add_run(subtitle)
            r.font.size = Pt(16)
            r.font.color.rgb = MUTED
            t.paragraph_format.space_after = Pt(4)

        if tagline:
            t = self.d.add_paragraph()
            r = t.add_run(tagline)
            r.bold = True
            r.font.size = Pt(15)
            r.font.color.rgb = BLUE
            t.paragraph_format.space_after = Pt(24)

        self._md = ['*' + programme + '*', '']
        if tagline or subtitle:
            self._md += ['**' + (tagline or subtitle) + '**', '']
        self.rule(space_before=0, space_after=14)
        if meta_rows:
            self.table(["", ""], meta_rows, [1.7, 4.85],
                       header_fill="FFFFFF", font_size=9.5, zebra=False,
                       show_header=False)
        return self

    def contents(self):
        """Page break, a plain bold Contents, then the TOC field.

        Deliberately not an h1 — an h1 lists itself in its own contents.
        """
        self.page_break()
        h = self.d.add_paragraph()
        r = h.add_run("Contents")
        r.bold = True
        r.font.size = Pt(19)
        r.font.color.rgb = INK
        h.paragraph_format.space_after = Pt(10)
        return self.toc()

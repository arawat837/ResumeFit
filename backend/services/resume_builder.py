"""
backend/services/resume_builder.py
Generates ATS-compliant .docx and .pdf resumes with accepted Google XYZ bullet rewrites applied.
Supports 3 curated university student template layouts:
1. 'ivy_league' (Harvard/Wharton format: centered header, academic order, classic serif/clean styling)
2. 'tech_minimalist' (Stanford/CMU CS format: skills-first, left-aligned, high information density)
3. 'modern_corporate' (Consulting / Business Analyst format: sky-blue accent headings, executive hierarchy)
"""

import io
import re
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table

logger = logging.getLogger("resumefit.builder")


def add_p_bottom_border(paragraph, color_hex: str = "CCCCCC", sz: str = "4", space: str = "3"):
    """Adds a real bottom divider border line to paragraph using direct OOXML w:pBdr."""
    pPr = paragraph._p.get_or_add_pPr()
    existing = pPr.find(qn('w:pBdr'))
    if existing is not None:
        pPr.remove(existing)
    bdr_xml = f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="{sz}" w:space="{space}" w:color="{color_hex}"/></w:pBdr>'
    pPr.append(parse_xml(bdr_xml))


def set_table_borders_none(table):
    """Removes all visible borders from a docx table."""
    tblPr = table._tbl.tblPr
    existing = tblPr.find(qn('w:tblBdr'))
    if existing is not None:
        tblPr.remove(existing)
    tblBdr_xml = (
        f'<w:tblBdr {nsdecls("w")}>'
        '<w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/>'
        '<w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/>'
        '</w:tblBdr>'
    )
    tblPr.append(parse_xml(tblBdr_xml))


def set_cell_shading(cell, color_hex: str):
    """Sets background fill color of a docx table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    tcPr.append(parse_xml(shd_xml))


def set_cell_margins(cell, top: int = 0, bottom: int = 0, left: int = 140, right: int = 0):
    """Sets internal padding/margins for a docx table cell (in dxa: 20 dxa = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    mar_xml = (
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        '</w:tcMar>'
    )
    tcPr.append(parse_xml(mar_xml))


def estimate_content_density(parsed_resume: Dict[str, Any]) -> bool:
    """
    Estimates whether content will exceed a single page.
    Rough heuristic: total bullet count + total section/role entry count.
    Returns True if content is dense and should have base font sizes scaled down.
    """
    exp = parsed_resume.get("experience", [])
    proj = parsed_resume.get("projects", [])
    lead = parsed_resume.get("leadership", [])
    edu = parsed_resume.get("education", [])
    skills = parsed_resume.get("skills", [])
    skills_lines = parsed_resume.get("skills_raw_lines", [])

    total_bullets = sum(len(e.get("bullets", [])) for e in exp + proj + lead)
    total_entries = len(exp) + len(proj) + len(lead) + len(edu)
    total_skills = len(skills_lines) if skills_lines else (len(skills) // 3)

    return (total_bullets + total_entries + total_skills) > 17



CURATED_TEMPLATES = {
    "original": {
        "id": "original",
        "name": "Keep Original Format",
        "subtitle": "Your Existing Resume Layout",
        "desc": "Preserves your exact resume structure & section order; makes surgical in-place bullet replacements only.",
        "font_docx": "Calibri",
        "font_pdf": "Helvetica",
        "font_pdf_bold": "Helvetica-Bold",
        "accent_hex": "#0F172A",
        "align": "center",
        "order": ["education", "experience", "projects", "leadership", "skills"]
    },
    "ivy_league": {
        "id": "ivy_league",
        "name": "Ivy League / Classic University",
        "subtitle": "Harvard & Wharton Standard",
        "desc": "Centered header, classic academic ordering (Education → Experience → Projects → Skills), elegant typography.",
        "font_docx": "Georgia",
        "font_pdf": "Times-Roman",
        "font_pdf_bold": "Times-Bold",
        "accent_hex": "#1E293B",
        "align": "center",
        "order": ["education", "experience", "projects", "leadership", "skills"]
    },
    "tech_minimalist": {
        "id": "tech_minimalist",
        "name": "Tech Minimalist",
        "subtitle": "Silicon Valley & CMU Standard",
        "desc": "Technical Skills first for 6-second recruiter scans, compact bullet spacing, high density.",
        "font_docx": "Arial",
        "font_pdf": "Helvetica",
        "font_pdf_bold": "Helvetica-Bold",
        "accent_hex": "#0F172A",
        "align": "left",
        "order": ["skills", "projects", "experience", "education", "leadership"]
    },
    "modern_corporate": {
        "id": "modern_corporate",
        "name": "Modern Corporate & Consulting",
        "subtitle": "McKinsey & Business Analyst Standard",
        "desc": "Sky-blue section accents, structured metric emphasis, balanced corporate hierarchy.",
        "font_docx": "Calibri",
        "font_pdf": "Helvetica",
        "font_pdf_bold": "Helvetica-Bold",
        "accent_hex": "#0284C7",
        "align": "left",
        "order": ["experience", "projects", "education", "leadership", "skills"]
    }
}


def apply_bullet_rewrites(
    item_list: List[Dict[str, Any]],
    applied_rewrites: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Substitutes matched original bullets with accepted rewrite_bullet in experience/project blocks."""
    rewrite_map = {}
    for rw in applied_rewrites:
        orig = (rw.get("original_bullet") or "").strip().lower()
        replacement = rw.get("rewrite_bullet")
        if orig and replacement:
            rewrite_map[orig] = replacement.strip()

    updated_items = []
    for item in item_list:
        new_item = dict(item)
        original_bullets = item.get("bullets", [])
        new_bullets = []

        for bullet in original_bullets:
            clean_b = bullet.strip().lstrip("-•* ").strip().lower()
            matched_rewrite = None
            for orig_key, rw_val in rewrite_map.items():
                if orig_key in clean_b or clean_b in orig_key:
                    matched_rewrite = rw_val
                    break

            if matched_rewrite:
                new_bullets.append(matched_rewrite)
            else:
                new_bullets.append(bullet)

        new_item["bullets"] = new_bullets
        updated_items.append(new_item)

    return updated_items


def replace_in_paragraph_runs(paragraph, orig: str, new_b: str) -> bool:
    """
    Substitutes matched original bullet text with new_b strictly at the Run level.
    Only the characters in overlapping runs are modified.
    All preceding, subsequent, and un-overlapped runs, run properties (b, i, u, color, size, font),
    and paragraph properties are preserved byte-for-byte.
    Handles spans across multiple runs by writing new_b at the first overlapping run
    and clearing the matched text in subsequent overlapping runs.
    """
    if not paragraph.runs:
        return False

    full_text = "".join(r.text for r in paragraph.runs)
    if not full_text.strip():
        return False

    clean_orig = orig.strip()
    if not clean_orig:
        return False

    # Attempt 1: Exact substring match (case-insensitive)
    idx = full_text.lower().find(clean_orig.lower())
    match_len = len(clean_orig)

    # Attempt 2: If orig starts with bullet glyphs/numbers/whitespace, strip them
    if idx == -1:
        stripped_orig = re.sub(
            r"^[\s\t•\*\-\–\—\·\u2022\u25cf\uf0b7\uf0a7\u25aa\u25e6\u25cb\u2043\u2219\u2713\(\d+\)\.]+\s*",
            "",
            clean_orig
        ).strip()
        if stripped_orig:
            idx = full_text.lower().find(stripped_orig.lower())
            match_len = len(stripped_orig)

    # Attempt 3: Trailing period variations
    if idx == -1:
        no_dot = clean_orig.rstrip(".")
        if no_dot:
            idx = full_text.lower().find(no_dot.lower())
            match_len = len(no_dot)

    # Attempt 4: Multi-word prefix match for slightly trimmed parser bullets
    if idx == -1 and len(clean_orig) > 30:
        prefix = clean_orig[:30].lower()
        idx_prefix = full_text.lower().find(prefix)
        if idx_prefix != -1:
            idx = idx_prefix
            # Match up to the end of the paragraph/sentence
            match_len = len(full_text) - idx_prefix

    if idx == -1:
        return False

    end = idx + match_len
    pos = 0
    first_overlap = True

    for run in paragraph.runs:
        run_len = len(run.text)
        run_start = pos
        run_end = pos + run_len

        if run_start < end and run_end > idx:
            local_start = max(0, idx - run_start)
            local_end = min(run_len, end - run_start)

            replacement = new_b if first_overlap else ""
            run.text = run.text[:local_start] + replacement + run.text[local_end:]
            first_overlap = False

        pos += run_len

    return True


def apply_rewrites_to_custom_docx(
    custom_docx_bytes: bytes,
    applied_rewrites: List[Dict[str, Any]]
) -> bytes:
    """
    Takes an uploaded custom or original .docx file and applies Google XYZ bullet rewrites
    in place at the Run level, preserving 100% of formatting, layout, fonts, and un-overlapped text.
    """
    if not applied_rewrites:
        return custom_docx_bytes

    doc = Document(io.BytesIO(custom_docx_bytes))

    replacements = []
    for rw in applied_rewrites:
        orig = (rw.get("original_bullet") or "").strip()
        new_b = (rw.get("rewrite_bullet") or "").strip()
        if orig and new_b:
            replacements.append((orig, new_b))

    if not replacements:
        return custom_docx_bytes

    # Collect all paragraphs from document body and all table cells (including nested tables)
    def collect_all_paragraphs(container):
        paragraphs = list(container.paragraphs)
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    paragraphs.extend(collect_all_paragraphs(cell))
        return paragraphs

    all_paragraphs = collect_all_paragraphs(doc)

    for orig, new_b in replacements:
        for p in all_paragraphs:
            if replace_in_paragraph_runs(p, orig, new_b):
                break

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def convert_docx_to_pdf_via_libreoffice(docx_bytes: bytes) -> Optional[bytes]:
    """
    Attempts headless conversion of DOCX bytes to PDF using LibreOffice/soffice if installed on server.
    Returns None if LibreOffice is not available or if conversion fails.
    """
    soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_path:
        return None

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_file = tmp_path / "resume_in.docx"
            input_file.write_bytes(docx_bytes)

            cmd = [
                soffice_path,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_path),
                str(input_file)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if res.returncode == 0:
                output_pdf = tmp_path / "resume_in.pdf"
                if output_pdf.exists():
                    return output_pdf.read_bytes()
    except Exception as e:
        logger.warning(f"LibreOffice DOCX-to-PDF conversion failed: {e}")
        return None

    return None


def _format_skill_line(paragraph, text: str, font_name: str, body_pt: float):
    if ":" in text:
        cat, val = text.split(":", 1)
        r_cat = paragraph.add_run(cat + ": ")
        r_cat.bold = True
        r_cat.font.size = Pt(body_pt)
        r_cat.font.name = font_name
        r_val = paragraph.add_run(val.strip())
        r_val.font.size = Pt(body_pt)
        r_val.font.name = font_name
    else:
        r = paragraph.add_run(text)
        r.font.size = Pt(body_pt)
        r.font.name = font_name


def build_docx_resume(
    parsed_resume: Dict[str, Any],
    applied_rewrites: Optional[List[Dict[str, Any]]] = None,
    template_id: str = "original"
) -> bytes:
    """Generates an ATS-compliant Word document (.docx) according to chosen template."""
    tmpl = CURATED_TEMPLATES.get(template_id, CURATED_TEMPLATES["original"])
    doc = Document()

    # 1. Standard ATS 0.75" Margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    contact = parsed_resume.get("contact", {})
    name = contact.get("name") or parsed_resume.get("candidate_name") or "CANDIDATE NAME"
    font_name = tmpl["font_docx"]
    is_center = tmpl["align"] == "center"

    # Hex to RGB
    hex_clean = tmpl["accent_hex"].lstrip("#")
    r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    accent_rgb = RGBColor(r, g, b)

    is_dense = estimate_content_density(parsed_resume)
    is_tech = template_id == "tech_minimalist"
    is_ivy = template_id == "ivy_league"
    is_corp = template_id == "modern_corporate"

    # Base typography with density reduction fallback (reduce base font size by 0.5-1pt if dense)
    if is_dense:
        name_pt = 15.5
        h2_pt = 10.5
        item_pt = 9.5
        sub_pt = 9.0
        body_pt = 8.5
        contact_pt = 8.5
    else:
        name_pt = 17.0
        h2_pt = 11.5
        item_pt = 10.5
        sub_pt = 9.5
        body_pt = 9.5
        contact_pt = 9.5

    space_factor = 0.75 if (is_tech or is_dense) else 1.0

    # 2. Header: Name & Contact
    name_para = doc.add_paragraph()
    if is_center:
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_para.paragraph_format.space_before = Pt(0)
    name_para.paragraph_format.space_after = Pt(2)
    run_name = name_para.add_run(name.upper())
    run_name.bold = True
    run_name.font.size = Pt(name_pt)
    run_name.font.name = font_name
    run_name.font.color.rgb = RGBColor(15, 23, 42)

    # ivy_league: add thin rule under candidate name (not just section headers)
    if is_ivy:
        add_p_bottom_border(name_para, color_hex=hex_clean, sz="6", space="4")

    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(f"Mobile: {contact['phone']}")
    if contact.get("email"):
        contact_parts.append(f"Email: {contact['email']}")
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact.get("location"):
        contact_parts.append(contact["location"])

    if contact_parts:
        contact_para = doc.add_paragraph()
        if is_center:
            contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_para.paragraph_format.space_before = Pt(2)
        contact_para.paragraph_format.space_after = Pt(6 * space_factor)
        run_contact = contact_para.add_run(" | ".join(contact_parts))
        run_contact.font.size = Pt(contact_pt)
        run_contact.font.name = font_name
        run_contact.font.color.rgb = RGBColor(100, 116, 139)

    def add_section_header(title: str):
        h_para = doc.add_paragraph()
        h_para.paragraph_format.space_before = Pt(8 * space_factor)
        h_para.paragraph_format.space_after = Pt(3 * space_factor)
        h_run = h_para.add_run(title.upper())
        h_run.bold = True
        h_run.font.size = Pt(h2_pt)
        h_run.font.name = font_name
        h_run.font.color.rgb = accent_rgb

        # ivy_league: academic small_caps on section headers
        if is_ivy:
            h_run.font.small_caps = True

        # Real section-header divider line using direct OOXML w:pBdr
        add_p_bottom_border(h_para, color_hex=hex_clean, sz="4", space="3")

    def add_custom_bullet_to_container(container, text: str, is_last: bool = False):
        b_para = container.add_paragraph()
        b_para.paragraph_format.left_indent = Inches(0.22)
        b_para.paragraph_format.first_line_indent = Inches(-0.14)
        b_para.paragraph_format.space_before = Pt(0)
        b_para.paragraph_format.space_after = Pt((4 if is_last else 1.2) * space_factor)
        b_para.paragraph_format.line_spacing = 1.05

        # Literal bullet character run colored with template accent
        b_glyph = b_para.add_run("• ")
        b_glyph.bold = True
        b_glyph.font.size = Pt(body_pt)
        b_glyph.font.name = font_name
        b_glyph.font.color.rgb = accent_rgb

        # Content run
        t_run = b_para.add_run(text)
        t_run.font.size = Pt(body_pt)
        t_run.font.name = font_name
        t_run.font.color.rgb = RGBColor(30, 41, 59)
        return b_para

    def render_education():
        education = parsed_resume.get("education", [])
        if not education:
            return
        add_section_header("Education")
        for edu_idx, edu in enumerate(education):
            inst = edu.get("institution") or ""
            degree = edu.get("degree") or ""
            year = edu.get("year") or ""

            edu_para = doc.add_paragraph()
            edu_para.paragraph_format.space_before = Pt(2 * space_factor)
            edu_para.paragraph_format.space_after = Pt(0)
            if inst:
                run_inst = edu_para.add_run(inst)
                run_inst.bold = True
                run_inst.font.size = Pt(item_pt)
                run_inst.font.name = font_name
            if year:
                run_yr = edu_para.add_run(f" | {year}")
                run_yr.font.size = Pt(sub_pt)
                run_yr.font.color.rgb = RGBColor(100, 116, 139)

            if degree:
                deg_para = doc.add_paragraph()
                deg_para.paragraph_format.space_before = Pt(0)
                deg_para.paragraph_format.space_after = Pt((4 if edu_idx == len(education) - 1 else 1.5) * space_factor)
                run_deg = deg_para.add_run(degree)
                run_deg.font.size = Pt(sub_pt)
                run_deg.font.name = font_name

    def render_experience():
        raw_exp = parsed_resume.get("experience", [])
        if not raw_exp:
            return
        add_section_header("Experience")
        updated_exp = apply_bullet_rewrites(raw_exp, applied_rewrites or [])

        for exp_idx, exp in enumerate(updated_exp):
            role = exp.get("role") or ""
            company = exp.get("company") or ""
            dur = exp.get("duration") or ""
            header_text = role + (f" | {company}" if company else "")
            if not header_text:
                header_text = "Position"

            bullets = [b.strip().lstrip("-•* ").strip() for b in exp.get("bullets", []) if b.strip().lstrip("-•* ").strip()]
            is_last_exp = (exp_idx == len(updated_exp) - 1)

            if is_corp:
                # 2-column table with thin colored left accent bar (0.05" wide)
                entry_table = doc.add_table(rows=1, cols=2)
                set_table_borders_none(entry_table)

                # Col 0: Accent bar
                bar_cell = entry_table.cell(0, 0)
                bar_cell.width = Inches(0.05)
                set_cell_shading(bar_cell, hex_clean)
                p_bar = bar_cell.paragraphs[0]
                p_bar.paragraph_format.space_before = Pt(0)
                p_bar.paragraph_format.space_after = Pt(0)
                p_bar.paragraph_format.line_spacing = Pt(2)

                # Col 1: Content
                content_cell = entry_table.cell(0, 1)
                content_cell.width = Inches(6.90)
                set_cell_margins(content_cell, top=0, bottom=40, left=140, right=0)

                p_role = content_cell.paragraphs[0]
                p_role.paragraph_format.space_before = Pt(1)
                p_role.paragraph_format.space_after = Pt(1)
                r_role = p_role.add_run(header_text)
                r_role.bold = True
                r_role.font.size = Pt(item_pt)
                r_role.font.name = font_name
                if dur:
                    r_dur = p_role.add_run(f" | {dur}")
                    r_dur.font.size = Pt(sub_pt)
                    r_dur.font.color.rgb = RGBColor(100, 116, 139)

                for b_idx, bullet in enumerate(bullets):
                    add_custom_bullet_to_container(content_cell, bullet, is_last=(b_idx == len(bullets) - 1))
            else:
                p_role = doc.add_paragraph()
                p_role.paragraph_format.space_before = Pt(3 * space_factor)
                p_role.paragraph_format.space_after = Pt(1)
                r_role = p_role.add_run(header_text)
                r_role.bold = True
                r_role.font.size = Pt(item_pt)
                r_role.font.name = font_name
                if dur:
                    r_dur = p_role.add_run(f" | {dur}")
                    r_dur.font.size = Pt(sub_pt)
                    r_dur.font.color.rgb = RGBColor(100, 116, 139)

                for b_idx, bullet in enumerate(bullets):
                    is_last_b = is_last_exp and (b_idx == len(bullets) - 1)
                    add_custom_bullet_to_container(doc, bullet, is_last=is_last_b)

    def render_projects():
        raw_proj = parsed_resume.get("projects", [])
        if not raw_proj:
            return
        add_section_header("Projects")
        updated_proj = apply_bullet_rewrites(raw_proj, applied_rewrites or [])

        for proj_idx, proj in enumerate(updated_proj):
            title = proj.get("title") or "Project"
            org = proj.get("organization") or ""
            dur = proj.get("duration") or ""
            header_text = title + (f" | {org}" if org else "")

            bullets = [b.strip().lstrip("-•* ").strip() for b in proj.get("bullets", []) if b.strip().lstrip("-•* ").strip()]
            is_last_proj = (proj_idx == len(updated_proj) - 1)

            if is_corp:
                entry_table = doc.add_table(rows=1, cols=2)
                set_table_borders_none(entry_table)

                bar_cell = entry_table.cell(0, 0)
                bar_cell.width = Inches(0.05)
                set_cell_shading(bar_cell, hex_clean)
                p_bar = bar_cell.paragraphs[0]
                p_bar.paragraph_format.space_before = Pt(0)
                p_bar.paragraph_format.space_after = Pt(0)
                p_bar.paragraph_format.line_spacing = Pt(2)

                content_cell = entry_table.cell(0, 1)
                content_cell.width = Inches(6.90)
                set_cell_margins(content_cell, top=0, bottom=40, left=140, right=0)

                p_p = content_cell.paragraphs[0]
                p_p.paragraph_format.space_before = Pt(1)
                p_p.paragraph_format.space_after = Pt(1)
                r_p = p_p.add_run(header_text)
                r_p.bold = True
                r_p.font.size = Pt(item_pt)
                r_p.font.name = font_name
                if dur:
                    r_dur = p_p.add_run(f" | {dur}")
                    r_dur.font.size = Pt(sub_pt)
                    r_dur.font.color.rgb = RGBColor(100, 116, 139)

                for b_idx, bullet in enumerate(bullets):
                    add_custom_bullet_to_container(content_cell, bullet, is_last=(b_idx == len(bullets) - 1))
            else:
                p_p = doc.add_paragraph()
                p_p.paragraph_format.space_before = Pt(3 * space_factor)
                p_p.paragraph_format.space_after = Pt(1)
                r_p = p_p.add_run(header_text)
                r_p.bold = True
                r_p.font.size = Pt(item_pt)
                r_p.font.name = font_name
                if dur:
                    r_dur = p_p.add_run(f" | {dur}")
                    r_dur.font.size = Pt(sub_pt)
                    r_dur.font.color.rgb = RGBColor(100, 116, 139)

                for b_idx, bullet in enumerate(bullets):
                    is_last_b = is_last_proj and (b_idx == len(bullets) - 1)
                    add_custom_bullet_to_container(doc, bullet, is_last=is_last_b)

    def render_leadership():
        raw_lead = parsed_resume.get("leadership", [])
        if not raw_lead:
            return
        add_section_header("Leadership & Involvement")
        updated_lead = apply_bullet_rewrites(raw_lead, applied_rewrites or [])

        for lead_idx, lead in enumerate(updated_lead):
            role = lead.get("role") or "Leadership"
            org = lead.get("organization") or ""
            header_text = role + (f" | {org}" if org else "")

            l_para = doc.add_paragraph()
            l_para.paragraph_format.space_before = Pt(3 * space_factor)
            l_para.paragraph_format.space_after = Pt(1)
            run_l = l_para.add_run(header_text)
            run_l.bold = True
            run_l.font.size = Pt(item_pt)
            run_l.font.name = font_name

            bullets = [b.strip().lstrip("-•* ").strip() for b in lead.get("bullets", []) if b.strip().lstrip("-•* ").strip()]
            is_last_lead = (lead_idx == len(updated_lead) - 1)
            for b_idx, bullet in enumerate(bullets):
                is_last_b = is_last_lead and (b_idx == len(bullets) - 1)
                add_custom_bullet_to_container(doc, bullet, is_last=is_last_b)

    def render_skills():
        raw_lines = parsed_resume.get("skills_raw_lines", [])
        skills = parsed_resume.get("skills", [])
        if not raw_lines and not skills:
            return
        add_section_header("Technical Skills" if is_tech else "Skills & Interests")

        if is_tech:
            # Compact 2-column skills table with no visible borders
            items = []
            if raw_lines:
                items = [line.strip() for line in raw_lines if line.strip()]
            else:
                half = (len(skills) + 1) // 2
                items = [", ".join(skills[:half]), ", ".join(skills[half:])]

            pairs = []
            for i in range(0, len(items), 2):
                l_item = items[i]
                r_item = items[i + 1] if (i + 1) < len(items) else ""
                pairs.append((l_item, r_item))

            tbl = doc.add_table(rows=len(pairs), cols=2)
            set_table_borders_none(tbl)
            for r_idx, (left_txt, right_txt) in enumerate(pairs):
                c_left = tbl.cell(r_idx, 0)
                c_left.width = Inches(3.5)
                set_cell_margins(c_left, top=0, bottom=20, left=0, right=60)
                p_l = c_left.paragraphs[0]
                p_l.paragraph_format.space_before = Pt(0)
                p_l.paragraph_format.space_after = Pt(1)
                _format_skill_line(p_l, left_txt, font_name, body_pt)

                c_right = tbl.cell(r_idx, 1)
                c_right.width = Inches(3.5)
                set_cell_margins(c_right, top=0, bottom=20, left=60, right=0)
                p_r = c_right.paragraphs[0]
                p_r.paragraph_format.space_before = Pt(0)
                p_r.paragraph_format.space_after = Pt(1)
                if right_txt:
                    _format_skill_line(p_r, right_txt, font_name, body_pt)
        else:
            if raw_lines:
                for line_idx, s_line in enumerate(raw_lines):
                    if not s_line.strip():
                        continue
                    s_para = doc.add_paragraph()
                    s_para.paragraph_format.space_before = Pt(0)
                    s_para.paragraph_format.space_after = Pt((4 if line_idx == len(raw_lines) - 1 else 1.5) * space_factor)
                    _format_skill_line(s_para, s_line, font_name, body_pt)
            else:
                skills_para = doc.add_paragraph()
                skills_para.paragraph_format.space_before = Pt(0)
                skills_para.paragraph_format.space_after = Pt(4 * space_factor)
                skills_run = skills_para.add_run(", ".join(skills))
                skills_run.font.size = Pt(body_pt)
                skills_run.font.name = font_name

    section_renderers = {
        "education": render_education,
        "experience": render_experience,
        "projects": render_projects,
        "leadership": render_leadership,
        "skills": render_skills,
    }

    for sec_key in tmpl["order"]:
        if sec_key in section_renderers:
            section_renderers[sec_key]()

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def build_pdf_resume(
    parsed_resume: Dict[str, Any],
    applied_rewrites: Optional[List[Dict[str, Any]]] = None,
    template_id: str = "original"
) -> bytes:
    """Generates an ATS-compliant PDF document according to chosen template."""
    tmpl = CURATED_TEMPLATES.get(template_id, CURATED_TEMPLATES["original"])
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    font_main = tmpl["font_pdf"]
    font_bold = tmpl["font_pdf_bold"]
    accent_color = colors.HexColor(tmpl["accent_hex"])
    align_code = 1 if tmpl["align"] == "center" else 0

    is_dense = estimate_content_density(parsed_resume)
    is_tech = template_id == "tech_minimalist"
    is_ivy = template_id == "ivy_league"
    is_corp = template_id == "modern_corporate"

    font_adj = 1.0 if is_dense else 0.0

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=16 - font_adj,
        leading=20 - font_adj,
        alignment=align_code,
        textColor=colors.HexColor('#0F172A')
    )

    contact_style = ParagraphStyle(
        'DocContact',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5 - font_adj,
        leading=12 - font_adj,
        alignment=align_code,
        textColor=colors.HexColor('#64748B')
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=10 - font_adj,
        leading=13 - font_adj,
        textColor=accent_color,
        spaceBefore=5 if is_tech else 7,
        spaceAfter=1
    )

    item_title_style = ParagraphStyle(
        'ItemTitle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=9.5 - font_adj,
        leading=12.5 - font_adj,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=2
    )

    sub_title_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5 - font_adj,
        leading=11.5 - font_adj,
        textColor=colors.HexColor('#475569')
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5 - font_adj,
        leading=11.5 - font_adj,
        leftIndent=12,
        firstLineIndent=-8,
        textColor=colors.HexColor('#334155'),
        spaceAfter=1.0 if is_tech else 1.5
    )

    story = []

    # 1. Name & Contact
    contact = parsed_resume.get("contact", {})
    name = contact.get("name") or parsed_resume.get("candidate_name") or "CANDIDATE NAME"
    story.append(Paragraph(name.upper(), title_style))
    story.append(Spacer(1, 2))

    # ivy_league: thin rule under candidate name
    if is_ivy:
        story.append(HRFlowable(width="100%", thickness=0.8, color=accent_color, spaceAfter=3))

    contact_parts = []
    if contact.get("phone"):
        contact_parts.append(f"Mobile: {contact['phone']}")
    if contact.get("email"):
        contact_parts.append(f"Email: {contact['email']}")
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])
    if contact.get("location"):
        contact_parts.append(contact["location"])

    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact_style))
        story.append(Spacer(1, 3))

    if not is_ivy:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=4))

    def render_education():
        education = parsed_resume.get("education", [])
        if not education:
            return
        story.append(Paragraph("EDUCATION", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=accent_color, spaceAfter=2))
        for edu in education:
            inst = edu.get("institution") or ""
            degree = edu.get("degree") or ""
            yr = edu.get("year") or ""
            if inst:
                line = f"<b>{inst}</b>" + (f" <font color='#64748B'>| {yr}</font>" if yr else "")
                story.append(Paragraph(line, item_title_style))
            if degree:
                story.append(Paragraph(degree, sub_title_style))
        story.append(Spacer(1, 2 if is_tech else 3))

    def render_experience():
        raw_exp = parsed_resume.get("experience", [])
        if not raw_exp:
            return
        story.append(Paragraph("EXPERIENCE", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=accent_color, spaceAfter=2))
        updated_exp = apply_bullet_rewrites(raw_exp, applied_rewrites or [])

        for exp in updated_exp:
            role = exp.get("role") or ""
            company = exp.get("company") or ""
            dur = exp.get("duration") or ""
            header_text = role + (f" | {company}" if company else "")
            flowables = []
            if header_text:
                role_header = f"<b>{header_text}</b>" + (f" <font color='#64748B'>| {dur}</font>" if dur else "")
                flowables.append(Paragraph(role_header, item_title_style))

            for bullet in exp.get("bullets", []):
                clean_bullet = bullet.strip().lstrip("-•* ").strip()
                if clean_bullet:
                    flowables.append(Paragraph(f"<font color='{tmpl['accent_hex']}'>&bull;</font> {clean_bullet}", bullet_style))

            if is_corp:
                # 2-column table with thin colored left accent bar
                entry_table = Table([['', flowables]], colWidths=[4, 498])
                entry_table.setStyle([
                    ('BACKGROUND', (0,0), (0,0), accent_color),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (1,0), (1,0), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ])
                story.append(entry_table)
                story.append(Spacer(1, 2))
            else:
                for f in flowables:
                    story.append(f)
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 2 if is_tech else 3))

    def render_projects():
        raw_proj = parsed_resume.get("projects", [])
        if not raw_proj:
            return
        story.append(Paragraph("PROJECTS", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=accent_color, spaceAfter=2))
        updated_proj = apply_bullet_rewrites(raw_proj, applied_rewrites or [])

        for proj in updated_proj:
            title = proj.get("title") or "Project"
            org = proj.get("organization") or ""
            dur = proj.get("duration") or ""
            header_text = f"<b>{title}</b>" + (f" | {org}" if org else "") + (f" <font color='#64748B'>| {dur}</font>" if dur else "")
            flowables = [Paragraph(header_text, item_title_style)]

            for bullet in proj.get("bullets", []):
                clean_b = bullet.strip().lstrip("-•* ").strip()
                if clean_b:
                    flowables.append(Paragraph(f"<font color='{tmpl['accent_hex']}'>&bull;</font> {clean_b}", bullet_style))

            if is_corp:
                entry_table = Table([['', flowables]], colWidths=[4, 498])
                entry_table.setStyle([
                    ('BACKGROUND', (0,0), (0,0), accent_color),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (1,0), (1,0), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 1),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ])
                story.append(entry_table)
                story.append(Spacer(1, 2))
            else:
                for f in flowables:
                    story.append(f)
                story.append(Spacer(1, 2))

        story.append(Spacer(1, 2 if is_tech else 3))

    def render_leadership():
        raw_lead = parsed_resume.get("leadership", [])
        if not raw_lead:
            return
        story.append(Paragraph("LEADERSHIP & INVOLVEMENT", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=accent_color, spaceAfter=2))
        updated_lead = apply_bullet_rewrites(raw_lead, applied_rewrites or [])

        for lead in updated_lead:
            role = lead.get("role") or "Leadership"
            org = lead.get("organization") or ""
            header_text = f"<b>{role}</b>" + (f" | {org}" if org else "")
            story.append(Paragraph(header_text, item_title_style))

            for bullet in lead.get("bullets", []):
                clean_b = bullet.strip().lstrip("-•* ").strip()
                if clean_b:
                    story.append(Paragraph(f"<font color='{tmpl['accent_hex']}'>&bull;</font> {clean_b}", bullet_style))
            story.append(Spacer(1, 2))

        story.append(Spacer(1, 2 if is_tech else 3))

    def render_skills():
        raw_lines = parsed_resume.get("skills_raw_lines", [])
        skills = parsed_resume.get("skills", [])
        if not raw_lines and not skills:
            return
        story.append(Paragraph("TECHNICAL SKILLS" if is_tech else "SKILLS & INTERESTS", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=accent_color, spaceAfter=2))

        if is_tech:
            # Compact 2-column skills table
            items = []
            if raw_lines:
                items = [line.strip() for line in raw_lines if line.strip()]
            else:
                half = (len(skills) + 1) // 2
                items = [", ".join(skills[:half]), ", ".join(skills[half:])]

            pairs = []
            for i in range(0, len(items), 2):
                l_item = items[i]
                r_item = items[i + 1] if (i + 1) < len(items) else ""
                pairs.append((l_item, r_item))

            table_data = []
            for left_txt, right_txt in pairs:
                p_l = Paragraph(
                    f"<b>{left_txt.split(':', 1)[0]}:</b> {left_txt.split(':', 1)[1].strip()}" if ":" in left_txt else left_txt,
                    bullet_style
                )
                p_r = Paragraph(
                    f"<b>{right_txt.split(':', 1)[0]}:</b> {right_txt.split(':', 1)[1].strip()}" if ":" in right_txt else right_txt,
                    bullet_style
                ) if right_txt else Paragraph("", bullet_style)
                table_data.append([p_l, p_r])

            s_table = Table(table_data, colWidths=[250, 254])
            s_table.setStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ])
            story.append(s_table)
        else:
            if raw_lines:
                for line in raw_lines:
                    if not line.strip():
                        continue
                    if ":" in line:
                        cat, val = line.split(":", 1)
                        story.append(Paragraph(f"<b>{cat}:</b> {val.strip()}", bullet_style))
                    else:
                        story.append(Paragraph(line, bullet_style))
            else:
                story.append(Paragraph(", ".join(skills), bullet_style))
        story.append(Spacer(1, 3))

    section_renderers = {
        "education": render_education,
        "experience": render_experience,
        "projects": render_projects,
        "leadership": render_leadership,
        "skills": render_skills,
    }

    for sec_key in tmpl["order"]:
        if sec_key in section_renderers:
            section_renderers[sec_key]()

    doc.build(story)
    return buffer.getvalue()


"""
backend/services/resume_builder.py
Generates ATS-compliant .docx and .pdf resumes with accepted Google XYZ bullet rewrites applied.
Supports 3 curated university student template layouts:
1. 'ivy_league' (Harvard/Wharton format: centered header, academic order, classic serif/clean styling)
2. 'tech_minimalist' (Stanford/CMU CS format: skills-first, left-aligned, high information density)
3. 'modern_corporate' (Consulting / Business Analyst format: sky-blue accent headings, executive hierarchy)
"""

import io
from typing import Dict, Any, List, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable


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


def apply_rewrites_to_custom_docx(
    custom_docx_bytes: bytes,
    applied_rewrites: List[Dict[str, Any]]
) -> bytes:
    """Takes an uploaded custom .docx file and applies Google XYZ bullet rewrites in place."""
    doc = Document(io.BytesIO(custom_docx_bytes))

    replacements = []
    for rw in applied_rewrites:
        orig = (rw.get("original_bullet") or "").strip()
        new_b = (rw.get("rewrite_bullet") or "").strip()
        if orig and new_b:
            replacements.append((orig, new_b))

    def replace_in_paragraphs(paragraphs):
        for p in paragraphs:
            text = p.text
            if not text.strip():
                continue
            for orig, new_b in replacements:
                clean_orig = orig.lstrip("-•* ").strip()
                if clean_orig and clean_orig.lower() in text.lower():
                    idx = text.lower().find(clean_orig.lower())
                    if idx != -1:
                        target_substring = text[idx:idx + len(clean_orig)]
                        p.text = text.replace(target_substring, new_b)
                        text = p.text
                elif orig and orig.lower() in text.lower():
                    idx = text.lower().find(orig.lower())
                    if idx != -1:
                        target_substring = text[idx:idx + len(orig)]
                        p.text = text.replace(target_substring, new_b)
                        text = p.text

    replace_in_paragraphs(doc.paragraphs)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                replace_in_paragraphs(cell.paragraphs)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


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

    # 2. Header: Name & Contact
    name_para = doc.add_paragraph()
    if is_center:
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_name = name_para.add_run(name.upper())
    run_name.bold = True
    run_name.font.size = Pt(17)
    run_name.font.name = font_name
    run_name.font.color.rgb = RGBColor(15, 23, 42)

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
        run_contact = contact_para.add_run(" | ".join(contact_parts))
        run_contact.font.size = Pt(9.5)
        run_contact.font.name = font_name
        run_contact.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph()  # Spacing

    def add_section_header(title: str):
        h_para = doc.add_paragraph()
        h_run = h_para.add_run(title.upper())
        h_run.bold = True
        h_run.font.size = Pt(11.5)
        h_run.font.name = font_name
        h_run.font.color.rgb = accent_rgb

    def render_education():
        education = parsed_resume.get("education", [])
        if not education:
            return
        add_section_header("Education")
        for edu in education:
            inst = edu.get("institution") or ""
            degree = edu.get("degree") or ""
            year = edu.get("year") or ""

            edu_para = doc.add_paragraph()
            if inst:
                run_inst = edu_para.add_run(inst)
                run_inst.bold = True
                run_inst.font.size = Pt(10.5)
                run_inst.font.name = font_name
            if year:
                run_yr = edu_para.add_run(f" | {year}")
                run_yr.font.size = Pt(9.5)
                run_yr.font.color.rgb = RGBColor(100, 116, 139)

            if degree:
                deg_para = doc.add_paragraph()
                run_deg = deg_para.add_run(degree)
                run_deg.font.size = Pt(9.5)
                run_deg.font.name = font_name
        doc.add_paragraph()

    def render_experience():
        raw_exp = parsed_resume.get("experience", [])
        if not raw_exp:
            return
        add_section_header("Experience")
        updated_exp = apply_bullet_rewrites(raw_exp, applied_rewrites or [])

        for exp in updated_exp:
            role = exp.get("role") or ""
            company = exp.get("company") or ""
            dur = exp.get("duration") or ""

            role_para = doc.add_paragraph()
            header_text = role + (f" | {company}" if company else "")
            if not header_text:
                header_text = "Position"
            run_role = role_para.add_run(header_text)
            run_role.bold = True
            run_role.font.size = Pt(10.5)
            run_role.font.name = font_name

            if dur:
                run_dur = role_para.add_run(f" | {dur}")
                run_dur.font.size = Pt(9.5)
                run_dur.font.color.rgb = RGBColor(100, 116, 139)

            for bullet in exp.get("bullets", []):
                clean_bullet = bullet.strip().lstrip("-•* ").strip()
                if clean_bullet:
                    b_para = doc.add_paragraph(style="List Bullet")
                    b_run = b_para.add_run(clean_bullet)
                    b_run.font.size = Pt(9.5)
                    b_run.font.name = font_name
        doc.add_paragraph()

    def render_projects():
        raw_proj = parsed_resume.get("projects", [])
        if not raw_proj:
            return
        add_section_header("Projects")
        updated_proj = apply_bullet_rewrites(raw_proj, applied_rewrites or [])

        for proj in updated_proj:
            title = proj.get("title") or "Project"
            org = proj.get("organization") or ""
            dur = proj.get("duration") or ""

            p_para = doc.add_paragraph()
            header_text = title + (f" | {org}" if org else "")
            run_p = p_para.add_run(header_text)
            run_p.bold = True
            run_p.font.size = Pt(10.5)
            run_p.font.name = font_name

            if dur:
                run_dur = p_para.add_run(f" | {dur}")
                run_dur.font.size = Pt(9.5)
                run_dur.font.color.rgb = RGBColor(100, 116, 139)

            for bullet in proj.get("bullets", []):
                clean_b = bullet.strip().lstrip("-•* ").strip()
                if clean_b:
                    b_para = doc.add_paragraph(style="List Bullet")
                    b_run = b_para.add_run(clean_b)
                    b_run.font.size = Pt(9.5)
                    b_run.font.name = font_name
        doc.add_paragraph()

    def render_leadership():
        raw_lead = parsed_resume.get("leadership", [])
        if not raw_lead:
            return
        add_section_header("Leadership & Involvement")
        updated_lead = apply_bullet_rewrites(raw_lead, applied_rewrites or [])

        for lead in updated_lead:
            role = lead.get("role") or "Leadership"
            org = lead.get("organization") or ""

            l_para = doc.add_paragraph()
            header_text = role + (f" | {org}" if org else "")
            run_l = l_para.add_run(header_text)
            run_l.bold = True
            run_l.font.size = Pt(10.5)
            run_l.font.name = font_name

            for bullet in lead.get("bullets", []):
                clean_b = bullet.strip().lstrip("-•* ").strip()
                if clean_b:
                    b_para = doc.add_paragraph(style="List Bullet")
                    b_run = b_para.add_run(clean_b)
                    b_run.font.size = Pt(9.5)
                    b_run.font.name = font_name
        doc.add_paragraph()

    def render_skills():
        raw_lines = parsed_resume.get("skills_raw_lines", [])
        skills = parsed_resume.get("skills", [])
        if not raw_lines and not skills:
            return
        add_section_header("Skills & Interests")
        if raw_lines:
            for s_line in raw_lines:
                if not s_line.strip():
                    continue
                s_para = doc.add_paragraph()
                if ":" in s_line:
                    cat, val = s_line.split(":", 1)
                    r_cat = s_para.add_run(cat + ": ")
                    r_cat.bold = True
                    r_cat.font.size = Pt(9.5)
                    r_cat.font.name = font_name
                    r_val = s_para.add_run(val.strip())
                    r_val.font.size = Pt(9.5)
                    r_val.font.name = font_name
                else:
                    r = s_para.add_run(s_line)
                    r.font.size = Pt(9.5)
                    r.font.name = font_name
        else:
            skills_para = doc.add_paragraph()
            skills_run = skills_para.add_run(", ".join(skills))
            skills_run.font.size = Pt(9.5)
            skills_run.font.name = font_name
        doc.add_paragraph()

    section_renderers = {
        "education": render_education,
        "experience": render_experience,
        "projects": render_projects,
        "leadership": render_leadership,
        "skills": render_skills,
    }

    # Render in template-specific section hierarchy
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

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=16,
        leading=20,
        alignment=align_code,
        textColor=colors.HexColor('#0F172A')
    )

    contact_style = ParagraphStyle(
        'DocContact',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5,
        leading=12,
        alignment=align_code,
        textColor=colors.HexColor('#64748B')
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=10,
        leading=13,
        textColor=accent_color,
        spaceBefore=6,
        spaceAfter=2
    )

    item_title_style = ParagraphStyle(
        'ItemTitle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=2
    )

    sub_title_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#475569')
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5,
        leading=11.5,
        leftIndent=12,
        firstLineIndent=-8,
        textColor=colors.HexColor('#334155'),
        spaceAfter=1.5
    )

    story = []

    # 1. Name & Contact
    contact = parsed_resume.get("contact", {})
    name = contact.get("name") or parsed_resume.get("candidate_name") or "CANDIDATE NAME"
    story.append(Paragraph(name.upper(), title_style))
    story.append(Spacer(1, 3))

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
        story.append(Spacer(1, 4))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=5))

    def render_education():
        education = parsed_resume.get("education", [])
        if not education:
            return
        story.append(Paragraph("EDUCATION", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor('#E2E8F0'), spaceAfter=3))
        for edu in education:
            inst = edu.get("institution") or ""
            degree = edu.get("degree") or ""
            yr = edu.get("year") or ""
            if inst:
                line = f"<b>{inst}</b>" + (f" <font color='#64748B'>| {yr}</font>" if yr else "")
                story.append(Paragraph(line, item_title_style))
            if degree:
                story.append(Paragraph(degree, sub_title_style))
        story.append(Spacer(1, 4))

    def render_experience():
        raw_exp = parsed_resume.get("experience", [])
        if not raw_exp:
            return
        story.append(Paragraph("EXPERIENCE", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor('#E2E8F0'), spaceAfter=3))
        updated_exp = apply_bullet_rewrites(raw_exp, applied_rewrites or [])

        for exp in updated_exp:
            role = exp.get("role") or ""
            company = exp.get("company") or ""
            dur = exp.get("duration") or ""
            header_text = role + (f" | {company}" if company else "")
            if header_text:
                role_header = f"<b>{header_text}</b>" + (f" <font color='#64748B'>| {dur}</font>" if dur else "")
                story.append(Paragraph(role_header, item_title_style))

            for bullet in exp.get("bullets", []):
                clean_bullet = bullet.strip().lstrip("-•* ").strip()
                if clean_bullet:
                    story.append(Paragraph(f"&bull; {clean_bullet}", bullet_style))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 3))

    def render_projects():
        raw_proj = parsed_resume.get("projects", [])
        if not raw_proj:
            return
        story.append(Paragraph("PROJECTS", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor('#E2E8F0'), spaceAfter=3))
        updated_proj = apply_bullet_rewrites(raw_proj, applied_rewrites or [])

        for proj in updated_proj:
            title = proj.get("title") or "Project"
            org = proj.get("organization") or ""
            dur = proj.get("duration") or ""
            header_text = f"<b>{title}</b>" + (f" | {org}" if org else "") + (f" <font color='#64748B'>| {dur}</font>" if dur else "")
            story.append(Paragraph(header_text, item_title_style))

            for bullet in proj.get("bullets", []):
                clean_b = bullet.strip().lstrip("-•* ").strip()
                if clean_b:
                    story.append(Paragraph(f"&bull; {clean_b}", bullet_style))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 3))

    def render_leadership():
        raw_lead = parsed_resume.get("leadership", [])
        if not raw_lead:
            return
        story.append(Paragraph("LEADERSHIP & INVOLVEMENT", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor('#E2E8F0'), spaceAfter=3))
        updated_lead = apply_bullet_rewrites(raw_lead, applied_rewrites or [])

        for lead in updated_lead:
            role = lead.get("role") or "Leadership"
            org = lead.get("organization") or ""
            header_text = f"<b>{role}</b>" + (f" | {org}" if org else "")
            story.append(Paragraph(header_text, item_title_style))

            for bullet in lead.get("bullets", []):
                clean_b = bullet.strip().lstrip("-•* ").strip()
                if clean_b:
                    story.append(Paragraph(f"&bull; {clean_b}", bullet_style))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 3))

    def render_skills():
        raw_lines = parsed_resume.get("skills_raw_lines", [])
        skills = parsed_resume.get("skills", [])
        if not raw_lines and not skills:
            return
        story.append(Paragraph("SKILLS & INTERESTS", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor('#E2E8F0'), spaceAfter=3))
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
        story.append(Spacer(1, 4))

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

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
    "ivy_league": {
        "id": "ivy_league",
        "name": "Ivy League / Classic University",
        "subtitle": "Harvard & Wharton Standard",
        "desc": "Centered header, classic academic ordering (Education → Experience → Skills), elegant typography.",
        "font_docx": "Georgia",
        "font_pdf": "Times-Roman",
        "font_pdf_bold": "Times-Bold",
        "accent_hex": "#1E293B",
        "align": "center",
        "order": ["education", "experience", "skills"]
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
        "order": ["skills", "experience", "education"]
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
        "order": ["experience", "education", "skills"]
    }
}


def apply_bullet_rewrites(
    experience_list: List[Dict[str, Any]],
    applied_rewrites: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Substitutes matched original bullets with accepted rewrite_bullet in experience blocks."""
    rewrite_map = {}
    for rw in applied_rewrites:
        orig = (rw.get("original_bullet") or "").strip().lower()
        replacement = rw.get("rewrite_bullet")
        if orig and replacement:
            rewrite_map[orig] = replacement.strip()

    updated_experience = []
    for exp in experience_list:
        new_exp = dict(exp)
        original_bullets = exp.get("bullets", [])
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

        new_exp["bullets"] = new_bullets
        updated_experience.append(new_exp)

    return updated_experience


def build_docx_resume(
    parsed_resume: Dict[str, Any],
    applied_rewrites: Optional[List[Dict[str, Any]]] = None,
    template_id: str = "ivy_league"
) -> bytes:
    """Generates an ATS-compliant Word document (.docx) according to chosen template."""
    tmpl = CURATED_TEMPLATES.get(template_id, CURATED_TEMPLATES["ivy_league"])
    doc = Document()

    # 1. Standard ATS 0.75" Margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    contact = parsed_resume.get("contact", {})
    name = contact.get("name") or "CANDIDATE NAME"
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
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])

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
            edu_para = doc.add_paragraph()
            edu_title = edu.get("degree") or "Degree"
            inst = edu.get("institution") or "University"
            year = edu.get("year") or ""

            run_title = edu_para.add_run(f"{edu_title} — {inst}")
            run_title.bold = True
            run_title.font.size = Pt(10.5)
            run_title.font.name = font_name

            if year:
                run_yr = edu_para.add_run(f" ({year})")
                run_yr.font.size = Pt(10)
                run_yr.font.color.rgb = RGBColor(100, 116, 139)
        doc.add_paragraph()

    def render_skills():
        skills = parsed_resume.get("skills", [])
        if not skills:
            return
        add_section_header("Technical Skills")
        skills_para = doc.add_paragraph()
        skills_run = skills_para.add_run(", ".join(skills))
        skills_run.font.size = Pt(10)
        skills_run.font.name = font_name
        doc.add_paragraph()

    def render_experience():
        raw_exp = parsed_resume.get("experience", [])
        if not raw_exp:
            return
        add_section_header("Professional Experience")
        updated_exp = apply_bullet_rewrites(raw_exp, applied_rewrites or [])

        for exp in updated_exp:
            role = exp.get("role") or "Role"
            company = exp.get("company") or ""
            dur = exp.get("duration") or ""

            role_para = doc.add_paragraph()
            role_header_text = f"{role}" + (f", {company}" if company else "")
            run_role = role_para.add_run(role_header_text)
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

    section_renderers = {
        "education": render_education,
        "experience": render_experience,
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
    template_id: str = "ivy_league"
) -> bytes:
    """Generates an ATS-compliant PDF document according to chosen template."""
    tmpl = CURATED_TEMPLATES.get(template_id, CURATED_TEMPLATES["ivy_league"])
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
        fontSize=17,
        leading=21,
        alignment=align_code,
        textColor=colors.HexColor('#0F172A')
    )

    contact_style = ParagraphStyle(
        'DocContact',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=9,
        leading=13,
        alignment=align_code,
        textColor=colors.HexColor('#64748B')
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=10.5,
        leading=14,
        textColor=accent_color,
        spaceBefore=7,
        spaceAfter=3
    )

    role_style = ParagraphStyle(
        'RoleTitle',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=3
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName=font_main,
        fontSize=8.5,
        leading=12,
        leftIndent=14,
        firstLineIndent=-10,
        textColor=colors.HexColor('#334155'),
        spaceAfter=2
    )

    story = []

    # 1. Name & Contact
    contact = parsed_resume.get("contact", {})
    name = contact.get("name") or "CANDIDATE NAME"
    story.append(Paragraph(name.upper(), title_style))
    story.append(Spacer(1, 4))

    contact_parts = []
    if contact.get("email"):
        contact_parts.append(contact["email"])
    if contact.get("phone"):
        contact_parts.append(contact["phone"])
    if contact.get("linkedin"):
        contact_parts.append(contact["linkedin"])

    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact_style))
        story.append(Spacer(1, 6))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0'), spaceAfter=6))

    def render_education():
        education = parsed_resume.get("education", [])
        if not education:
            return
        story.append(Paragraph("EDUCATION", h2_style))
        for edu in education:
            title = edu.get("degree") or "Degree"
            inst = edu.get("institution") or "University"
            yr = edu.get("year") or ""
            line = f"<b>{title}</b> — {inst}" + (f" ({yr})" if yr else "")
            story.append(Paragraph(line, bullet_style))
        story.append(Spacer(1, 5))

    def render_skills():
        skills = parsed_resume.get("skills", [])
        if not skills:
            return
        story.append(Paragraph("TECHNICAL SKILLS", h2_style))
        story.append(Paragraph(", ".join(skills), bullet_style))
        story.append(Spacer(1, 5))

    def render_experience():
        raw_exp = parsed_resume.get("experience", [])
        if not raw_exp:
            return
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", h2_style))
        updated_exp = apply_bullet_rewrites(raw_exp, applied_rewrites or [])

        for exp in updated_exp:
            role = exp.get("role") or "Role"
            company = exp.get("company") or ""
            dur = exp.get("duration") or ""
            role_header = f"<b>{role}</b>" + (f", {company}" if company else "") + (f" <font color='#64748B'>| {dur}</font>" if dur else "")
            story.append(Paragraph(role_header, role_style))

            for bullet in exp.get("bullets", []):
                clean_bullet = bullet.strip().lstrip("-•* ").strip()
                if clean_bullet:
                    story.append(Paragraph(f"&bull; {clean_bullet}", bullet_style))
            story.append(Spacer(1, 3))

    section_renderers = {
        "education": render_education,
        "experience": render_experience,
        "skills": render_skills,
    }

    for sec_key in tmpl["order"]:
        if sec_key in section_renderers:
            section_renderers[sec_key]()

    doc.build(story)
    return buffer.getvalue()

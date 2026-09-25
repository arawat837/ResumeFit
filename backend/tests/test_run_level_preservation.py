import io
import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from docx import Document
from docx.shared import Pt, RGBColor

from main import app
from database import init_db, create_user, upgrade_user_to_pro, create_access_token

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    temp_dir = tempfile.TemporaryDirectory()
    test_db_path = os.path.join(temp_dir.name, "test_run_preservation.db")
    monkeypatch.setattr("config.DATABASE_URL", None)
    monkeypatch.setattr("database.DATABASE_URL", None)
    monkeypatch.setattr("config.DATABASE_PATH", test_db_path)
    monkeypatch.setattr("database.DATABASE_PATH", test_db_path)
    init_db(test_db_path)
    user = create_user("Alex Mercer", "alex@university.edu", "hashedpass", db_path=test_db_path)
    upgrade_user_to_pro(user["id"], "CAMPUS2026", db_path=test_db_path)
    token = create_access_token(user["id"], user["email"])
    yield {"token": token, "db_path": test_db_path}
    temp_dir.cleanup()


def create_mixed_formatting_docx() -> bytes:
    """
    Creates a Word document with intricate run-level styling:
    - Paragraph 0: Candidate Name (bold, 16pt, centered)
    - Paragraph 1: Contact line (italic)
    - Paragraph 2: Section Heading 'EXPERIENCE' (bold, 12pt)
    - Paragraph 3: Job Header with mixed runs (bold company, italic role, plain date with custom color)
    - Paragraph 4: Bullet with inline bold metric:
        Run 0: '• ' (plain)
        Run 1: 'Led market research across ' (plain)
        Run 2: '15 enterprise clients' (bold, red)
        Run 3: ' to identify growth bottlenecks.' (plain)
    - Paragraph 5: Unmodified bullet
    """
    doc = Document()

    p0 = doc.add_paragraph()
    r0 = p0.add_run("Alex Mercer")
    r0.bold = True
    r0.font.size = Pt(16)

    p1 = doc.add_paragraph()
    r1 = p1.add_run("alex@university.edu | (555) 019-2834 | New York, NY")
    r1.italic = True

    p2 = doc.add_paragraph()
    r2 = p2.add_run("EXPERIENCE")
    r2.bold = True
    r2.font.size = Pt(12)

    # Job Header: Mixed formatting
    p3 = doc.add_paragraph()
    r3_0 = p3.add_run("Acme Advisory Group")
    r3_0.bold = True
    r3_1 = p3.add_run(" - ")
    r3_2 = p3.add_run("Business Analyst Intern")
    r3_2.italic = True
    r3_3 = p3.add_run(" | ")
    r3_4 = p3.add_run("June 2024 - August 2024")
    r3_4.font.color.rgb = RGBColor(100, 116, 139)

    # Bullet with inline bold metric
    p4 = doc.add_paragraph()
    r4_0 = p4.add_run("• ")
    r4_1 = p4.add_run("Led market research across ")
    r4_2 = p4.add_run("15 enterprise clients")
    r4_2.bold = True
    r4_2.font.color.rgb = RGBColor(255, 0, 0)
    r4_3 = p4.add_run(" to identify growth bottlenecks.")

    # Unmodified bullet
    p5 = doc.add_paragraph()
    r5_0 = p5.add_run("• ")
    r5_1 = p5.add_run("Coordinated weekly sprint reviews with cross-functional leadership.")

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def test_run_level_preservation_and_exact_xml_diff(setup_test_db):
    """
    Requirement 5 Test:
    1. Scans a .docx containing paragraphs with mixed formatting.
    2. Applies a rewrite to one bullet.
    3. Exports with template_id == 'original'.
    4. Asserts:
       (a) The rewritten text is correct.
       (b) Every run's bold/italic/font/color outside the matched span is byte-identical to the original document.
       (c) Side-by-side XML diff of word/document.xml shows ONLY the targeted sentence changed.
    """
    token = setup_test_db["token"]
    orig_docx_bytes = create_mixed_formatting_docx()

    # 1. Scan resume and ensure raw bytes are persisted with a scan_id
    scan_res = client.post(
        "/api/scan",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("alex_mercer.docx", orig_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert "scan_id" in scan_data
    scan_id = scan_data["scan_id"]
    assert scan_id is not None
    assert scan_data.get("file_type") == "docx"

    orig_target = "Led market research across 15 enterprise clients to identify growth bottlenecks."
    new_target = "Spearheaded strategic market research across 15 Tier-1 enterprise accounts, uncovering key operational bottlenecks that unlocked $120K in quarterly revenue."

    # 2. Export with template_id == 'original' using persisted scan_id
    export_payload = {
        "format": "docx",
        "template_id": "original",
        "scan_id": scan_id,
        "parsed_resume": scan_data.get("parsed_resume", {}),
        "applied_rewrites": [
            {
                "original_bullet": orig_target,
                "rewrite_bullet": new_target,
                "role": "Business Analyst Intern"
            }
        ]
    }

    export_res = client.post(
        "/api/resume/export",
        json=export_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert export_res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in export_res.headers["content-type"]
    exported_docx_bytes = export_res.content

    # 3. Read exported document and verify visible text
    exported_doc = Document(io.BytesIO(exported_docx_bytes))
    all_text = "\n".join(p.text for p in exported_doc.paragraphs)
    assert new_target in all_text
    assert orig_target not in all_text

    # 4. Extract word/document.xml from original and exported files
    with zipfile.ZipFile(io.BytesIO(orig_docx_bytes)) as z_orig:
        orig_xml = z_orig.read("word/document.xml").decode("utf-8")

    with zipfile.ZipFile(io.BytesIO(exported_docx_bytes)) as z_edit:
        edit_xml = z_edit.read("word/document.xml").decode("utf-8")

    orig_root = ET.fromstring(orig_xml)
    edit_root = ET.fromstring(edit_xml)

    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    orig_body = orig_root.find(f"{ns}body")
    edit_body = edit_root.find(f"{ns}body")

    orig_ps = orig_body.findall(f"{ns}p")
    edit_ps = edit_body.findall(f"{ns}p")

    # Assert paragraph count is unchanged
    assert len(orig_ps) == len(edit_ps) == 6

    # (b) Assert every paragraph outside the rewritten bullet is BYTE-FOR-BYTE IDENTICAL in XML:
    # Paragraph 0: Candidate Name
    assert ET.tostring(orig_ps[0]) == ET.tostring(edit_ps[0]), "Paragraph 0 (Name) was modified!"
    # Paragraph 1: Contact
    assert ET.tostring(orig_ps[1]) == ET.tostring(edit_ps[1]), "Paragraph 1 (Contact) was modified!"
    # Paragraph 2: Heading
    assert ET.tostring(orig_ps[2]) == ET.tostring(edit_ps[2]), "Paragraph 2 (Section Heading) was modified!"
    # Paragraph 3: Job Header (bold company, italic role, colored date)
    assert ET.tostring(orig_ps[3]) == ET.tostring(edit_ps[3]), "Paragraph 3 (Job Header with mixed formatting) was modified!"
    # Paragraph 5: Unmodified second bullet
    assert ET.tostring(orig_ps[5]) == ET.tostring(edit_ps[5]), "Paragraph 5 (Second bullet) was modified!"

    # Now inspect Paragraph 4 (the targeted rewritten bullet):
    orig_runs = orig_ps[4].findall(f"{ns}r")
    edit_runs = edit_ps[4].findall(f"{ns}r")

    # Assert run count is preserved (no runs deleted or created)
    assert len(orig_runs) == len(edit_runs) == 4

    # Run 0 is the bullet symbol '• ' -> MUST BE BYTE-FOR-BYTE IDENTICAL!
    assert ET.tostring(orig_runs[0]) == ET.tostring(edit_runs[0]), "Run 0 (bullet glyph) was modified!"

    # Run 1 received the new rewritten text
    t_run1 = edit_runs[1].find(f"{ns}t")
    assert t_run1 is not None and t_run1.text == new_target

    # Runs 2 and 3 had their matched text cleared without destroying run tags/properties
    t_run2 = edit_runs[2].find(f"{ns}t")
    t_run3 = edit_runs[3].find(f"{ns}t")
    assert getattr(t_run2, "text", None) in (None, "")
    assert getattr(t_run3, "text", None) in (None, "")


def test_pdf_export_for_original_and_custom_templates_returns_clean_error_or_pdf(setup_test_db):
    """
    Requirement 4 Test:
    PDF export for template_id == 'original' or custom_template_base64 must NOT silently
    substitute a generic layout. If LibreOffice is absent, it must return a clear HTTP 400 error.
    """
    token = setup_test_db["token"]
    orig_docx_bytes = create_mixed_formatting_docx()

    scan_res = client.post(
        "/api/scan",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("alex_mercer.docx", orig_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    scan_id = scan_res.json()["scan_id"]

    res = client.post(
        "/api/resume/export",
        json={
            "format": "pdf",
            "template_id": "original",
            "scan_id": scan_id,
            "parsed_resume": {"contact": {"name": "Alex Mercer"}},
            "applied_rewrites": []
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    # In environments without LibreOffice, it returns HTTP 400 with descriptive error
    # If LibreOffice is installed, it returns HTTP 200 with PDF
    if res.status_code == 400:
        assert "PDF export is not supported for custom or original-format templates" in res.json()["detail"]
    else:
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"

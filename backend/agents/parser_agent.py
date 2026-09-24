import json
import logging
import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ResumeContact(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""

class ResumeExperienceItem(BaseModel):
    role: str = ""
    company: str = ""
    duration: str = ""
    bullets: List[str] = Field(default_factory=list)

class ResumeEducationItem(BaseModel):
    institution: str = ""
    degree: str = ""
    year: str = ""

class ResumeParsedData(BaseModel):
    contact: Dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    skills_raw_lines: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    leadership: List[Dict[str, Any]] = Field(default_factory=list)


class ParserAgent:
    """
    Parser Agent: Converts raw resume text into structured JSON schema:
    {contact, summary, skills[], skills_raw_lines[], experience[], education[], projects[], leadership[]}
    Uses native async Google GenAI client if available, with deterministic fallback.
    Returns: {"data": dict, "used_gemini": bool}
    """

    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    async def run(self, resume_text: str) -> Dict[str, Any]:
        clean_text = resume_text.strip()

        # 1. Native asynchronous call with google-genai
        if self.gemini_client:
            prompt = (
                "You are an expert resume parsing engine. Parse the following resume text into comprehensive structured JSON.\n"
                "CRITICAL REQUIREMENT: Do NOT omit any sections or bullets. Extract all experiences, projects, leadership, and education entries completely.\n"
                "Return ONLY valid JSON matching this schema:\n"
                "{\n"
                '  "contact": {"name": "", "email": "", "phone": "", "linkedin": "", "location": ""},\n'
                '  "summary": "",\n'
                '  "skills": ["skill1", "skill2"],\n'
                '  "skills_raw_lines": ["Tools: Excel, Power BI", "Core Skills: Negotiation"],\n'
                '  "education": [{"institution": "", "degree": "", "year": ""}],\n'
                '  "experience": [{"role": "", "company": "", "duration": "", "bullets": ["bullet1", "bullet2"]}],\n'
                '  "projects": [{"title": "", "organization": "", "duration": "", "bullets": ["bullet1"]}],\n'
                '  "leadership": [{"role": "", "organization": "", "bullets": ["bullet1"]}]\n'
                "}\n\n"
                f"Resume Text:\n{clean_text}"
            )
            from config import GEMINI_MODEL
            import asyncio

            for attempt in range(3):
                try:
                    response = await asyncio.wait_for(
                        self.gemini_client.aio.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=prompt,
                            config={"response_mime_type": "application/json"}
                        ),
                        timeout=12.0
                    )

                    raw_text = getattr(response, "text", "")
                    clean_json = raw_text.strip() if raw_text else ""
                    if clean_json.startswith("```"):
                        clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                        clean_json = re.sub(r"\s*```$", "", clean_json)

                    data = json.loads(clean_json)
                    validated = ResumeParsedData(**data).model_dump()
                    return {"data": validated, "used_gemini": True}
                except Exception as e:
                    if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < 2:
                        logger.info(f"Gemini Parser Agent received 503 high demand spike, retrying in {1.5 * (attempt + 1)}s...")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    logger.warning(f"Gemini Parser Agent failed (raw_response.text: {locals().get('raw_text')!r}): {e}")
                    break

        # 2. Deterministic rule-based fallback parser
        fallback_data = self._fallback_parse(clean_text)
        return {"data": fallback_data, "used_gemini": False}

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """
        Deterministic, rule-based resume parsing extracting all sections:
        Contact, Education (multi-tier), Experience, Projects, Leadership, and Skills.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return ResumeParsedData().model_dump()

        # 1. Contact Info Extraction
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b", text)
        linkedin_match = re.search(r"(?:linkedin\.com/in/[\w\-]+|linkedin\.com/[\w\-]+)", text, re.IGNORECASE)

        location = ""
        for line in lines[1:4]:
            if any(c in line for c in ["@", "http", "www", "Mobile:", "Phone:"]):
                continue
            if re.search(r"\b[A-Za-z\s]+,\s*[A-Za-z\s]+\b", line):
                location = line.strip()
                break

        name = lines[0]
        if len(name.split()) > 4 or any(c in name for c in ["@", "http", "www", "/"]):
            name = "Candidate"

        contact = {
            "name": name,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "linkedin": linkedin_match.group(0) if linkedin_match else "",
            "location": location
        }

        # 2. Section Partitioning
        section_patterns = {
            "education": re.compile(r"^(?:education|academic|qualifications)\b", re.IGNORECASE),
            "experience": re.compile(r"^(?:experience|work\s+history|employment|professional\s+experience)\b", re.IGNORECASE),
            "projects": re.compile(r"^(?:projects|academic\s+projects|key\s+projects)\b", re.IGNORECASE),
            "leadership": re.compile(r"^(?:leadership|involvement|extracurricular|activities|leadership\s*&\s*involvement)\b", re.IGNORECASE),
            "skills": re.compile(r"^(?:skills|technical\s+skills|core\s+skills|skills\s*&\s*interests|technologies)\b", re.IGNORECASE),
            "summary": re.compile(r"^(?:summary|profile|about\s+me|objective)\b", re.IGNORECASE)
        }

        sections = {k: [] for k in section_patterns}
        current_sec = "summary"

        for line in lines[1:]:
            matched = False
            for sec_name, pat in section_patterns.items():
                if pat.match(line):
                    current_sec = sec_name
                    matched = True
                    break
            if not matched:
                sections[current_sec].append(line)

        # Bullet recognition regex
        bullet_regex = re.compile(r"^[\s\t]*([•\*\-\–\—\·\u2022\u25cf\uf0b7\uf0a7\u25aa\u25e6\u25cb\u2043\u2219\u2713]|\(\w+\)|\d+[\.\)])\s*")

        def parse_item_blocks(block_lines: List[str]) -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            curr: Optional[Dict[str, Any]] = None
            for raw_line in block_lines:
                cleaned = re.sub(r"^\(cid:\d+\)\s*", "• ", raw_line).strip()
                is_bullet = bool(bullet_regex.match(cleaned))
                if is_bullet:
                    bullet_clean = bullet_regex.sub("", cleaned).strip()
                    if curr is None:
                        curr = {"title": "Experience", "subtitle": "", "duration": "", "bullets": []}
                    curr["bullets"].append(bullet_clean)
                else:
                    if curr and (curr["bullets"] or curr.get("title")):
                        items.append(curr)
                    # Extract date
                    dur_match = re.search(r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}\s*[-–—]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?[a-z]*\s*\d{4}|\b20\d\d\s*[-–—]\s*20\d\d|\b20\d\d\b)", raw_line, re.IGNORECASE)
                    dur_str = dur_match.group(0) if dur_match else ""
                    clean_title = raw_line.replace(dur_str, "").strip() if dur_str else raw_line
                    curr = {"title": clean_title, "subtitle": "", "duration": dur_str, "bullets": []}

            if curr and (curr["bullets"] or curr.get("title")):
                items.append(curr)
            return items

        # 3. Education Parsing
        education_items: List[Dict[str, Any]] = []
        edu_lines = sections["education"]
        i = 0
        while i < len(edu_lines):
            line = edu_lines[i]
            dur_match = re.search(r"(\b20\d\d\s*[-–—]\s*20\d\d|\b20\d\d\b)", line)
            duration = dur_match.group(0) if dur_match else ""
            clean_inst = line.replace(duration, "").strip()

            sub = ""
            if i + 1 < len(edu_lines) and not re.search(r"\b(School|College|University|Vidyapith|Institute)\b", edu_lines[i+1], re.IGNORECASE):
                sub = edu_lines[i+1]
                i += 1
                if not duration:
                    d2 = re.search(r"(\b20\d\d\s*[-–—]\s*20\d\d|\b20\d\d\b)", sub)
                    if d2:
                        duration = d2.group(0)
                        sub = sub.replace(duration, "").strip()

            education_items.append({
                "institution": clean_inst,
                "degree": sub or "Degree Program",
                "year": duration
            })
            i += 1

        # 4. Experience Parsing
        experience_items: List[Dict[str, Any]] = []
        for it in parse_item_blocks(sections["experience"]):
            experience_items.append({
                "role": it["title"],
                "company": it.get("subtitle", ""),
                "duration": it.get("duration", ""),
                "bullets": it["bullets"]
            })

        # 5. Projects Parsing
        project_items: List[Dict[str, Any]] = []
        for it in parse_item_blocks(sections["projects"]):
            project_items.append({
                "title": it["title"],
                "organization": it.get("subtitle", ""),
                "duration": it.get("duration", ""),
                "bullets": it["bullets"]
            })

        # 6. Leadership Parsing
        leadership_items: List[Dict[str, Any]] = []
        for it in parse_item_blocks(sections["leadership"]):
            leadership_items.append({
                "role": it["title"],
                "organization": it.get("subtitle", ""),
                "bullets": it["bullets"]
            })

        # 7. Skills Parsing
        skills_raw_lines = sections["skills"]
        skills_tokens = [s.strip(" •·-|*") for s in re.split(r"[,;|•\n]+", " ".join(skills_raw_lines)) if s.strip(" •·-|*")]
        skills = list(dict.fromkeys([s for s in skills_tokens if 1 < len(s) < 40]))

        summary_text = " ".join(sections["summary"][:4]).strip()

        return {
            "contact": contact,
            "summary": summary_text,
            "skills": skills,
            "skills_raw_lines": skills_raw_lines,
            "experience": experience_items,
            "education": education_items,
            "projects": project_items,
            "leadership": leadership_items
        }

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
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)


class ParserAgent:
    """
    Parser Agent: Converts raw resume text into structured JSON schema:
    {contact, summary, skills[], experience[], education[]}
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
                "You are an expert resume parsing engine. Parse the following resume text into structured JSON.\n"
                "Return ONLY valid JSON matching this schema:\n"
                "{\n"
                '  "contact": {"name": "", "email": "", "phone": "", "linkedin": ""},\n'
                '  "summary": "",\n'
                '  "skills": ["skill1", "skill2"],\n'
                '  "experience": [{"role": "", "company": "", "duration": "", "bullets": ["bullet1"]}],\n'
                '  "education": [{"institution": "", "degree": "", "year": ""}]\n'
                "}\n\n"
                f"Resume Text:\n{clean_text}"
            )
            from config import GEMINI_MODEL
            import asyncio

            for attempt in range(3):
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
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
        Deterministic, rule-based resume parsing using regular expressions and section boundary detection.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 1. Contact Info Extraction
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        linkedin_match = re.search(r"(?:linkedin\.com/in/[\w\-]+|linkedin\.com/[\w\-]+)", text, re.IGNORECASE)

        name = lines[0] if lines else "Candidate"
        if len(name.split()) > 4 or any(c in name for c in ["@", "http", "www", "/"]):
            name = "Candidate"

        contact = {
            "name": name,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "linkedin": linkedin_match.group(0) if linkedin_match else "",
        }

        # 2. Section Partitioning
        sections = {
            "summary": [],
            "skills": [],
            "experience": [],
            "education": []
        }

        current_section = "summary"
        section_headers = {
            "experience": re.compile(r"^(?:experience|work\s+history|employment|professional\s+experience|projects)\b", re.IGNORECASE),
            "education": re.compile(r"^(?:education|academic\s+background|qualifications)\b", re.IGNORECASE),
            "skills": re.compile(r"^(?:technical\s+skills|skills|core\s+competencies|technologies)\b", re.IGNORECASE),
            "summary": re.compile(r"^(?:summary|profile|about\s+me|objective)\b", re.IGNORECASE),
        }

        for line in lines[1:]:  # skip first line as name
            matched_new_section = False
            for sec_name, pattern in section_headers.items():
                if pattern.match(line):
                    current_section = sec_name
                    matched_new_section = True
                    break
            if not matched_new_section:
                sections[current_section].append(line)

        # 3. Skills parsing
        skills_raw = " ".join(sections["skills"])
        # Split on commas, bullets, pipes, or semicolons
        skills_tokens = [s.strip(" •·-|*") for s in re.split(r"[,;|•\n]+", skills_raw) if s.strip(" •·-|*")]
        # Deduplicate while preserving order
        skills = list(dict.fromkeys([s for s in skills_tokens if len(s) > 1 and len(s) < 35]))

        # 4. Experience parsing
        experience_items: List[Dict[str, Any]] = []
        current_exp = None

        for line in sections["experience"]:
            cleaned_line = re.sub(r"^\(cid:\d+\)\s*", "• ", line).strip()
            is_bullet = (
                cleaned_line.startswith(("-", "*", "•", "–", "—", "·", "\u2022", "\u25cf", "\uf0b7"))
                or bool(re.match(r"^\d+\.", cleaned_line))
            )
            if is_bullet:
                bullet_clean = re.sub(r"^([-*•–—·\u2022\u25cf\uf0b7]|\d+\.)+\s*", "", cleaned_line).strip()
                if current_exp:
                    current_exp["bullets"].append(bullet_clean)
                else:
                    current_exp = {"role": "Experience", "company": "", "duration": "", "bullets": [bullet_clean]}
            else:
                if current_exp and current_exp["bullets"]:
                    experience_items.append(current_exp)
                current_exp = {"role": line, "company": "", "duration": "", "bullets": []}

        if current_exp and (current_exp["bullets"] or current_exp["role"]):
            experience_items.append(current_exp)

        # 5. Education parsing
        education_items: List[Dict[str, Any]] = []
        edu_lines = sections["education"]
        if edu_lines:
            degree = ""
            institution = edu_lines[0]
            year = ""
            for line in edu_lines:
                if re.search(r"\b(bachelor|master|b\.s|m\.s|b\.a|bba|phd|degree)\b", line, re.IGNORECASE):
                    degree = line
                year_match = re.search(r"\b(20\d\d|19\d\d)\b", line)
                if year_match:
                    year = year_match.group(0)

            education_items.append({
                "institution": institution,
                "degree": degree or "Degree Program",
                "year": year
            })

        summary_text = " ".join(sections["summary"][:4]).strip()

        return {
            "contact": contact,
            "summary": summary_text,
            "skills": skills,
            "experience": experience_items,
            "education": education_items,
        }

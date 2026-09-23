import json
import logging
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class JDParsedResult(BaseModel):
    required_skills: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    seniority: str = "Entry-Level"

# Standard technical & business skill vocab for fallback parser
COMMON_KEYWORDS_CATALOG = [
    "python", "sql", "excel", "powerbi", "tableau", "r", "machine learning",
    "data analysis", "statistics", "etl", "pandas", "numpy", "git",
    "financial modeling", "powerpoint", "problem solving", "stakeholder management",
    "strategy", "market research", "benchmarking", "communication",
    "seo", "sem", "google analytics", "content strategy", "social media", "copywriting",
    "a/b testing", "email marketing", "hubspot", "campaigns",
    "talent acquisition", "onboarding", "hris", "workday", "bamboohr",
    "employee relations", "compliance", "interviewing", "recruitment"
]

class JDAgent:
    """
    JD Agent: Extracts required skills, keywords, and seniority from job description.
    Conditionality: Only invoked when a JD is actually provided.
    Skipped completely in General ATS mode with zero latency/cost (returns None).
    Reports {"data": ..., "used_gemini": bool} when run.
    """

    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    async def run(self, jd_text: Optional[str]) -> Optional[Dict[str, Any]]:
        # Immediate skip if no JD is provided
        if not jd_text or not jd_text.strip():
            logger.info("General ATS mode: Skipping JD Agent entirely.")
            return None

        clean_jd = jd_text.strip()

        # 1. Native asynchronous call with google-genai
        if self.gemini_client:
            prompt = (
                "You are an expert ATS recruiter. Analyze the following Job Description and extract:\n"
                "1. required_skills: list of essential hard and technical skills\n"
                "2. keywords: key domain terminology, frameworks, certifications\n"
                "3. seniority: target experience level (e.g., Internship, Entry-Level, Associate)\n\n"
                "Return ONLY valid JSON matching this schema:\n"
                "{\n"
                '  "required_skills": ["skill1", "skill2"],\n'
                '  "keywords": ["keyword1", "keyword2"],\n'
                '  "seniority": "Entry-Level"\n'
                "}\n\n"
                f"Job Description:\n{clean_jd}"
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
                    validated = JDParsedResult(**data).model_dump()
                    return {"data": validated, "used_gemini": True}
                except Exception as e:
                    if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < 2:
                        logger.info(f"Gemini JD Agent received 503 high demand spike, retrying in {1.5 * (attempt + 1)}s...")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    logger.warning(f"Gemini JD agent failed (raw_response.text: {locals().get('raw_text')!r}): {e}")
                    break

        # 2. Deterministic rule-based fallback parser
        fallback_data = self._fallback_parse(clean_jd)
        return {"data": fallback_data, "used_gemini": False}

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Extracts skills and keywords via heuristic keyword dictionary."""
        lower_text = text.lower()
        found_skills = []
        found_keywords = []

        for kw in COMMON_KEYWORDS_CATALOG:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower_text):
                if len(found_skills) < 8:
                    found_skills.append(kw.title())
                else:
                    found_keywords.append(kw)

        # Seniority heuristic
        seniority = "Entry-Level"
        if re.search(r"\b(intern|internship|co-op)\b", lower_text):
            seniority = "Internship"
        elif re.search(r"\b(senior|lead|manager|principal)\b", lower_text):
            seniority = "Senior"
        elif re.search(r"\b(mid|associate|experienced)\b", lower_text):
            seniority = "Associate"

        return {
            "required_skills": found_skills or ["Problem Solving", "Communication", "Analytical Skills"],
            "keywords": found_keywords or ["collaboration", "deliverables", "strategy"],
            "seniority": seniority
        }

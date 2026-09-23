"""
backend/agents/recommendation_agent.py
Recommendation Agent: Produces ranked, actionable resume fixes.
Calls Gemini asynchronously when available, with a deterministic rubric-gap fallback.
Returns {"data": recommendations, "used_gemini": bool}.
"""

from typing import Dict, Any, List, Optional
import json
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RecommendationItem(BaseModel):
    priority: int
    issue: str
    suggestion: str


class RecommendationAgent:
    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    async def run(
        self,
        scoring_result: Dict[str, Any],
        parsed_resume: Dict[str, Any],
        parsed_jd: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates ranked, high-impact suggestions.
        Returns:
            {"data": list[dict], "used_gemini": bool}
        """
        # 1. Attempt Gemini async call if client is available
        if self.gemini_client:
            diagnostics = scoring_result.get("diagnostics", {})
            breakdown = scoring_result.get("breakdown", {})
            ats_score = scoring_result.get("ats_score", 0)

            prompt = (
                "You are an elite career coach and ATS optimization specialist for university students.\n"
                "Analyze the resume data, job description (if any), and rubric diagnostics below.\n"
                "Generate 5 to 7 specific, highly actionable recommendations ranked by impact priority (1 is highest priority).\n"
                "Format rules:\n"
                "- Provide concrete rewrite examples with real numbers, action verbs, and keywords.\n"
                "- Return ONLY valid JSON matching this schema:\n"
                "[\n"
                '  {"priority": 1, "issue": "Short descriptive title of the problem", "suggestion": "Clear, actionable advice with a specific before/after or rewrite example"}\n'
                "]\n\n"
                f"Overall ATS Score: {ats_score}/100\n"
                f"Category Breakdown: {json.dumps(breakdown)}\n"
                f"Diagnostics: {json.dumps(diagnostics)}\n"
                f"Resume Summary & Sample Bullets: {json.dumps(parsed_resume.get('experience', [])[:3])}\n"
                f"Target JD Criteria: {json.dumps(parsed_jd) if parsed_jd else 'General ATS Assessment (no specific JD)'}"
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

                    raw_data = json.loads(clean_json)
                    if isinstance(raw_data, list):
                        validated = [RecommendationItem(**item).model_dump() for item in raw_data if isinstance(item, dict)]

                        # Contract check: must have at least 5 recommendations to satisfy UI contract (top 3 free + at least 2 locked Pro items)
                        if len(validated) < 5:
                            logger.warning(
                                f"Gemini returned only {len(validated)} recommendation(s) (minimum 5 required). "
                                f"(raw_response.text: {raw_text!r}) Falling through to deterministic fallback."
                            )
                            break
                        else:
                            validated.sort(key=lambda x: x["priority"])
                            return {"data": validated, "used_gemini": True}
                except Exception as e:
                    if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < 2:
                        logger.info(f"Gemini Recommendation Agent received 503 high demand spike, retrying in {1.5 * (attempt + 1)}s...")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    logger.warning(f"Gemini Recommendation Agent failed (raw_response.text: {locals().get('raw_text')!r}): {e}")
                    break

        # 2. Deterministic Rubric-Driven Fallback (guarantees >= 5 items)
        fallback_recs = self._fallback_recommendations(scoring_result, parsed_resume, parsed_jd)
        return {"data": fallback_recs, "used_gemini": False}

    def _fallback_recommendations(
        self,
        scoring_result: Dict[str, Any],
        parsed_resume: Dict[str, Any],
        parsed_jd: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, rule-based recommendation generator.
        Generates 5-6 prioritized fixes derived directly from rubric gap diagnostics.
        """
        recs: List[Dict[str, Any]] = []
        diagnostics = scoring_result.get("diagnostics", {})
        breakdown = scoring_result.get("breakdown", {})

        kw_diag = diagnostics.get("keywords", {})
        fmt_diag = diagnostics.get("formatting", {})
        sec_diag = diagnostics.get("sections", {})
        ach_diag = diagnostics.get("achievements", {})

        priority = 1

        # Check 1: Quantified Achievements (< 70)
        if breakdown.get("achievements", 100) < 70 or ach_diag.get("metric_percentage", 100) < 50:
            recs.append({
                "priority": priority,
                "issue": "Insufficient Quantified Achievements",
                "suggestion": (
                    f"Only {ach_diag.get('metric_bullets', 0)} of your {ach_diag.get('total_bullets', 0)} bullet points contain numbers or metrics. "
                    "Use the Google 'XYZ formula' (Accomplished [X] as measured by [Y] by doing [Z]). "
                    "For example: 'Automated weekly reporting using Python, reducing processing time by 35% and saving 4 hours per cycle.'"
                )
            })
            priority += 1

        # Check 2: Missing Keywords from JD or General benchmarks
        missing_kw = kw_diag.get("missing", [])
        if missing_kw:
            top_missing = ", ".join(missing_kw[:4])
            recs.append({
                "priority": priority,
                "issue": f"Missing Core Keywords: {top_missing}",
                "suggestion": (
                    f"Your resume lacks these critical terms found in target postings: {top_missing}. "
                    "Integrate them naturally into your Skills section and under project bullets where you used these tools or methodologies."
                )
            })
            priority += 1

        # Check 3: Formatting Red Flags
        fmt_issues = fmt_diag.get("issues", [])
        if fmt_issues:
            recs.append({
                "priority": priority,
                "issue": "ATS Formatting Hazards Detected",
                "suggestion": (
                    f"{' '.join(fmt_issues)} Convert all content into a single-column layout without tables or decorative images. "
                    "Use standard bullet characters and plain left-aligned headers."
                )
            })
            priority += 1

        # Check 4: Missing Standard Sections
        missing_secs = sec_diag.get("missing", [])
        if missing_secs:
            recs.append({
                "priority": priority,
                "issue": f"Missing Core Section: {', '.join(missing_secs)}",
                "suggestion": (
                    f"ATS algorithms expect standard headings: {', '.join(missing_secs)}. "
                    "Add these dedicated sections using clear, unstyled H2-level titles (e.g. 'Education', 'Technical Skills', 'Experience')."
                )
            })
            priority += 1

        # Check 5: Action Verb Usage
        if ach_diag.get("verb_percentage", 100) < 65:
            recs.append({
                "priority": priority,
                "issue": "Passive or Repetitive Bullet Openings",
                "suggestion": (
                    "Replace passive phrases like 'Responsible for' or 'Helped with' with active, decisive verbs. "
                    "Start bullets with power verbs such as 'Spearheaded', 'Engineered', 'Optimized', or 'Coordinated'."
                )
            })
            priority += 1

        # Check 6: Contact & Professional Links
        contact = parsed_resume.get("contact", {})
        if not contact.get("linkedin"):
            recs.append({
                "priority": priority,
                "issue": "Missing LinkedIn Profile URL",
                "suggestion": (
                    "Include a clean, customized LinkedIn URL in your header (e.g., linkedin.com/in/yourname). "
                    "Modern ATS parsers match candidate profiles directly against verified LinkedIn accounts."
                )
            })
            priority += 1

        # Ensure at least 5 recommendations exist so top 3 are free and remaining fill the Pro gate
        supplemental_recommendations = [
            {
                "issue": "Add a Target-Specific Professional Summary",
                "suggestion": (
                    "Add a 2-3 line summary at the top of your resume tailored to the exact role. "
                    "Highlight your degree, top 3 technical proficiencies, and immediate value proposition."
                )
            },
            {
                "issue": "Highlight Relevant Coursework & Certifications",
                "suggestion": (
                    "Include 3-4 specialized upper-division courses or recognized professional certifications "
                    "(e.g., AWS, Coursera, Bloomberg, Google). ATS keyword scanners actively index credential titles."
                )
            },
            {
                "issue": "Enhance Bullet Readability with Project Scope",
                "suggestion": (
                    "Contextualize your accomplishments by mentioning team size, project duration, or tech stack in every bullet. "
                    "Example: 'Collaborated in an Agile team of 4 over 10 weeks to deliver a customer analytics portal'."
                )
            },
            {
                "issue": "Include Verified Portfolio or GitHub Link",
                "suggestion": (
                    "Add a direct link to your GitHub, Kaggle, or personal portfolio website in your header. "
                    "Recruiters and modern ATS scanners parse external portfolio links to verify hands-on project work."
                )
            }
        ]

        for supp in supplemental_recommendations:
            if len(recs) >= 5:
                break
            recs.append({
                "priority": priority,
                "issue": supp["issue"],
                "suggestion": supp["suggestion"]
            })
            priority += 1

        return recs

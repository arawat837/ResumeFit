"""
backend/agents/recommendation_agent.py
Recommendation Agent: Produces ranked, actionable resume fixes grounded in the candidate's actual resume.
Calls Gemini asynchronously when available, with a deterministic rubric-gap fallback.
Returns {"data": recommendations, "used_gemini": bool}.
"""

from typing import Dict, Any, List, Optional
import json
import logging
import re
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RecommendationItem(BaseModel):
    priority: int
    issue: str
    suggestion: str
    original_bullet: Optional[str] = None
    rewrite_bullet: Optional[str] = None
    role: Optional[str] = None


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
        Generates ranked, high-impact suggestions grounded directly in the candidate's actual resume text.
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
                "CRITICAL REQUIREMENT: Every single recommendation MUST be specifically grounded in the candidate's ACTUAL resume provided below.\n"
                "DO NOT provide generic or unrelated bullet points. Do NOT invent unrelated roles.\n\n"
                "Generate 5 to 7 specific, highly actionable recommendations ranked by impact priority (1 is highest priority).\n"
                "For experience bullet improvements:\n"
                "1. Quote the EXACT bullet text from the candidate's resume under 'original_bullet'.\n"
                "2. Provide an improved rewrite under 'rewrite_bullet' applying the Google XYZ formula (Accomplished [X] as measured by [Y] by doing [Z]), keeping their actual project context while adding realistic quantification and strong action verbs.\n"
                "3. Set 'role' to the specific role or project title from their resume where this bullet appeared.\n\n"
                "Return ONLY valid JSON matching this schema:\n"
                "[\n"
                "  {\n"
                '    "priority": 1,\n'
                '    "issue": "Specific issue title citing the bullet or section",\n'
                '    "suggestion": "Clear, actionable explanation citing the exact section and why this change boosts their ATS match",\n'
                '    "original_bullet": "Exact quote from their resume (or null if general section recommendation)",\n'
                '    "rewrite_bullet": "Google XYZ bullet rewrite (or null)",\n'
                '    "role": "Role title from candidate resume (or null)"\n'
                "  }\n"
                "]\n\n"
                f"Overall ATS Score: {ats_score}/100\n"
                f"Category Breakdown: {json.dumps(breakdown)}\n"
                f"Rubric Diagnostics: {json.dumps(diagnostics)}\n"
                f"Candidate Actual Experience & Bullets: {json.dumps(parsed_resume.get('experience', []))}\n"
                f"Candidate Technical Skills: {json.dumps(parsed_resume.get('skills', []))}\n"
                f"Candidate Education: {json.dumps(parsed_resume.get('education', []))}\n"
                f"Candidate Contact: {json.dumps(parsed_resume.get('contact', {}))}\n"
                f"Target JD Criteria: {json.dumps(parsed_jd) if parsed_jd else 'General ATS Assessment (no specific JD)'}"
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

                    raw_data = json.loads(clean_json)
                    if isinstance(raw_data, list):
                        validated = [RecommendationItem(**item).model_dump() for item in raw_data if isinstance(item, dict)]

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

        # 2. Deterministic Rubric-Driven Fallback grounded in candidate's actual resume
        fallback_recs = self._fallback_recommendations(scoring_result, parsed_resume, parsed_jd)
        return {"data": fallback_recs, "used_gemini": False}

    def _fallback_recommendations(
        self,
        scoring_result: Dict[str, Any],
        parsed_resume: Dict[str, Any],
        parsed_jd: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic recommendation generator strictly grounded in the candidate's actual resume.
        Identifies exact unquantified or weak bullets from their experience blocks and produces tailored rewrites.
        """
        recs: List[Dict[str, Any]] = []
        diagnostics = scoring_result.get("diagnostics", {})
        breakdown = scoring_result.get("breakdown", {})

        kw_diag = diagnostics.get("keywords", {})
        fmt_diag = diagnostics.get("formatting", {})
        sec_diag = diagnostics.get("sections", {})
        ach_diag = diagnostics.get("achievements", {})

        experience_entries = parsed_resume.get("experience", [])
        skills_list = parsed_resume.get("skills", [])
        contact = parsed_resume.get("contact", {})

        metric_regex = re.compile(r"(\d+(?:\.\d+)?%|\$\d+|\d+x|\d+\s*(?:hrs?|hours?|days?|weeks?|k))", re.IGNORECASE)

        priority = 1

        # Check 1: Extract ACTUAL bullets from candidate's experience that lack metrics
        for exp in experience_entries:
            role = exp.get("role", "Experience")
            company = exp.get("company", "")
            role_label = f"{role} ({company})" if company else role
            bullets = exp.get("bullets", [])

            for bullet in bullets:
                clean_bullet = bullet.strip().lstrip("-•* ").strip()
                if not clean_bullet or len(clean_bullet) < 15:
                    continue

                if not metric_regex.search(clean_bullet):
                    # Found an actual unquantified bullet from candidate's resume
                    # Generate a contextual Google XYZ rewrite keeping their exact core action
                    ends_punct = clean_bullet.rstrip(". ")
                    rewrite = f"{ends_punct}, improving process throughput by 25% and saving 6+ hours weekly."
                    
                    recs.append({
                        "priority": priority,
                        "issue": f"Unquantified Bullet in {role_label}",
                        "suggestion": (
                            f"In your '{role_label}' section, the bullet \"{clean_bullet}\" lacks measurable business or technical outcomes. "
                            "Apply the Google XYZ formula (Accomplished [X] as measured by [Y] by doing [Z]) to prove real-world impact."
                        ),
                        "original_bullet": clean_bullet,
                        "rewrite_bullet": rewrite,
                        "role": role_label
                    })
                    priority += 1

                if len(recs) >= 3:
                    break
            if len(recs) >= 3:
                break

        # Check 2: Missing Keywords from JD or Universal Benchmark
        missing_kw = kw_diag.get("missing", [])
        if missing_kw:
            top_missing = ", ".join(missing_kw[:4])
            first_role = experience_entries[0].get("role", "Projects") if experience_entries else "Experience"
            recs.append({
                "priority": priority,
                "issue": f"Missing Core JD Skills: {top_missing}",
                "suggestion": (
                    f"Your resume lacks high-frequency job keywords: {top_missing}. "
                    f"Add these competencies to your Technical Skills section and mention where you used them under your '{first_role}' bullets."
                ),
                "original_bullet": None,
                "rewrite_bullet": None,
                "role": None
            })
            priority += 1

        # Check 3: Formatting & Layout Hazards
        fmt_issues = fmt_diag.get("issues", [])
        if fmt_issues:
            recs.append({
                "priority": priority,
                "issue": "ATS Formatting Hazards Detected",
                "suggestion": (
                    f"{' '.join(fmt_issues)} Multi-column tables or image graphics cause ATS text extraction order to scramble. "
                    "Use a standard, single-column layout with clean bullet characters."
                ),
                "original_bullet": None,
                "rewrite_bullet": None,
                "role": None
            })
            priority += 1

        # Check 4: Missing Core Section
        missing_secs = sec_diag.get("missing", [])
        if missing_secs:
            recs.append({
                "priority": priority,
                "issue": f"Missing Required Section: {', '.join(missing_secs)}",
                "suggestion": (
                    f"ATS algorithms index standard headings: {', '.join(missing_secs)}. "
                    "Add dedicated sections using standard H2 headers (e.g. 'Education', 'Technical Skills', 'Experience')."
                ),
                "original_bullet": None,
                "rewrite_bullet": None,
                "role": None
            })
            priority += 1

        # Check 5: Action Verb Openings in Candidate Bullets
        for exp in experience_entries:
            role = exp.get("role", "Experience")
            for bullet in exp.get("bullets", []):
                clean_bullet = bullet.strip().lstrip("-•* ").strip()
                if clean_bullet and any(clean_bullet.lower().startswith(p) for p in ["responsible for", "worked on", "helped", "assisted"]):
                    # Replace passive verb with power verb
                    words = clean_bullet.split()
                    verb_replacement = "Spearheaded" if "lead" in clean_bullet.lower() else "Optimized"
                    rewritten_passive = f"{verb_replacement} {clean_bullet.lstrip('Responsible for worked on helped assisted').strip()}"
                    recs.append({
                        "priority": priority,
                        "issue": f"Passive Bullet Opening in {role}",
                        "suggestion": (
                            f"In '{role}', the bullet \"{clean_bullet}\" starts with passive language. "
                            "Begin with decisive action verbs like 'Spearheaded', 'Engineered', 'Optimized', or 'Automated'."
                        ),
                        "original_bullet": clean_bullet,
                        "rewrite_bullet": rewritten_passive,
                        "role": role
                    })
                    priority += 1
                    break
            if len(recs) >= 6:
                break

        # Check 6: LinkedIn / Portfolio URL Check
        if not contact.get("linkedin"):
            recs.append({
                "priority": priority,
                "issue": "Missing LinkedIn Profile URL in Contact Header",
                "suggestion": (
                    "Include a clean LinkedIn URL (e.g., linkedin.com/in/yourname) in your contact header. "
                    "Modern ATS parsers match candidate profiles directly against verified LinkedIn data."
                ),
                "original_bullet": None,
                "rewrite_bullet": None,
                "role": None
            })
            priority += 1

        # Guarantee minimum 5 recommendations by analyzing more actual bullets if needed
        if len(recs) < 5:
            for exp in experience_entries:
                role = exp.get("role", "Experience")
                for bullet in exp.get("bullets", []):
                    clean_b = bullet.strip().lstrip("-•* ").strip()
                    if clean_b and not any(r.get("original_bullet") == clean_b for r in recs):
                        recs.append({
                            "priority": priority,
                            "issue": f"Expand Scope & Deliverables in {role}",
                            "suggestion": (
                                f"In '{role}', expand the context for \"{clean_b}\" by detailing the tools used and team collaboration."
                            ),
                            "original_bullet": clean_b,
                            "rewrite_bullet": f"{clean_b.rstrip('.')} utilizing modern industry frameworks, exceeding delivery benchmarks by 15%.",
                            "role": role
                        })
                        priority += 1
                        if len(recs) >= 5:
                            break
                if len(recs) >= 5:
                    break

        # Fallback padding if resume had zero experience bullets
        if len(recs) < 5:
            recs.append({
                "priority": priority,
                "issue": "Add Targeted Project Experience",
                "suggestion": "Include at least 2 structured technical projects or leadership experiences with quantified outcomes.",
                "original_bullet": None,
                "rewrite_bullet": None,
                "role": None
            })

        return recs

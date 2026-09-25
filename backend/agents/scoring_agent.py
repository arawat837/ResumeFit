"""
backend/agents/scoring_agent.py
Purely deterministic ATS Rubric Scoring Engine.
No LLM calls are made here, ensuring explainable, consistent scores without hallucination.
"""

from typing import Dict, Any, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

# Common action verbs recommended by university career centers
ACTION_VERBS = {
    "accelerated", "achieved", "administered", "analyzed", "automated", "built",
    "calculated", "centralized", "collaborated", "constructed", "coordinated",
    "created", "delivered", "designed", "developed", "directed", "engineered",
    "enhanced", "established", "executed", "expanded", "formulated", "generated",
    "guided", "implemented", "improved", "increased", "initiated", "launched",
    "led", "managed", "maximized", "minimized", "modeled", "negotiated",
    "optimized", "orchestrated", "organized", "overhauled", "pioneered",
    "planned", "produced", "reduced", "refactored", "resolved", "restructured",
    "revamped", "scaled", "simplified", "spearheaded", "streamlined", "supervised",
    "trained", "transformed", "unified", "upgraded", "validated"
}

# Domain-keyed ATS Skill Benchmarks for general mode
DOMAIN_BENCHMARKS: Dict[str, List[str]] = {
    "tech": [
        "python", "sql", "git", "data analysis", "docker", "apis", "cloud", "agile", "testing"
    ],
    "business_analyst": [
        "excel", "sql", "tableau", "power bi", "data modeling", "process mapping", "stakeholder management", "requirements gathering", "kpis"
    ],
    "finance": [
        "financial modeling", "excel", "valuation", "forecasting", "budgeting", "risk analysis", "accounting", "variance analysis"
    ],
    "marketing": [
        "seo", "content strategy", "social media", "google analytics", "campaign management", "copywriting", "market research", "email marketing", "conversion rate"
    ],
    "general": [
        "communication", "project management", "problem solving", "cross-functional collaboration", "analytical skills", "leadership", "process improvement"
    ]
}

# Alias for backwards compatibility
GENERAL_ATS_BENCHMARKS = DOMAIN_BENCHMARKS["general"]


class ScoringAgent:
    """
    Evaluates structured resume and JD against a rigorous ATS rubric:
    1. keyword_match (35%): JD skill/keyword overlap or general ATS skill density
    2. formatting (20%): penalty checks for tables, images, multi-columns, length
    3. sections (20%): presence of Contact, Education, Experience, Skills
    4. achievements (25%): action verbs and quantified bullet metrics
    """

    def __init__(self):
        pass

    async def run(
        self,
        parsed_resume: Dict[str, Any],
        parsed_jd: Optional[Dict[str, Any]],
        formatting_meta: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """
        Executes rubric scoring synchronously/asynchronously.
        Returns dict containing 'ats_score', 'breakdown', and detailed 'diagnostics'.
        """
        # 1. Keyword Match Score (0 - 100)
        kw_score, kw_diagnostics = self._calculate_keyword_match(parsed_resume, parsed_jd, mode)

        # 2. Formatting Score (0 - 100)
        fmt_score, fmt_diagnostics = self._calculate_formatting(formatting_meta)

        # 3. Sections Score (0 - 100)
        sec_score, sec_diagnostics = self._calculate_sections(parsed_resume)

        # 4. Quantified Achievements Score (0 - 100)
        ach_score, ach_diagnostics = self._calculate_achievements(parsed_resume)

        # Weighted Overall ATS Score
        # Keywords: 35%, Achievements: 25%, Formatting: 20%, Sections: 20%
        composite = (
            0.35 * kw_score +
            0.20 * fmt_score +
            0.20 * sec_score +
            0.25 * ach_score
        )
        ats_score = max(0, min(100, int(round(composite))))

        return {
            "ats_score": ats_score,
            "breakdown": {
                "keyword_match": kw_score,
                "formatting": fmt_score,
                "sections": sec_score,
                "achievements": ach_score,
            },
            "diagnostics": {
                "keywords": kw_diagnostics,
                "formatting": fmt_diagnostics,
                "sections": sec_diagnostics,
                "achievements": ach_diagnostics,
            }
        }

    def _get_all_resume_text(self, resume: Dict[str, Any]) -> str:
        """Aggregates all text fields from parsed resume into a single lowercase string."""
        parts = []
        if resume.get("summary"):
            parts.append(resume["summary"])
        for skill in resume.get("skills", []):
            parts.append(str(skill))
        for exp in resume.get("experience", []):
            parts.append(exp.get("role", ""))
            parts.append(exp.get("company", ""))
            parts.extend(exp.get("bullets", []))
        for edu in resume.get("education", []):
            parts.append(edu.get("degree", ""))
            parts.append(edu.get("institution", ""))
        return " ".join(parts).lower()

    def _detect_domain(self, resume: Dict[str, Any]) -> str:
        """
        Detects the candidate's domain by checking which domain benchmark set
        has the highest overlap with the candidate's parsed skills list.
        If the max overlap is 0, defaults to 'general'.
        """
        raw_skills = resume.get("skills", [])
        if not raw_skills:
            return "general"

        skills_list = [str(s).strip().lower() for s in raw_skills if str(s).strip()]
        if not skills_list:
            return "general"

        best_domain = "general"
        max_overlap = 0

        # Check specialized domains first, then general
        for domain in ["tech", "business_analyst", "finance", "marketing", "general"]:
            benchmarks = DOMAIN_BENCHMARKS[domain]
            overlap = 0
            for b in benchmarks:
                b_low = b.lower()
                for s in skills_list:
                    if b_low == s or (len(s) >= 3 and s in b_low) or (len(b_low) >= 3 and b_low in s):
                        overlap += 1
                        break
            if overlap > max_overlap:
                max_overlap = overlap
                best_domain = domain

        if max_overlap == 0:
            return "general"

        return best_domain

    def _calculate_keyword_match(
        self,
        resume: Dict[str, Any],
        jd: Optional[Dict[str, Any]],
        mode: str
    ) -> tuple[int, Dict[str, Any]]:
        full_text = self._get_all_resume_text(resume)

        # Mode A: JD provided (preset or custom)
        if jd and (jd.get("required_skills") or jd.get("keywords")):
            required = [s.strip().lower() for s in jd.get("required_skills", []) if s.strip()]
            keywords = [k.strip().lower() for k in jd.get("keywords", []) if k.strip()]
            all_targets = list(dict.fromkeys(required + keywords))

            if not all_targets:
                return 75, {"matched": [], "missing": [], "detected_domain": None, "mode": "jd_empty"}

            matched = [t for t in all_targets if re.search(r"\b" + re.escape(t) + r"\b", full_text)]
            missing = [t for t in all_targets if t not in matched]

            ratio = len(matched) / len(all_targets)
            score = int(round(ratio * 100))
            return max(15, min(100, score)), {
                "matched": matched,
                "missing": missing,
                "total_targets": len(all_targets),
                "detected_domain": None,
                "mode": "jd"
            }

        # Mode B: General ATS mode (no JD)
        # Evaluates core competency density & technical skills present using domain-aware benchmarks
        domain = self._detect_domain(resume)
        active_benchmarks = DOMAIN_BENCHMARKS[domain]

        skills_found = [str(s).strip().lower() for s in resume.get("skills", []) if str(s).strip()]
        matched_benchmarks = [
            b for b in active_benchmarks
            if re.search(r"\b" + re.escape(b) + r"\b", full_text)
        ]

        skill_count = len(skills_found)
        score = 50 + min(30, skill_count * 3) + min(20, len(matched_benchmarks) * 3)
        score = max(25, min(95, score))

        missing_benchmarks = [b for b in active_benchmarks if b not in matched_benchmarks]
        return score, {
            "matched": matched_benchmarks,
            "missing": missing_benchmarks,
            "detected_domain": domain,
            "mode": "general"
        }

    def _calculate_formatting(self, formatting_meta: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        score = 100
        issues = []

        if formatting_meta.get("has_tables", False):
            score -= 15
            issues.append("Resume contains tables, which frequently scramble ATS text extraction.")

        if formatting_meta.get("image_count", 0) > 0:
            score -= 15
            issues.append("Resume contains images/graphics; ATS cannot read embedded text in images.")

        if formatting_meta.get("has_multi_column", False):
            score -= 15
            issues.append("Multi-column layout detected; risk of out-of-order reading by older ATS.")

        char_count = formatting_meta.get("char_count", 0)
        if char_count < 600:
            score -= 20
            issues.append("Resume appears too brief (under 600 characters).")
        elif char_count > 6000:
            score -= 10
            issues.append("Resume exceeds standard 1-2 page length for university applicants.")

        return max(20, min(100, score)), {"issues": issues}

    def _calculate_sections(self, resume: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        score = 0
        missing = []
        present = []

        # 1. Contact (25 pts)
        contact = resume.get("contact", {})
        if contact.get("email") or contact.get("phone"):
            score += 25
            present.append("Contact Info")
        else:
            missing.append("Contact Information (Email/Phone)")

        # 2. Education (25 pts)
        if resume.get("education") and len(resume["education"]) > 0:
            score += 25
            present.append("Education")
        else:
            missing.append("Education Section")

        # 3. Experience (25 pts)
        if resume.get("experience") and len(resume["experience"]) > 0:
            score += 25
            present.append("Experience / Projects")
        else:
            missing.append("Experience / Work History Section")

        # 4. Skills (25 pts)
        if resume.get("skills") and len(resume["skills"]) > 0:
            score += 25
            present.append("Skills")
        else:
            missing.append("Skills Section")

        return max(0, min(100, score)), {"present": present, "missing": missing}

    def _calculate_achievements(self, resume: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        bullets: List[str] = []
        for exp in resume.get("experience", []):
            bullets.extend(exp.get("bullets", []))

        if not bullets:
            return 30, {
                "total_bullets": 0,
                "metric_bullets": 0,
                "action_verb_bullets": 0,
                "issues": ["No bullet points found in experience section."]
            }

        # Strict quantification signal: requires percentage, currency, multiplier, or recognized scale unit
        metric_pattern = re.compile(
            r"("
            r"\b\d+(?:\.\d+)?\s*%"  # Percentages: 20%, 3.5 %
            r"|\$(?:\d+(?:\.\d+)?|\d{1,3}(?:,\d{3})+)(?:[kKmMbB])?\b"  # Currency: $500, $12k, $1.5M
            r"|\b\d+(?:\.\d+)?\s*[xX]\b"  # Multipliers: 3x, 2.5X
            r"|\b\d+(?:\.\d+)?\s*(?:[kKmMbB]|hrs?|hours?|days?|weeks?|months?|mins?|minutes?)\b"  # Units: 10 hrs, 4 weeks, 50k
            r")"
        )

        metric_count = 0
        action_verb_count = 0

        for b in bullets:
            cleaned = b.strip().lower()
            if metric_pattern.search(cleaned):
                metric_count += 1

            # First word check for strong action verb
            first_word = re.split(r"[\s\-_,.:;]+", cleaned)[0] if cleaned else ""
            if first_word in ACTION_VERBS:
                action_verb_count += 1

        total = len(bullets)
        metric_ratio = metric_count / total
        verb_ratio = action_verb_count / total

        # Achievements score: 60% on quantifiable metrics, 40% on action verbs
        score = int(round((0.60 * metric_ratio + 0.40 * verb_ratio) * 100))
        score = max(20, min(100, score))

        return score, {
            "total_bullets": total,
            "metric_bullets": metric_count,
            "action_verb_bullets": action_verb_count,
            "metric_percentage": round(metric_ratio * 100),
            "verb_percentage": round(verb_ratio * 100),
        }

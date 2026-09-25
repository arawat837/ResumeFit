"""
backend/agents/pipeline.py
Pipeline Orchestrator for ResumeFit.
Coordinates Parser, JD, Scoring, and Recommendation agents.
Maintains granular agent-level engine status and accurate top-level engine attribution.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from .parser_agent import ParserAgent
from .jd_agent import JDAgent
from .scoring_agent import ScoringAgent
from .recommendation_agent import RecommendationAgent

logger = logging.getLogger(__name__)


class AgentPipeline:
    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client
        self.parser_agent = ParserAgent(gemini_client=gemini_client)
        self.jd_agent = JDAgent(gemini_client=gemini_client)
        self.scoring_agent = ScoringAgent()  # Purely deterministic rubric calculation (no LLM call)
        self.recommendation_agent = RecommendationAgent(gemini_client=gemini_client)

    async def run(
        self,
        resume_text: str,
        formatting_meta: Dict[str, Any],
        mode: str,
        jd_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the agentic scanning pipeline.

        Returns:
            {
                "engine": "gemini" | "rubric_fallback",
                "agent_engines": {
                    "parser": bool,
                    "jd": bool | None,
                    "recommendation": bool
                },
                "ats_score": int,
                "breakdown": {
                    "keyword_match": int,
                    "formatting": int,
                    "sections": int,
                    "achievements": int
                },
                "recommendations": list[dict],
                "parsed_summary": dict
            }
        """
        has_jd = bool(jd_text and jd_text.strip()) and (mode != "general")

        # Step 1 & 2: Concurrency & Conditionality
        if has_jd:
            logger.info("Executing Parser Agent and JD Agent concurrently via asyncio.gather")
            parser_res, jd_res = await asyncio.gather(
                self.parser_agent.run(resume_text),
                self.jd_agent.run(jd_text)
            )
            parser_used_gemini = parser_res["used_gemini"]
            jd_used_gemini = jd_res["used_gemini"]
            parsed_resume = parser_res["data"]
            parsed_jd = jd_res["data"]
        else:
            logger.info("General ATS mode: Skipping JD Agent completely (0 added latency/cost)")
            parser_res = await self.parser_agent.run(resume_text)
            parser_used_gemini = parser_res["used_gemini"]
            jd_used_gemini = None  # Explicitly None because JD agent did not execute
            parsed_resume = parser_res["data"]
            parsed_jd = None

        # Step 3: Purely deterministic Rubric Scoring Agent (no LLM call)
        scoring_result = await self.scoring_agent.run(
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            formatting_meta=formatting_meta,
            mode=mode
        )

        # Step 4: Sequential Recommendation Agent (Gemini or deterministic rubric fallback)
        rec_res = await self.recommendation_agent.run(
            scoring_result=scoring_result,
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd
        )
        rec_used_gemini = rec_res["used_gemini"]
        recommendations = rec_res["data"]

        # Granular agent engine breakdown
        agent_engines = {
            "parser": parser_used_gemini,
            "jd": jd_used_gemini,
            "recommendation": rec_used_gemini
        }

        # Top-level engine: "gemini" ONLY if EVERY agent that actually executed succeeded with Gemini
        executed_statuses = [parser_used_gemini, rec_used_gemini]
        if has_jd and jd_used_gemini is not None:
            executed_statuses.append(jd_used_gemini)

        all_used_gemini = all(s is True for s in executed_statuses)
        engine = "gemini" if all_used_gemini else "rubric_fallback"

        logger.info(
            f"Pipeline completed with top-level engine='{engine}', "
            f"agent_engines={agent_engines}"
        )

        return {
            "engine": engine,
            "agent_engines": agent_engines,
            "ats_score": scoring_result["ats_score"],
            "breakdown": scoring_result["breakdown"],
            "recommendations": recommendations,
            "parsed_resume": parsed_resume,
            "parsed_jd": parsed_jd,
            "scoring_result": scoring_result,
            "parsed_summary": {
                "skills_detected": len(parsed_resume.get("skills", [])),
                "experience_entries": len(parsed_resume.get("experience", [])),
                "education_entries": len(parsed_resume.get("education", [])),
                "has_jd": has_jd,
            }
        }

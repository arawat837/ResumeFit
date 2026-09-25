"""
backend/tests/test_recommendation_and_benchmarks.py
Unit tests verifying:
1. Recommendation fallback rewrite diversity and deterministic template selection.
2. Passive verb replacement using diverse action verbs.
3. Gemini success partial padding when >= 3 recommendations returned.
4. Gemini complete fallback when < 3 recommendations returned.
5. Domain-aware benchmark selection in ScoringAgent (marketing, finance, business analyst, tech, general).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.recommendation_agent import (
    RecommendationAgent,
    QUANT_TEMPLATES,
    ACTION_VERB_POOL,
)
from agents.scoring_agent import ScoringAgent, DOMAIN_BENCHMARKS


@pytest.mark.asyncio
async def test_recommendation_fallback_diversity():
    """
    Test 1: Run recommendation agent on two resumes with different unquantified bullets
    and assert their fallback rewrites do not share the same closing clause.
    """
    agent = RecommendationAgent(gemini_client=None)

    scoring_result = {
        "ats_score": 70,
        "breakdown": {"keyword_match": 70, "formatting": 80, "sections": 80, "achievements": 50},
        "diagnostics": {
            "keywords": {"missing": []},
            "formatting": {"issues": []},
            "sections": {"missing": []},
            "achievements": {"action_verb_ratio": 0.5, "quantified_bullet_ratio": 0.0},
        },
    }

    # Resume A: has an unquantified bullet about reporting dashboards
    resume_a = {
        "contact": {"linkedin": "linkedin.com/in/alex"},
        "skills": ["Python", "FastAPI"],
        "education": [{"degree": "B.S. CS", "institution": "State University"}],
        "experience": [
            {
                "role": "Software Engineer",
                "company": "Company A",
                "bullets": ["Developed internal reporting dashboard for business stakeholders"],
            }
        ],
    }

    # Resume B: has an unquantified bullet about database migrations
    resume_b = {
        "contact": {"linkedin": "linkedin.com/in/taylor"},
        "skills": ["PostgreSQL", "Docker"],
        "education": [{"degree": "B.S. CS", "institution": "State University"}],
        "experience": [
            {
                "role": "Backend Engineer",
                "company": "Company B",
                "bullets": ["Managed database migrations and monitored system performance"],
            }
        ],
    }

    res_a = await agent.run(scoring_result, resume_a, None)
    res_b = await agent.run(scoring_result, resume_b, None)

    assert not res_a["used_gemini"]
    assert not res_b["used_gemini"]

    # Extract the unquantified bullet rewrite from each
    bullet_recs_a = [r for r in res_a["data"] if r.get("original_bullet") == "Developed internal reporting dashboard for business stakeholders"]
    bullet_recs_b = [r for r in res_b["data"] if r.get("original_bullet") == "Managed database migrations and monitored system performance"]

    assert len(bullet_recs_a) >= 1
    assert len(bullet_recs_b) >= 1

    rewrite_a = bullet_recs_a[0]["rewrite_bullet"]
    rewrite_b = bullet_recs_b[0]["rewrite_bullet"]

    assert rewrite_a is not None
    assert rewrite_b is not None
    # Assert they do not share the same closing clause / template
    assert rewrite_a != rewrite_b

    # Verify both rewrites were generated from the valid QUANT_TEMPLATES pool
    assert any(t.rstrip(".") in rewrite_a for t in QUANT_TEMPLATES)
    assert any(t.rstrip(".") in rewrite_b for t in QUANT_TEMPLATES)


@pytest.mark.asyncio
async def test_passive_verb_replacement_diversity():
    """
    Assert passive verbs ('responsible for', 'worked on') are replaced
    with action verbs from ACTION_VERB_POOL.
    """
    agent = RecommendationAgent(gemini_client=None)

    scoring_result = {
        "ats_score": 65,
        "breakdown": {"keyword_match": 60, "formatting": 80, "sections": 80, "achievements": 40},
        "diagnostics": {"keywords": {}, "formatting": {}, "sections": {}, "achievements": {}},
    }

    resume = {
        "contact": {"linkedin": "linkedin.com/in/candidate"},
        "skills": ["Python"],
        "education": [],
        "experience": [
            {
                "role": "Team Lead",
                "bullets": [
                    "Responsible for coordinating daily sprint standups across 4 departments with 95% on-time delivery"
                ],
            }
        ],
    }

    res = await agent.run(scoring_result, resume, None)
    passive_recs = [r for r in res["data"] if "Passive Bullet Opening" in r.get("issue", "")]
    assert len(passive_recs) >= 1

    rewrite = passive_recs[0]["rewrite_bullet"]
    first_word = rewrite.split()[0]
    assert first_word in ACTION_VERB_POOL


@pytest.mark.asyncio
async def test_gemini_partial_padding_when_ge_3():
    """
    Assert that when Gemini returns 3 valid recommendations (>= 3 but < 5),
    Gemini's recommendations are preserved and padded up to 5 from fallback.
    """
    mock_gemini = MagicMock()
    mock_response = MagicMock()
    # Mock returns 3 items from Gemini
    mock_response.text = """[
        {"priority": 1, "issue": "Gemini Item 1", "suggestion": "Fix 1", "original_bullet": "Bullet 1", "rewrite_bullet": "Rewrite 1", "role": "Role 1"},
        {"priority": 2, "issue": "Gemini Item 2", "suggestion": "Fix 2", "original_bullet": "Bullet 2", "rewrite_bullet": "Rewrite 2", "role": "Role 1"},
        {"priority": 3, "issue": "Gemini Item 3", "suggestion": "Fix 3", "original_bullet": null, "rewrite_bullet": null, "role": null}
    ]"""

    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    agent = RecommendationAgent(gemini_client=mock_gemini)

    scoring_result = {
        "ats_score": 75,
        "breakdown": {},
        "diagnostics": {"keywords": {}, "formatting": {}, "sections": {}, "achievements": {}},
    }
    resume = {
        "contact": {},
        "skills": ["Python"],
        "education": [],
        "experience": [
            {
                "role": "Software Developer",
                "bullets": ["Bullet 1", "Bullet 2", "An extra unquantified bullet that needs work"],
            }
        ],
    }

    res = await agent.run(scoring_result, resume, None)
    assert res["used_gemini"] is True
    assert len(res["data"]) >= 5

    # Check that Gemini's original 3 items are present
    issues = [r["issue"] for r in res["data"]]
    assert "Gemini Item 1" in issues
    assert "Gemini Item 2" in issues
    assert "Gemini Item 3" in issues

    # Check that covered bullets ('Bullet 1', 'Bullet 2') were not duplicated by fallback padding
    non_gemini_recs = [r for r in res["data"] if r["issue"] not in ["Gemini Item 1", "Gemini Item 2", "Gemini Item 3"]]
    for pad_rec in non_gemini_recs:
        if pad_rec.get("original_bullet"):
            assert pad_rec["original_bullet"] not in ["Bullet 1", "Bullet 2"]


@pytest.mark.asyncio
async def test_gemini_falls_through_when_lt_3():
    """
    Assert that when Gemini returns < 3 recommendations, it falls through to fallback.
    """
    mock_gemini = MagicMock()
    mock_response = MagicMock()
    # Mock returns only 2 items
    mock_response.text = """[
        {"priority": 1, "issue": "Item 1", "suggestion": "Sugg 1", "original_bullet": null, "rewrite_bullet": null, "role": null},
        {"priority": 2, "issue": "Item 2", "suggestion": "Sugg 2", "original_bullet": null, "rewrite_bullet": null, "role": null}
    ]"""
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    agent = RecommendationAgent(gemini_client=mock_gemini)

    scoring_result = {
        "ats_score": 75,
        "breakdown": {},
        "diagnostics": {"keywords": {}, "formatting": {}, "sections": {}, "achievements": {}},
    }
    resume = {
        "contact": {},
        "skills": ["Python"],
        "education": [],
        "experience": [],
    }

    res = await agent.run(scoring_result, resume, None)
    assert res["used_gemini"] is False
    assert len(res["data"]) >= 5


@pytest.mark.asyncio
async def test_scoring_agent_marketing_resume():
    """
    Test 2: Run scoring agent on a marketing resume (no python/sql/git in skills)
    and assert that tech benchmarks are not surfaced in missing keywords.
    """
    scoring_agent = ScoringAgent()

    marketing_resume = {
        "summary": "Creative Marketing Specialist with 3+ years experience growing brands.",
        "skills": ["SEO", "Content Strategy", "Social Media", "Google Analytics", "Copywriting"],
        "education": [{"degree": "B.A. Marketing", "institution": "Northwestern University"}],
        "experience": [
            {
                "role": "Marketing Coordinator",
                "company": "BrandCo",
                "bullets": [
                    "Managed SEO content strategy resulting in a 45% increase in organic search traffic.",
                    "Executed social media campaigns across 4 platforms reaching 200k+ impressions.",
                ],
            }
        ],
    }

    meta = {"has_tables": False, "image_count": 0, "has_multi_column": False, "char_count": 1200}

    result = await scoring_agent.run(marketing_resume, None, meta, mode="general")

    kw_diag = result["diagnostics"]["keywords"]
    assert kw_diag["detected_domain"] == "marketing"

    # Crucial assertion: tech benchmarks must NOT be in missing keywords
    tech_keywords = {"python", "sql", "git", "docker"}
    missing = set(kw_diag["missing"])
    assert not (tech_keywords & missing), f"Tech keywords found in marketing missing: {tech_keywords & missing}"

    # Marketing keywords that weren't in the resume should be in missing
    # Marketing benchmarks: seo, content strategy, social media, google analytics, campaign management, copywriting, market research, email marketing, conversion rate
    # Missing should include things like "market research", "email marketing", "conversion rate"
    assert any(m in DOMAIN_BENCHMARKS["marketing"] for m in kw_diag["missing"])


@pytest.mark.asyncio
async def test_scoring_agent_domain_detection_all():
    """
    Assert domain detection works accurately for finance, business analyst, tech, and general.
    """
    scoring_agent = ScoringAgent()
    meta = {"has_tables": False, "image_count": 0, "has_multi_column": False, "char_count": 1000}

    # 1. Finance resume
    finance_res = {
        "skills": ["Financial Modeling", "Valuation", "Forecasting", "Budgeting", "Excel"],
        "experience": [{"role": "Financial Analyst", "bullets": ["Built financial models for $20M acquisition"]}]
    }
    f_result = await scoring_agent.run(finance_res, None, meta, mode="general")
    assert f_result["diagnostics"]["keywords"]["detected_domain"] == "finance"
    assert "python" not in f_result["diagnostics"]["keywords"]["missing"]

    # 2. Business Analyst resume
    ba_res = {
        "skills": ["Tableau", "Power BI", "Data Modeling", "Process Mapping", "Requirements Gathering"],
        "experience": [{"role": "Business Analyst", "bullets": ["Mapped business workflows for 5 teams"]}]
    }
    ba_result = await scoring_agent.run(ba_res, None, meta, mode="general")
    assert ba_result["diagnostics"]["keywords"]["detected_domain"] == "business_analyst"

    # 3. Tech resume
    tech_res = {
        "skills": ["Python", "Docker", "Git", "APIs", "Cloud"],
        "experience": [{"role": "Software Engineer", "bullets": ["Deployed microservices on cloud"]}]
    }
    t_result = await scoring_agent.run(tech_res, None, meta, mode="general")
    assert t_result["diagnostics"]["keywords"]["detected_domain"] == "tech"

    # 4. General resume (no specialized keywords)
    gen_res = {
        "skills": ["Team Communication", "Problem Solving", "Leadership"],
        "experience": [{"role": "Assistant", "bullets": ["Supported team coordination and communications"]}]
    }
    g_result = await scoring_agent.run(gen_res, None, meta, mode="general")
    assert g_result["diagnostics"]["keywords"]["detected_domain"] == "general"

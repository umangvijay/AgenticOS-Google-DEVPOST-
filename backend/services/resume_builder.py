"""
AgentOS — Resume builder.

Turns unstructured profile text (or existing JSON) into a structured ATS-ready
resume, scores it against a job description, and renders HTML.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Union

from backend.models.resume import Resume
from backend.services import gemini_client
from backend.services.ats_analyzer_service import ATSAnalyzerService
from backend.services.jd_parser_service import JDParserService
from backend.services.resume_renderer import ResumeRendererService
from backend.services.resume_tailor_service import ResumeTailorService


class ResumeBuilderError(Exception):
    pass


def _as_resume(source: Union[str, dict, Resume]) -> Resume:
    if isinstance(source, Resume):
        return source
    if isinstance(source, dict):
        return Resume.model_validate(source)
    text = (source or "").strip()
    if not text:
        raise ResumeBuilderError("Empty resume")
    if text.startswith("{"):
        return Resume.model_validate_json(text)
    raise ResumeBuilderError("Resume text must be parsed first")


async def parse_resume_from_text(profile_text: str) -> Resume:
    """Convert a CV / notes dump into a structured Resume. Never invent employers."""
    if not (profile_text or "").strip():
        raise ResumeBuilderError("No resume text provided")
    prompt = f"""Convert this person's background into a structured resume JSON.
Do NOT invent employers, dates, degrees, or metrics that are not in the source.
You MAY tighten wording and add ATS-friendly phrasing for facts that ARE present.
If contact fields are missing, use placeholders like "name@example.com" only when the source has no email.

SOURCE:
{profile_text[:20000]}

Return JSON matching:
{{
  "id": "string",
  "contact": {{"name":"","email":"","phone":"","linkedin":"","github":"","location":""}},
  "summary": "string",
  "skills": ["..."],
  "experience": [{{"company":"","title":"","location":"","start_date":"","end_date":"","bullets":["..."]}}],
  "education": [{{"institution":"","degree":"","graduation_date":""}}],
  "projects": [{{"name":"","description":"","bullets":["..."],"technologies":["..."]}}]
}}
"""
    data = await gemini_client.generate_json(prompt)
    if not isinstance(data, dict):
        raise ResumeBuilderError("Model returned an invalid resume")
    data.setdefault("id", str(uuid.uuid4()))
    return Resume.model_validate(data)


async def create_and_score(
    profile_text: str,
    job_description: str = "",
    tailor: bool = False,
) -> Dict[str, Any]:
    resume = await parse_resume_from_text(profile_text)
    renderer = ResumeRendererService()
    result: Dict[str, Any] = {
        "resume": resume.model_dump(mode="json"),
        "html": renderer.render_html(resume),
    }
    if not job_description.strip():
        return result

    jd = JDParserService().parse_job_description(job_description)
    if tailor:
        tailored = ResumeTailorService().tailor(resume, jd, target_job_id=str(uuid.uuid4()))
        resume = tailored.resume
        result["resume"] = resume.model_dump(mode="json")
        result["html"] = renderer.render_html(resume)
        result["tailored"] = True
    score = ATSAnalyzerService().analyze(resume, jd)
    result["ats"] = score.model_dump(mode="json")
    result["job"] = {"title": jd.title, "company": jd.company}
    return result


def score_resume(resume_source: Union[str, dict, Resume], job_description: str) -> Dict[str, Any]:
    resume = _as_resume(resume_source)
    jd = JDParserService().parse_job_description(job_description)
    score = ATSAnalyzerService().analyze(resume, jd)
    return {
        "ats": score.model_dump(mode="json"),
        "job": {"title": jd.title, "company": jd.company},
        "resume_id": resume.id,
    }

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.dependencies.auth import get_current_user, AuthenticatedUser, require_not_viewer
from backend.security.rate_limiter import check_rate_limit
from backend.models.resume import Resume
from backend.services.jd_parser_service import JDParserService
from backend.services.ats_analyzer_service import ATSAnalyzerService
from backend.services.resume_tailor_service import ResumeTailorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["resume"])

class AnalyzeRequest(BaseModel):
    master_resume: Dict[str, Any]
    job_description: str

class TailorRequest(BaseModel):
    master_resume: Dict[str, Any]
    job_description: str
    target_job_id: str

from fastapi import UploadFile, File, Form
import pdfplumber
import io
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
import json

@router.post("/scan", status_code=status.HTTP_200_OK)
async def scan_resume(
    file: UploadFile = File(...),
    jobDescription: str = Form(...),
    user: AuthenticatedUser = Depends(require_not_viewer)
):
    """
    Parse a PDF resume and analyze it against a job description using Gemini.
    """
    check_rate_limit(f"user:{user.user_id}", "resume_analyze")
    
    try:
        # Extract text from PDF
        text = ""
        content = await file.read()
        if file.filename.endswith('.pdf'):
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        else:
            text = content.decode('utf-8')
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")
            
        # Analyze with Gemini
        client_kwargs = {}
        if not settings.GEMINI_API_KEY:
            client_kwargs = {"vertexai": True, "project": settings.GOOGLE_CLOUD_PROJECT, "location": settings.GOOGLE_CLOUD_REGION}
        else:
            client_kwargs = {"api_key": settings.GEMINI_API_KEY}
            
        llm = Gemini(model=settings.GEMINI_MODEL, client_kwargs=client_kwargs)
        
        prompt = f"""
You are an expert ATS (Applicant Tracking System) Analyzer.
Analyze the following resume against the job description.

JOB DESCRIPTION:
{jobDescription}

RESUME:
{text}

Provide your analysis in JSON format with exactly these keys:
- "score": an integer from 0 to 100 representing the ATS match score.
- "keywords_found": a list of strings of important keywords found in both.
- "keywords_missing": a list of strings of important keywords from the JD missing in the resume.
- "suggestions": a list of strings with actionable advice to improve the resume.

Output ONLY valid JSON.
"""
        response = llm.generate_content(prompt)
        response_text = response.text
        
        # Clean up markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        result = json.loads(response_text.strip())
        return result
        
    except Exception as e:
        logger.error(f"Error scanning resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_resume(
    body: AnalyzeRequest,
    user: AuthenticatedUser = Depends(require_not_viewer)
):
    """
    Analyze a master resume against a job description.
    Provides deterministic scoring and gap analysis.
    """
    check_rate_limit(f"user:{user.user_id}", "resume_analyze")
    
    try:
        resume = Resume.model_validate(body.master_resume)
        jd_parser = JDParserService()
        jd = jd_parser.parse_job_description(body.job_description)
        
        analyzer = ATSAnalyzerService()
        score = analyzer.analyze(resume, jd)
        return score.model_dump()
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tailor", status_code=status.HTTP_200_OK)
async def tailor_resume(
    body: TailorRequest,
    user: AuthenticatedUser = Depends(require_not_viewer)
):
    """
    Tailors a master resume to a job description.
    Does NOT invent facts.
    """
    check_rate_limit(f"user:{user.user_id}", "resume_tailor")
    
    try:
        resume = Resume.model_validate(body.master_resume)
        jd_parser = JDParserService()
        jd = jd_parser.parse_job_description(body.job_description)
        
        tailor_service = ResumeTailorService()
        tailored = tailor_service.tailor(resume, jd, body.target_job_id)
        
        return {
            "status": "success",
            "tailored_resume": tailored.model_dump()
        }
    except Exception as e:
        logger.error(f"Error tailoring resume: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Note: We omit /render for now as WeasyPrint is quite heavy and it's 
# mocked out in the current implementation of the services.

import pytest
import pdfplumber
import io
from backend.models.resume import Resume, ContactInfo, Experience
from backend.services.resume_renderer import ResumeRendererService
from backend.services.ats_analyzer_service import ATSAnalyzerService
from backend.models.resume import JobDescription

def test_resume_renderer_pdf_extraction():
    # Setup mock resume
    resume = Resume(
        id="res-123",
        contact=ContactInfo(
            name="John Doe",
            email="john.doe@example.com",
            phone="555-0199"
        ),
        summary="A highly skilled software engineer.",
        skills=["Python", "FastAPI"],
        experience=[
            Experience(
                company="Google",
                title="Software Engineer",
                start_date="2020",
                bullets=["Built an incredible system."]
            )
        ]
    )
    
    renderer = ResumeRendererService()
    pdf_bytes = renderer.render_pdf(resume)
    
    assert len(pdf_bytes) > 0, "PDF bytes should be generated"
    
    # Read PDF text using pdfplumber to verify ATS machine readability
    extracted_text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"
            
    # Verify critical structural elements survived rendering and are parseable
    assert "John Doe" in extracted_text
    assert "john.doe@example.com" in extracted_text
    assert "555-0199" in extracted_text
    assert "Google" in extracted_text
    assert "Built an incredible system." in extracted_text
    assert "FastAPI" in extracted_text

def test_ats_analyzer_math():
    analyzer = ATSAnalyzerService()
    
    resume = Resume(
        id="res-123",
        contact=ContactInfo(name="John Doe", email="j@example.com", phone="123"),
        skills=["Python", "GCP"],
        experience=[Experience(company="A", title="B", start_date="2020", bullets=[])]
    )
    
    jd = JobDescription(
        raw_text="Test JD",
        title="Engineer",
        company="Tech Corp",
        required_skills=["python", "fastapi"],
        preferred_skills=["gcp", "terraform"],
        keywords=["engineer"],
        required_experience_years=2
    )
    
    score = analyzer.analyze(resume, jd)
    
    # Missing required: fastapi
    # Missing preferred: terraform
    # Matched required: python
    # Matched preferred: gcp
    # Total required = 2. Total preferred = 2. Weight = 2*2 + 2 = 6
    # Matched weight = (1*2) + (1*1) = 3.
    # Score = 3/6 = 50%
    assert score.skill_match_score == 50.0
    assert "fastapi" in score.missing_required_skills
    assert "terraform" in score.missing_missing_preferred_skills if hasattr(score, 'missing_missing_preferred_skills') else "terraform" in score.missing_preferred_skills

import re
import uuid
import copy
from typing import List
from backend.models.resume import Resume, JobDescription, TailoredResumeVersion
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class AntiFabricationValidator:
    def validate(self, original: Resume, tailored: Resume) -> bool:
        """
        Validates that the tailored resume has not fabricated any facts:
        1. No new skills added that aren't in the original.
        2. No new numerical metrics (numbers) in bullets that aren't in the original bullets.
        3. No new employers/companies.
        """
        # Check skills
        original_skills_norm = {self._normalize(s) for s in original.skills}
        for s in tailored.skills:
            if self._normalize(s) not in original_skills_norm:
                logger.warning(f"Fabrication detected: Skill '{s}' added.")
                return False
                
        # Check companies
        orig_companies = {self._normalize(e.company) for e in original.experience}
        for e in tailored.experience:
            if self._normalize(e.company) not in orig_companies:
                logger.warning(f"Fabrication detected: Company '{e.company}' added.")
                return False
                
        # Check metrics (numbers)
        orig_numbers = self._extract_numbers(self._get_all_bullets(original))
        tailored_numbers = self._extract_numbers(self._get_all_bullets(tailored))
        for num in tailored_numbers:
            if num not in orig_numbers:
                logger.warning(f"Fabrication detected: Metric '{num}' added.")
                return False
                
        return True
        
    def _normalize(self, term: str) -> str:
        return re.sub(r'[^a-z0-9]', '', term.lower())
        
    def _get_all_bullets(self, resume: Resume) -> str:
        text = []
        for exp in resume.experience:
            text.extend(exp.bullets)
        for proj in resume.projects:
            text.extend(proj.bullets)
        return " ".join(text)
        
    def _extract_numbers(self, text: str) -> set:
        return set(re.findall(r'\b\d+(?:[\.,]\d+)?\b', text))

class ResumeTailorService:
    def __init__(self):
        from google import genai
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = genai.Client(
                vertexai=True, 
                project=settings.GOOGLE_CLOUD_PROJECT, 
                location=settings.GOOGLE_CLOUD_REGION
            )
        self.validator = AntiFabricationValidator()

    def tailor(self, master_resume: Resume, jd: JobDescription, target_job_id: str) -> TailoredResumeVersion:
        """
        Rewrites the master resume to align with the JD without fabricating information.
        """
        from google.genai import types
        
        prompt = f"""
        You are an expert Resume Tailor.
        Rewrite the bullet points of the provided resume to better align with the given Job Description.
        
        CRITICAL RULES (ANTI-FABRICATION):
        1. DO NOT invent technologies, tools, or skills.
        2. DO NOT invent metrics (numbers, percentages, dollar amounts).
        3. DO NOT invent employers, projects, or years of experience.
        4. ONLY rephrase existing experience, emphasize existing skills, and improve clarity.
        
        Job Description:
        {jd.model_dump_json(indent=2)}
        
        Master Resume:
        {master_resume.model_dump_json(indent=2)}
        
        Return ONLY the updated Resume JSON matching the exact same schema.
        """
        
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Resume,
                    temperature=0.2
                )
            )
            
            if not response.text:
                raise ValueError("Model returned empty response.")
                
            tailored_resume = Resume.model_validate_json(response.text)
            
            # Post-tailoring validation
            is_valid = self.validator.validate(master_resume, tailored_resume)
            if not is_valid:
                logger.error("Anti-fabrication validation failed. Falling back to master resume.")
                # Fallback to master if hallucination occurs
                tailored_resume = copy.deepcopy(master_resume)
                
            # Guarantee immutability of the ID
            tailored_resume.id = master_resume.id
            
            return TailoredResumeVersion(
                id=str(uuid.uuid4()),
                source_resume_id=master_resume.id,
                target_job_id=target_job_id,
                resume=tailored_resume
            )
        except Exception as e:
            logger.error(f"Failed to tailor resume: {e}")
            raise

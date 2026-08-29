import logging
from backend.models.resume import JobDescription
from backend.config.settings import settings

logger = logging.getLogger(__name__)

class JDParserService:
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
            
    def parse_job_description(self, raw_text: str) -> JobDescription:
        """Parses a raw JD string into a structured JobDescription Pydantic model."""
        from google.genai import types
        
        prompt = f"""
        Extract the structured details from the following job description.
        If a field is missing or ambiguous, omit it or leave it blank.
        Extract technologies and tools into required_skills or preferred_skills as appropriate.
        Extract any educational requirements.
        Extract key responsibilities as brief bullet points.
        
        Job Description:
        {raw_text}
        """
        
        try:
            from backend.services.gemini_client import candidate_models, is_retryable_model_error

            last = None
            for candidate in candidate_models():
                try:
                    response = self.client.models.generate_content(
                        model=candidate,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=JobDescription,
                            temperature=0.1
                        )
                    )
                    if not response.text:
                        raise ValueError("Model returned empty response.")
                    return JobDescription.model_validate_json(response.text)
                except Exception as e:
                    last = e
                    if is_retryable_model_error(e):
                        logger.warning("JD parser Gemini %s unavailable (%s)", candidate, e)
                        continue
                    raise
            raise last or ValueError("Model returned empty response.")
        except Exception as e:
            logger.error(f"Failed to parse JD: {e}")
            raise

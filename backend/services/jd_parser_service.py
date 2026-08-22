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
            # We construct a slightly reduced schema definition for the model to ensure compatibility with Gemini structured output.
            # We can rely on Pydantic to do the final parsing.
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=JobDescription,
                    temperature=0.1
                )
            )
            
            # The response text should be valid JSON matching the JobDescription schema
            if not response.text:
                raise ValueError("Model returned empty response.")
                
            return JobDescription.model_validate_json(response.text)
        except Exception as e:
            logger.error(f"Failed to parse JD: {e}")
            raise

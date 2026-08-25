import json
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from backend.config.settings import settings
from backend.repositories.memory_repository import MemoryRepository
from backend.services.embedding_service import EmbeddingService
from backend.models.resume import Resume, JobDescription
from backend.services.jd_parser_service import JDParserService
from backend.services.ats_analyzer_service import ATSAnalyzerService
from backend.services.resume_tailor_service import ResumeTailorService
from backend.services.resume_renderer import ResumeRendererService

def get_orchestrator_agent(tool_router=None, catalog_json: str = "[]", memory_repo: MemoryRepository = None, embedding_service: EmbeddingService = None, user_id: str = "default_user", workflow_context: str = "") -> LlmAgent:
    client_kwargs = {}
    if not settings.GEMINI_API_KEY:
        client_kwargs = {
            "vertexai": True,
            "project": settings.GOOGLE_CLOUD_PROJECT,
            "location": settings.GOOGLE_CLOUD_REGION
        }
    else:
        client_kwargs = {"api_key": settings.GEMINI_API_KEY}
    
    llm = Gemini(
        model=settings.GEMINI_MODEL,
        client_kwargs=client_kwargs,
        tools=[{"google_search": {}}]
    )
    
    async def call_external_tool(agent_tool_name: str, arguments_json: str) -> str:
        """Call a tool from the external tool catalog.
        Args:
            agent_tool_name: The agent_tool_name from the catalog (e.g. mcp1__add).
            arguments_json: JSON string containing the arguments according to the tool's input_schema.
        """
        if not tool_router:
            return "Error: ToolRouter not initialized."
        try:
            args = json.loads(arguments_json)
            # We need to extract context from somewhere, or accept it as an argument
            # In Phase 2, the context is usually bound to the agent instance
            # We'll pass an empty context for now or a dummy context, but wait, we need real task_ids.
            # Let's see if we can get the context that the engine passed to the agent.
            # Actually, we can just let execute_tool_safe handle an empty context if it's not provided.
            result = await tool_router.execute_tool_safe(agent_tool_name, args, context={"user_id": user_id})
            return str(result)
        except Exception as e:
            # To bubble up retries/failures to Phase 2 workflow engine, we MUST raise it!
            raise e

    async def search_memory(query: str, limit: int = 5) -> str:
        """Search the semantic memory for relevant past context.
        Args:
            query: The search query string.
            limit: Maximum number of results to return.
        """
        if not memory_repo or not embedding_service:
            return "Error: Memory system not initialized."
        try:
            embedding = embedding_service.embed_text(query)
            results = memory_repo.search_memory(user_id, embedding, limit)
            if not results:
                return "No relevant memory found."
            return json.dumps([{"id": r.entry.id, "content": r.entry.content, "score": r.similarity_score} for r in results])
        except Exception as e:
            return f"Error searching memory: {str(e)}"

    async def store_memory(content: str, metadata_json: str = "{}") -> str:
        """Store semantic context into memory for future retrieval.
        Args:
            content: The text content to remember.
            metadata_json: JSON string of structured metadata.
        """
        if not memory_repo or not embedding_service:
            return "Error: Memory system not initialized."
        try:
            metadata = json.loads(metadata_json)
            embedding = embedding_service.embed_text(content)
            doc_id = memory_repo.store_memory(user_id, content, metadata, embedding)
            return f"Memory stored successfully with ID: {doc_id}"
        except Exception as e:
            return f"Error storing memory: {str(e)}"

    async def analyze_resume_ats(resume_json: str, jd_text: str) -> str:
        """Parse a Job Description and analyze a Resume for ATS compliance.
        Args:
            resume_json: The master resume in JSON format.
            jd_text: The raw job description text.
        """
        try:
            resume = Resume.model_validate_json(resume_json)
            jd_parser = JDParserService()
            jd = jd_parser.parse_job_description(jd_text)
            
            analyzer = ATSAnalyzerService()
            score = analyzer.analyze(resume, jd)
            return score.model_dump_json()
        except Exception as e:
            return f"Error analyzing ATS score: {str(e)}"
            
    async def tailor_resume(resume_json: str, jd_text: str, target_job_id: str) -> str:
        """Tailor a master resume to match a job description without fabricating facts.
        Args:
            resume_json: The master resume in JSON format.
            jd_text: The raw job description text.
            target_job_id: A unique ID for the target job.
        """
        try:
            resume = Resume.model_validate_json(resume_json)
            jd_parser = JDParserService()
            jd = jd_parser.parse_job_description(jd_text)
            
            tailor_service = ResumeTailorService()
            tailored = tailor_service.tailor(resume, jd, target_job_id)
            return tailored.model_dump_json()
        except Exception as e:
            return f"Error tailoring resume: {str(e)}"

    instruction = f"""You are the Orchestrator Agent. Your job is to execute the given task.
You have access to an external tool catalog:
{catalog_json}

To use a tool, call the `call_external_tool` function with the `agent_tool_name` and `arguments_json`.
Only use tools from the catalog. Do not attempt to guess URLs or use tools not in the catalog.
If you need to retrieve or store long-term semantic context, use the `search_memory` and `store_memory` tools.
If you need to work with resumes, you can `analyze_resume_ats` and `tailor_resume`.
If a tool fails, it will raise an error which the workflow engine will handle (checkpoints, retries).

Workflow History Context:
{workflow_context}
"""
    
    agent_tools = [call_external_tool, analyze_resume_ats, tailor_resume]
    if memory_repo and embedding_service:
        agent_tools.extend([search_memory, store_memory])
        
    return LlmAgent(
        name="OrchestratorAgent",
        instruction=instruction,
        model=llm,
        tools=agent_tools
    )

# Architecture Definition

## Master Architecture Overview
AgentOS operates as an autonomous AI workspace built on Google Cloud Platform and Gemini. The stack comprises a Next.js frontend and a Python/FastAPI backend utilizing the Google ADK and Google GenAI SDK.

## Key Subsystems
1. Agent Runtime (Google ADK)
2. Workflow Engine (Firestore + Pub/Sub + Cloud Run)
3. MCP Registry & Dynamic MCP Builder (Sandboxed)
4. Scheduler (Cloud Scheduler)
5. Memory (Gemini Embeddings + Vector Store)
6. Resume Engine (JD Parser, ATS Analyzer)

## API Boundaries
### Frontend (Next.js) <-> Backend (FastAPI)
- `POST /api/v1/intent`: Submit user goal.
- `GET /api/v1/workflows/{id}`: Fetch workflow status and execution timeline.
- `POST /api/v1/schedules`: Create new scheduled tasks.
- `GET /api/v1/mcp`: List available tools and connectors.
- `POST /api/v1/mcp/generate`: Request dynamic generation of a new MCP connector.
- `POST /api/v1/resumes`: Manage ATS resumes.
- `GET /api/v1/approvals`: Fetch pending L1/L2 approval requests.

## Database (Firestore Collections)
- `users`: User profiles, settings, autonomy levels.
- `workflows`: Parent workflow states, configuration.
- `runs`: Individual executions of a workflow.
- `tasks`: Granular task DAGs inside a run (with statuses: PENDING, RUNNING, COMPLETED, FAILED, etc.).
- `mcp_registry`: Available MCPs, versions, health status.
- `schedules`: Scheduled jobs, cron configurations.
- `memories`: Agentic memory embeddings and metadata.
- `resumes`: User resume profiles, versions, ATS scores.

## Pub/Sub Topics
- `agentos-workflow-events`: Task execution triggers and status changes.
- `agentos-scheduler-triggers`: Emitted by Cloud Scheduler to trigger workflows.
- `agentos-mcp-validation`: Asynchronous triggers for generated MCP security scans.

## Cloud Scheduler Architecture
- **Job Source:** Google Cloud Scheduler
- **Target:** Pub/Sub Topic (`agentos-scheduler-triggers`)
- **Payload:** `{"schedule_id": "...", "workflow_id": "..."}`
- **Consumer:** Worker service running on Cloud Run, which writes to Firestore and spins up Agent runs.

## Cloud Run Services
1. **API Service:** FastAPI backend for synchronous Next.js requests.
2. **Worker Service:** Asynchronous worker processing Pub/Sub queues for the workflow engine.
3. **MCP Sandbox:** Isolated Cloud Run environment strictly for testing dynamically generated MCP code.

## Cloud Storage (Artifacts)
- `agentos-artifacts-{env}`: User-generated PDFs, reports, downloaded assets.
- `agentos-mcp-builds-{env}`: Temporary storage for dynamically generated MCP code bundles.

## Service Accounts
- `sa-api-service@...`: Access to Firestore, Secret Manager (read), Cloud Storage (read/write).
- `sa-worker-service@...`: Access to Pub/Sub (sub), Firestore, Agent triggers, Cloud Storage.
- `sa-scheduler@...`: Specific permission to publish to `agentos-scheduler-triggers` Pub/Sub topic.
- `sa-mcp-sandbox@...`: Heavily restricted, isolated service account with NO project-wide write access and NO production secrets.

## Secret Requirements
- `GEMINI_API_KEY`: API key for GenAI operations (or use Vertex AI ADC).
- `DB_CREDENTIALS`: Optional, relies on ADC typically.
- `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET`: For user authentication.
- Third-party API Keys: Stored per-user dynamically in Secret Manager.

# Implementation Roadmap

## Phases
- **Phase 0:** Discovery, Repository Analysis, Architecture (Completed)
- **Phase 1:** Foundation (Agent Runtime, Intent/Planner/Orchestrator)
- **Phase 2:** Real Workflow Engine (Task DAGs, Checkpoints, Retries)
- **Phase 3:** MCP Runtime and Tool Registry (Tool Router, Health Checks)
- **Phase 4:** Dynamic MCP Builder (OpenAPI ingestion to generated Python server)
- **Phase 5:** MCP Sandbox and Security Hardening (Isolated container limits)
- **Phase 6:** Scheduler and Autonomous Background Execution (Cloud Scheduler -> Pub/Sub)
- **Phase 7:** Memory and Knowledge System (Gemini Embeddings)
- **Phase 8:** Resume Engine and ATS (JD matching, LaTeX/PDF generation)
- **Phase 9:** Plugin System and Agent Factory
- **Phase 10:** Security, Authentication, Approvals (Autonomy levels)
- **Phase 11:** Self-Healing Execution (RecoveryAgent)
- **Phase 12:** Observability, Auditing, Agent Evaluation (Metrics, Traces)
- **Phase 13:** Google Cloud Production Deployment (Terraform)
- **Phase 14:** Final UX + Stitch / Flow integration

## Phase 1 Acceptance Criteria
- User can input a goal on the frontend dashboard.
- Next.js successfully calls FastAPI.
- IntentAgent creates structured intent from goal.
- PlannerAgent creates execution plan.
- OrchestratorAgent executes one simple real tool.
- State is properly stored in Firestore.
- Frontend displays the execution timeline.
- All code passes typing, linting, tests.
- Execution completes locally and securely.

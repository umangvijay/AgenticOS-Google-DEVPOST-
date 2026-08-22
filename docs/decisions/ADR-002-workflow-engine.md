# ADR 002: Workflow Engine

## Context
The system needs to persist execution graphs (DAGs) and ensure execution reliability even if the frontend disconnects or a transient error occurs.

## Decision
We will build the workflow engine on top of **Firestore**. The state machine (PENDING, RUNNING, COMPLETED, FAILED, etc.) will be driven deterministically by worker logic.

## Rationale
- Firestore provides real-time updates and strong consistency for single-document transactions.
- Allows Next.js to optionally subscribe to real-time changes via Firebase SDK, or poll FastAPI.

## Consequences
- Requires explicit schema validation via Pydantic before writing to Firestore.
- Requires checkpointing strategy to resume workflows.

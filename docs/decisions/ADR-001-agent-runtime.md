# ADR 001: Agent Runtime

## Context
AgentOS needs a flexible, extensible runtime for executing multi-step LLM tasks and coordinating tools.

## Decision
We will use the **Google ADK (Agent Development Kit)** alongside the **Google GenAI SDK** for Gemini 3.x Flash.

## Rationale
- Deep integration with Google ecosystem.
- Provides solid abstractions for defining tools, agents, and planning.

## Consequences
- Requires standardizing on Python 3.11+.
- Code must adhere to the latest ADK documentation.

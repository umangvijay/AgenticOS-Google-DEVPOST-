# ADR 009: Security

## Context
An autonomous agent that can modify state and interact with external systems must have strict guardrails to prevent runaway loops or destructive actions.

## Decision
We will implement an **Approvals Engine** enforcing distinct Autonomy Levels (L0 to L3) and classifying tools by risk level (LOW, MEDIUM, HIGH, CRITICAL).

## Rationale
- Users must trust the system. Prompting for human approval for high-risk actions (e.g., deleting records, sending emails) builds trust.

## Consequences
- Workflows will block indefinitely (WAITING state) pending user approval for specific tasks.
- Frontend must support an Approvals dashboard.

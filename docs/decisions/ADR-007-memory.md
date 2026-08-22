# ADR 007: Memory

## Context
Agents require long-term context retention across profiles, workflows, and semantic document analysis.

## Decision
We will split memory into three tiers:
1. **Profile / Workflow Memory:** Structured JSON stored in Firestore.
2. **Semantic Memory:** Unstructured text embeddings using **Gemini Embedding 2**, stored in a vector database solution (or Firestore Vector Search if suitable).

## Rationale
- Mixing structural and semantic retrieval allows the LLM to access exact context (past runs) and fuzzy context (document snippets).

## Consequences
- Increases token usage/cost for generating and retrieving embeddings.

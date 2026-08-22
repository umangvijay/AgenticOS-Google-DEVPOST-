# ADR 008: Resume Engine

## Context
A key workflow is parsing job descriptions (JD) and tailoring resumes to maximize ATS compliance and user strengths.

## Decision
We will build a custom parser and ATS analyzer pipeline. The generator will produce outputs in LaTeX, Markdown, HTML, and PDF.

## Rationale
- Generating deterministic structured data (JSON) from the JD, then using LLMs to re-write bullet points, provides the most robust results compared to pure LLM generation.

## Consequences
- Requires local/containerized LaTeX or standard HTML-to-PDF rendering engines to support PDF exports.

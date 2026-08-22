# ADR 006: MCP Sandbox

## Context
Executing dynamically generated Python code based on third-party APIs poses severe security risks (SSRF, credential theft, RCE).

## Decision
We will execute all dynamically generated MCP servers in a strictly isolated **Cloud Run Sandbox Container**.

## Rationale
- Containerization provides boundary enforcement at the OS level.
- Cloud Run allows strict limitation of CPU, Memory, and Network egress (via VPC Service Controls or Egress rules).

## Consequences
- Requires a separate, heavily restricted Service Account with zero project-level IAM roles.
- Requires building and pushing a sandbox Docker image.

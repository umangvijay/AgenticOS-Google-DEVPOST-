# ADR 005: MCP Runtime

## Context
AgentOS differentiates by enabling agents to dynamically generate or discover Model Context Protocol (MCP) connectors.

## Decision
We will implement an **MCP Runtime and Tool Registry** that interfaces between the Agents and external tools, validating all requests before execution.

## Rationale
- Standardizes the API for all external integrations.
- Keeps agents agnostic to the underlying transport and authentication details of the API.

## Consequences
- Requires strict manifesting structure (name, version, endpoints, auth, scopes).

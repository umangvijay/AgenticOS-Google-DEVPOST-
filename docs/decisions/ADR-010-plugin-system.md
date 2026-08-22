# ADR 010: Plugin System

## Context
AgentOS should be extensible, allowing users to define custom agents, tools, prompts, and MCP requirements as bundled plugins.

## Decision
We will build a **Plugin Registry** that ingests a strict `manifest.yaml` format for managing plugin lifecycles (INSTALL, ENABLE, DISABLE, UNINSTALL).

## Rationale
- Promotes modular architecture and eventual community contribution.
- Prevents hardcoding custom behavior in the core engine.

## Consequences
- Plugins must undergo validation (similar to dynamic MCPs) before they are allowed to run in the main context.

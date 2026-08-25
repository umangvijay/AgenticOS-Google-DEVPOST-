# AgenticOS

AgenticOS is an autonomous, intelligent Agent Operating System built for the Google AI Hackathon. It is designed to interpret high-level user intents, break them down into DAG-based plans, and execute them reliably using a distributed Cloud Run microservice architecture with self-healing, security approvals, and a dynamic Model Context Protocol (MCP) tool integration layer.

## Key Features
- **Intent-Driven DAG Execution**: Uses the `google-adk` to translate human intent into a Directed Acyclic Graph of tasks.
- **Dynamic MCP Tools**: Automatically ingests OpenAPI specs and dynamically exposes them as MCP tools.
- **Security & Approval Matrix**: Fine-grained role-based access control, tool whitelisting, and human-in-the-loop approvals for destructive actions.
- **Self-Healing Recovery**: Built-in RecoveryAgent that analyzes semantic failures and automatically corrects malformed tool inputs.
- **Vector Memory**: Firestore-backed vector memory using Google GenAI embeddings.
- **Distributed Scale**: Built on Google Cloud (Cloud Run, Pub/Sub, Firestore) using Terraform.

## Documentation Navigation
- [Architecture](ARCHITECTURE.md)
- [Security](SECURITY.md)
- [Deployment](DEPLOYMENT.md)
- [Development](DEVELOPMENT.md)
- [Disaster Recovery](DISASTER_RECOVERY.md)
- [Contributing](CONTRIBUTING.md)
- [Repository Structure](docs/STRUCTURE.md)
- [Local Test Report](docs/LOCAL_TEST_REPORT.md)

## Quick Start
See [DEVELOPMENT.md](DEVELOPMENT.md) for local setup instructions.

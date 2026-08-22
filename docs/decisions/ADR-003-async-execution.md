# ADR 003: Asynchronous Execution

## Context
Long-running AI tasks, tool discovery, and document generation should not block the user's browser.

## Decision
We will decouple execution from HTTP requests using **Google Cloud Pub/Sub** and a dedicated **Cloud Run Worker** service.

## Rationale
- Pub/Sub ensures at-least-once delivery.
- Cloud Run scales down to zero when idle but handles asynchronous events smoothly.

## Consequences
- The Next.js frontend will rely on polling or Firestore real-time listeners instead of waiting for synchronous HTTP responses.

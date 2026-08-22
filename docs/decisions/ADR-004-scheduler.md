# ADR 004: Scheduler

## Context
Users must be able to schedule jobs (hourly, daily, custom cron) that run entirely autonomously.

## Decision
We will utilize **Google Cloud Scheduler** targeting the system's Pub/Sub topic (`agentos-scheduler-triggers`).

## Rationale
- Serverless, highly reliable, supports standard cron expressions and timezones natively.
- Prevents the need for maintaining an active long-running Python scheduler process.

## Consequences
- Local development requires a mock or manual trigger of the Pub/Sub emulator to simulate schedule execution.

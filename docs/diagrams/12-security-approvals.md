# Security approvals and HITL

High-risk tools and auth walls both pause the run. CAPTCHA/OTP/MFA use the same `WAITING_APPROVAL` status as explicit approvals.

```mermaid
graph TD
    Agent -->|High risk or challenge| Engine
    Engine -->|Pause| Status[WAITING_APPROVAL]
    Status --> DB[(SQLite or Firestore)]
    UI[Workspace] -->|SSE| Status
    User -->|Approve or Resume after challenge| UI
    UI -->|POST resume or approve| API
    API --> Engine
    Engine -->|Same browser session| Agent
```

Local default store is SQLite. Completing CAPTCHA in a different browser does not resume the agent session.

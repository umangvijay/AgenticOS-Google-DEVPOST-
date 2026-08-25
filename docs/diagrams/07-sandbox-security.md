# Sandbox Security Flow

```mermaid
graph TD
    Agent[Agent execution] -->|Call Tool| Policy[Tool Policy Engine]
    Policy -->|Check Whitelist| Audit[Audit Logger]
    Policy -->|Check Approval Matrix| Approver[Approval Service]
    Approver -->|Pending| Wait[Wait for User]
    Wait -->|Approved| Execute[Run Action]
    Execute -->|Log Result| Audit
```
